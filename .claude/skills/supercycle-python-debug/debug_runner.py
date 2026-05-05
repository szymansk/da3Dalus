#!/usr/bin/env python3
"""
debug_runner.py — Programmatic pdb/bdb debugging for Claude Code subagents.

Non-interactive debugging tools that output structured JSON. Uses Python's
bdb (the base debugger underlying pdb) to set breakpoints, break on
exceptions, and collect runtime state — all without requiring a TTY.

Three strategies:
  1. ExceptionHunter  — run target, break on exceptions, capture full context
  2. BreakpointInspector — set breakpoints at specific locations, collect state
  3. ProcessAttacher — attach to running process via SIGUSR1 signal dump

Usage:
  python debug_runner.py hunt <module> <function> [--args '{}'] [-o /tmp/out.json]
  python debug_runner.py inspect <module> <function> --bp file:line [--bp file:line:condition]
  python debug_runner.py attach <pid> [-o /tmp/out.json]
  python debug_runner.py install-handler
"""

from __future__ import annotations

import bdb
import json
import linecache
import os
import signal
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

MAX_REPR_LEN = 500
MAX_STACK_DEPTH = 50
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_HITS = 20


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def safe_repr(obj: Any, max_len: int = MAX_REPR_LEN) -> str:
    try:
        r = repr(obj)
        return r if len(r) <= max_len else r[:max_len] + "…"
    except Exception:
        return f"<repr failed: {type(obj).__name__}>"


def safe_type(obj: Any) -> str:
    try:
        return type(obj).__qualname__
    except Exception:
        return "<unknown>"


def _serialize(obj: Any) -> Any:
    if obj is None or isinstance(obj, (int, float, bool, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj[:50]]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in list(obj.items())[:50]}
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    return safe_repr(obj)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    type: str  # exception | breakpoint_hit | unhandled_exception | trace
    file: str
    line: int
    function: str
    locals: dict = field(default_factory=dict)
    stack_trace: list = field(default_factory=list)
    exception: dict | None = None
    expressions: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class DebugResult:
    session: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    breakpoints_hit: list = field(default_factory=list)
    recommendation: str = ""

    def to_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)
        print(f"[debug_runner] results → {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Frame introspection
# ---------------------------------------------------------------------------

def capture_locals(
    frame, variables: list[str] | None = None
) -> dict[str, dict]:
    loc = frame.f_locals
    names = variables if variables else [
        n for n in loc if not n.startswith("__")
    ]
    return {
        n: {"type": safe_type(loc[n]), "value": _serialize(loc[n])}
        for n in names if n in loc
    }


def capture_stack(frame, max_depth: int = MAX_STACK_DEPTH) -> list[dict]:
    stack: list[dict] = []
    f = frame
    depth = 0
    while f and depth < max_depth:
        stack.append({
            "file": f.f_code.co_filename,
            "line": f.f_lineno,
            "function": f.f_code.co_name,
            "code": (linecache.getline(f.f_code.co_filename, f.f_lineno).strip()
                     or ""),
        })
        f = f.f_back
        depth += 1
    stack.reverse()
    return stack


def exception_chain(exc: BaseException) -> list[str]:
    chain: list[str] = []
    seen: set[int] = set()
    while exc and id(exc) not in seen:
        seen.add(id(exc))
        chain.append(f"{type(exc).__name__}: {exc}")
        exc = exc.__cause__ or exc.__context__
    return chain


# ---------------------------------------------------------------------------
# Strategy 1: ExceptionHunter
# ---------------------------------------------------------------------------

class ExceptionHunter(bdb.Bdb):
    """Run a callable; break on every exception and capture full context."""

    # Paths to ignore — internal Python machinery that raises/catches exceptions normally
    _NOISE_PATHS = frozenset((
        "<frozen ", "importlib", "site-packages", "_bootstrap",
        "abc.py", "typing.py", "enum.py", "functools.py",
    ))

    def __init__(
        self,
        target_func: Callable,
        output_path: str = "/tmp/debug_result.json",
        variables: list[str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        project_root: str | None = None,
    ):
        super().__init__()
        self.target_func = target_func
        self.output_path = output_path
        self.variables = variables
        self.timeout = timeout
        self.project_root = project_root
        self.result = DebugResult(
            session={"strategy": "exception-hunt", "status": "running"}
        )
        self._t0 = 0.0

    def _is_noise(self, filename: str) -> bool:
        """Filter out exceptions from Python internals."""
        if any(p in filename for p in self._NOISE_PATHS):
            return True
        if self.project_root and self.project_root not in filename:
            if not filename.startswith("<"):
                return True
        return False

    def user_exception(self, frame, exc_info):
        if self._is_noise(frame.f_code.co_filename):
            self.set_continue()
            return

        exc_type, exc_value, _ = exc_info
        self.result.findings.append(asdict(Finding(
            type="exception",
            file=frame.f_code.co_filename,
            line=frame.f_lineno,
            function=frame.f_code.co_name,
            locals=capture_locals(frame, self.variables),
            stack_trace=capture_stack(frame),
            exception={
                "class": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value),
                "chain": exception_chain(exc_value),
            },
            timestamp=round(time.time() - self._t0, 4),
        )))
        self.set_continue()

    def run_target(self) -> DebugResult:
        self._t0 = time.time()
        timer = threading.Timer(self.timeout, self._on_timeout)
        timer.daemon = True
        timer.start()
        try:
            try:
                self.runcall(self.target_func)
            except bdb.BdbQuit:
                pass
            except Exception as e:
                self.result.findings.append(asdict(Finding(
                    type="unhandled_exception",
                    file="<top-level>",
                    line=0,
                    function="<target>",
                    exception={
                        "class": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                        "chain": exception_chain(e),
                    },
                    timestamp=round(time.time() - self._t0, 4),
                )))
        finally:
            timer.cancel()
            self.result.session["duration_seconds"] = round(
                time.time() - self._t0, 3
            )
            if self.result.session["status"] == "running":
                self.result.session["status"] = "completed"
            self.result.to_json(self.output_path)
        return self.result

    def _on_timeout(self):
        self.result.session["status"] = "timeout"
        self.set_quit()


# ---------------------------------------------------------------------------
# Strategy 2: BreakpointInspector
# ---------------------------------------------------------------------------

class BreakpointInspector(bdb.Bdb):
    """Set breakpoints at specific locations; collect state at each hit."""

    def __init__(
        self,
        target_func: Callable,
        breakpoints: list[dict],
        variables: list[str] | None = None,
        expressions: list[str] | None = None,
        output_path: str = "/tmp/debug_result.json",
        max_hits: int = DEFAULT_MAX_HITS,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        super().__init__()
        self.target_func = target_func
        self.bp_configs = breakpoints
        self.variables = variables
        self.expressions = expressions or []
        self.output_path = output_path
        self.max_hits = max_hits
        self.timeout = timeout
        self.result = DebugResult(
            session={"strategy": "breakpoint-inspect", "status": "running"}
        )
        self._hits = 0
        self._bp_counter: dict[str, int] = {}
        self._t0 = 0.0

    def _setup_breakpoints(self):
        for bp in self.bp_configs:
            fname = os.path.abspath(bp["file"])
            lineno = bp.get("line")
            cond = bp.get("condition")
            if lineno:
                self.set_break(fname, lineno, cond=cond)

    def user_line(self, frame):
        key = f"{frame.f_code.co_filename}:{frame.f_lineno}"
        if not self._is_target_bp(frame):
            self.set_continue()
            return

        self._hits += 1
        self._bp_counter[key] = self._bp_counter.get(key, 0) + 1

        expr_results = {}
        for expr in self.expressions:
            try:
                expr_results[expr] = _serialize(
                    eval(expr, frame.f_globals, frame.f_locals)  # noqa: S307
                )
            except Exception as e:
                expr_results[expr] = f"<error: {e}>"

        self.result.findings.append(asdict(Finding(
            type="breakpoint_hit",
            file=frame.f_code.co_filename,
            line=frame.f_lineno,
            function=frame.f_code.co_name,
            locals=capture_locals(frame, self.variables),
            stack_trace=capture_stack(frame),
            expressions=expr_results,
            timestamp=round(time.time() - self._t0, 4),
        )))

        if self._hits >= self.max_hits:
            self.result.session["status"] = "max_hits_reached"
            self.set_quit()
        else:
            self.set_continue()

    def _is_target_bp(self, frame) -> bool:
        for bp in self.bp_configs:
            bp_file = os.path.abspath(bp["file"])
            if bp_file == frame.f_code.co_filename or bp_file in frame.f_code.co_filename:
                if "line" in bp and bp["line"] == frame.f_lineno:
                    return True
                if "function" in bp and bp["function"] == frame.f_code.co_name:
                    return True
        return False

    def run_target(self) -> DebugResult:
        self._t0 = time.time()
        self._setup_breakpoints()
        timer = threading.Timer(self.timeout, lambda: self.set_quit())
        timer.daemon = True
        timer.start()
        try:
            try:
                self.runcall(self.target_func)
            except bdb.BdbQuit:
                pass
            except Exception as e:
                self.result.findings.append(asdict(Finding(
                    type="unhandled_exception",
                    file="<top-level>",
                    line=0,
                    function="<target>",
                    exception={
                        "class": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                    timestamp=round(time.time() - self._t0, 4),
                )))
        finally:
            timer.cancel()
            self.result.session["duration_seconds"] = round(
                time.time() - self._t0, 3
            )
            if self.result.session["status"] == "running":
                self.result.session["status"] = "completed"
            self.result.breakpoints_hit = [
                {"location": k, "hit_count": v}
                for k, v in self._bp_counter.items()
            ]
            self.result.to_json(self.output_path)
        return self.result


# ---------------------------------------------------------------------------
# Strategy 3: ProcessAttacher (signal-based state dump)
# ---------------------------------------------------------------------------

class ProcessAttacher:
    """Attach to a running Python process via SIGUSR1 signal dump.

    The target process must have the signal handler installed (see
    install_handler_code()). This class sends the signal and reads the
    resulting JSON dump file.
    """

    def __init__(
        self,
        pid: int,
        dump_path: str = "/tmp/debug_dump.json",
        timeout: int = 5,
    ):
        self.pid = pid
        self.dump_path = dump_path
        self.timeout = timeout

    def dump_state(self) -> dict:
        """Send SIGUSR1 and read the state dump."""
        if os.path.exists(self.dump_path):
            os.remove(self.dump_path)

        os.kill(self.pid, signal.SIGUSR1)

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if os.path.exists(self.dump_path):
                time.sleep(0.2)
                with open(self.dump_path) as f:
                    return json.load(f)
            time.sleep(0.1)

        raise TimeoutError(
            f"No debug dump from PID {self.pid} after {self.timeout}s. "
            "Is the SIGUSR1 handler installed?"
        )

    def multi_dump(self, count: int = 5, interval: float = 0.5) -> list[dict]:
        """Take multiple state snapshots to see execution progression."""
        dumps = []
        for _ in range(count):
            try:
                dumps.append(self.dump_state())
            except TimeoutError:
                break
            time.sleep(interval)
        return dumps

    @staticmethod
    def handler_code() -> str:
        """Python code to install in the target process's startup."""
        return '''
import json, os, signal, sys, threading, time, traceback

def _da3dalus_debug_handler(signum, frame):
    """SIGUSR1 → dump current state to /tmp/debug_dump.json"""
    try:
        result = {
            "timestamp": time.time(),
            "pid": os.getpid(),
            "signal_frame": {
                "file": frame.f_code.co_filename,
                "line": frame.f_lineno,
                "function": frame.f_code.co_name,
                "locals": {
                    k: repr(v)[:200]
                    for k, v in frame.f_locals.items()
                    if not k.startswith("__")
                },
            },
            "stack_trace": traceback.format_stack(frame),
            "all_threads": {},
        }
        for t in threading.enumerate():
            tid = t.ident
            if tid and tid in sys._current_frames():
                result["all_threads"][t.name] = (
                    traceback.format_stack(sys._current_frames()[tid])
                )
        with open("/tmp/debug_dump.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
    except Exception:
        pass  # Never crash the target process

signal.signal(signal.SIGUSR1, _da3dalus_debug_handler)
'''


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Programmatic Python debugger for CI/agent use"
    )
    sub = parser.add_subparsers(dest="cmd")

    # -- hunt --
    p_hunt = sub.add_parser(
        "hunt", help="Run target function and break on every exception"
    )
    p_hunt.add_argument("module", help="Dotted module path")
    p_hunt.add_argument("function", help="Function name to call")
    p_hunt.add_argument(
        "--args", default="{}", help="JSON kwargs for the function"
    )
    p_hunt.add_argument("--vars", nargs="*", help="Variables to capture")
    p_hunt.add_argument("--project-root", help="Filter exceptions to this path")
    p_hunt.add_argument("-o", "--output", default="/tmp/debug_result.json")
    p_hunt.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT)

    # -- inspect --
    p_bp = sub.add_parser(
        "inspect", help="Set breakpoints and collect state at each hit"
    )
    p_bp.add_argument("module", help="Dotted module path")
    p_bp.add_argument("function", help="Function name to call")
    p_bp.add_argument(
        "--bp", action="append", required=True,
        help="Breakpoint: file:line[:condition]  (repeatable)"
    )
    p_bp.add_argument(
        "--expr", action="append", help="Expression to evaluate at each hit"
    )
    p_bp.add_argument("--args", default="{}", help="JSON kwargs")
    p_bp.add_argument("--vars", nargs="*", help="Variables to capture")
    p_bp.add_argument("-o", "--output", default="/tmp/debug_result.json")
    p_bp.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_bp.add_argument("--max-hits", type=int, default=DEFAULT_MAX_HITS)

    # -- attach --
    p_att = sub.add_parser(
        "attach", help="Send SIGUSR1 to running process, read state dump"
    )
    p_att.add_argument("pid", type=int, help="Target PID")
    p_att.add_argument("-n", "--count", type=int, default=1,
                       help="Number of consecutive dumps")
    p_att.add_argument("--interval", type=float, default=0.5)
    p_att.add_argument("-o", "--output", default="/tmp/debug_dump.json")
    p_att.add_argument("-t", "--timeout", type=int, default=5)

    # -- install-handler --
    sub.add_parser(
        "install-handler",
        help="Print SIGUSR1 handler code to paste into target process"
    )

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "hunt":
        import importlib
        mod = importlib.import_module(args.module)
        func = getattr(mod, args.function)
        kwargs = json.loads(args.args)
        hunter = ExceptionHunter(
            target_func=lambda: func(**kwargs),
            output_path=args.output,
            variables=args.vars,
            timeout=args.timeout,
            project_root=getattr(args, "project_root", None),
        )
        result = hunter.run_target()
        n = len(result.findings)
        print(f"[debug_runner] hunt complete — {n} finding(s)")
        print(json.dumps(asdict(result), indent=2, default=str))

    elif args.cmd == "inspect":
        import importlib
        bps = []
        for spec in args.bp:
            parts = spec.split(":")
            bp = {"file": parts[0], "line": int(parts[1])}
            if len(parts) > 2:
                bp["condition"] = ":".join(parts[2:])
            bps.append(bp)

        mod = importlib.import_module(args.module)
        func = getattr(mod, args.function)
        kwargs = json.loads(args.args)
        inspector = BreakpointInspector(
            target_func=lambda: func(**kwargs),
            breakpoints=bps,
            variables=args.vars,
            expressions=args.expr or [],
            output_path=args.output,
            max_hits=args.max_hits,
            timeout=args.timeout,
        )
        result = inspector.run_target()
        n = len(result.findings)
        print(f"[debug_runner] inspect complete — {n} finding(s)")
        print(json.dumps(asdict(result), indent=2, default=str))

    elif args.cmd == "attach":
        attacher = ProcessAttacher(
            pid=args.pid,
            dump_path=args.output,
            timeout=args.timeout,
        )
        if args.count == 1:
            dump = attacher.dump_state()
            print(json.dumps(dump, indent=2, default=str))
        else:
            dumps = attacher.multi_dump(count=args.count, interval=args.interval)
            print(json.dumps(dumps, indent=2, default=str))

    elif args.cmd == "install-handler":
        print(ProcessAttacher.handler_code())


if __name__ == "__main__":
    _cli()
