/**
 * The canon navigator in connected mode (gh-1282, ADR 0030), run in jsdom against a stubbed backend.
 * The page is the generated artifact `public/canon-navigator.html`: one graph implementation.
 */
import { describe, it, expect } from "vitest";
import {
  openNavigator,
  settle,
  type Reply,
  type Route,
} from "./canonNavigator.helpers";

const QUERY = "?connected=1&api=http://api.test&aircraft=bryan";

const FLEET = [
  { id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} },
  {
    id: "rv-7",
    name: "RV-7",
    mass_kg: 0.5,
    flap_deflections: { "flap-deflection-landing": 30 },
  },
];

const PROVENANCE = { build_digest: "t", defaults_used: [] };

function quantity(slug: string, extra: Record<string, unknown> = {}) {
  return {
    slug,
    unit: "m/s",
    status: "ok",
    value: 7.5,
    tool: "OPT",
    application: "a",
    warnings: [],
    from_cache: false,
    ...extra,
  };
}

function response(over: Record<string, unknown> = {}): Reply {
  return {
    body: {
      quantities: [],
      input_errors: [],
      provenance: PROVENANCE,
      verdicts: [],
      needs_confirmation: [],
      logs: [],
      ...over,
    },
  };
}

/** A backend that serves the fleet and answers compute requests with `compute`. */
function backend(compute: (body: Record<string, unknown>) => Reply): Route {
  return (url, init) => {
    if (url.endsWith("/canon/fleet")) return { body: FLEET };
    return compute(JSON.parse(String(init?.body)));
  };
}

const answerOk = backend((body) =>
  response({ quantities: (body.quantities as string[]).map((s) => quantity(s)) }),
);

function badgeState(nav: ReturnType<typeof openNavigator>, id: string) {
  return nav.node(id).querySelector(".cbadge")?.getAttribute("data-state") ?? null;
}

function computeCalls(nav: ReturnType<typeof openNavigator>) {
  return nav.calls.filter((c) => c.url.endsWith("/canon/compute"));
}

describe("the navigator without ?connected=1", () => {
  it("behaves as the published artifact: nothing connected shows, nothing is fetched", async () => {
    const nav = openNavigator("", answerOk);
    await settle();
    expect(nav.document.getElementById("conn")!.hidden).toBe(true);
    expect(nav.document.getElementById("logpanel")!.hidden).toBe(true);
    nav.click(nav.node("stall-speed"));
    await settle();
    expect(nav.calls).toEqual([]);
    expect(nav.document.querySelector(".cbadge")).toBeNull();
    expect(nav.document.getElementById("kres")).toBeNull();
  });
});

describe("the connected navigator", () => {
  it("loads the aircraft and shows the development label", async () => {
    const nav = openNavigator(QUERY, answerOk);
    await settle();
    expect(nav.calls[0].url).toBe("http://api.test/canon/fleet");
    expect(nav.document.getElementById("conn")!.hidden).toBe(false);
    expect(nav.document.getElementById("connLabel")!.textContent).toBe(
      "Canon/kernel view (development), experts only",
    );
    expect(nav.document.getElementById("connAircraft")!.textContent).toContain("BRYAN");
    expect(nav.document.getElementById("logpanel")!.hidden).toBe(false);
  });

  it("reports an unknown aircraft and an unreachable backend", async () => {
    const unknown = openNavigator("?connected=1&api=http://api.test&aircraft=zzz", answerOk);
    await settle();
    expect(unknown.document.getElementById("connAircraft")!.textContent).toContain("Unknown aircraft");
    const down = openNavigator(QUERY, () => ({ status: 503, body: { error: { message: "down" } } }));
    await settle();
    expect(down.document.getElementById("connAircraft")!.textContent).toContain("not reachable: down");
  });

  it("computes a quantity on click and shows its value", async () => {
    const nav = openNavigator(QUERY, answerOk);
    await settle();
    nav.click(nav.node("stall-speed"));
    expect(badgeState(nav, "stall-speed")).toBe("computing");
    await settle();
    const [call] = computeCalls(nav);
    expect(call.url).toBe("http://api.test/canon/compute");
    expect(call.init?.method).toBe("POST");
    expect(call.body).toEqual({
      aircraft: { fleet: "bryan" },
      quantities: ["stall-speed"],
      values: {},
      include_long_runs: false,
    });
    expect(badgeState(nav, "stall-speed")).toBe("ok");
    expect(nav.document.getElementById("kres")!.textContent).toContain("7.5 m/s");
  });

  it("does not compute the same quantity twice but recomputes on request", async () => {
    const nav = openNavigator(QUERY, answerOk);
    await settle();
    nav.click(nav.node("stall-speed"));
    await settle();
    nav.click(nav.node("stall-speed"));
    await settle();
    expect(computeCalls(nav)).toHaveLength(1);
    nav.click(nav.document.getElementById("recompute")!);
    await settle();
    expect(computeCalls(nav)).toHaveLength(2);
  });

  it("shows an interval with its worlds", async () => {
    const nav = openNavigator(
      QUERY,
      backend(() =>
        response({
          quantities: [
            quantity("neutral-point", {
              unit: "m",
              value: null,
              interval: { min: 0.08, max: 0.1, worlds: { "neutral-point=avl": 0.1, "neutral-point=textbook": 0.08 } },
            }),
          ],
        }),
      ),
    );
    await settle();
    nav.click(nav.node("neutral-point"));
    await settle();
    const panel = nav.document.getElementById("kres")!.textContent!;
    expect(panel).toContain("0.08…0.1 m");
    expect(panel).toContain("neutral-point=avl");
  });

  it("marks warnings and shows them in the panel", async () => {
    const warning = {
      severity: "defect",
      code: "reynolds_outside_band",
      message: "The tip chords are below the band.",
      origin: "minimum-drag-speed",
      world: null,
    };
    const nav = openNavigator(
      QUERY,
      backend(() => response({ quantities: [quantity("minimum-drag-speed", { warnings: [warning] })] })),
    );
    await settle();
    nav.click(nav.node("minimum-drag-speed"));
    await settle();
    expect(badgeState(nav, "minimum-drag-speed")).toBe("warning");
    const panel = nav.document.getElementById("kres")!.textContent!;
    expect(panel).toContain("defect · reynolds_outside_band");
    expect(panel).toContain("The tip chords are below the band.");
  });

  describe("an error", () => {
    const upstream = {
      code: "upstream_failed",
      category: "upstream_failed",
      message: "`stall-speed` has no value because `air-density` failed.",
      hint: "Fix `air-density` first.",
      retryable: false,
      escalate: false,
      detail: { causes: [{ quantity: "air-density", code: "missing_input" }] },
    };

    it("is marked at the node and offers to go to the failing upstream node", async () => {
      const nav = openNavigator(
        QUERY,
        backend((body) => {
          const slug = (body.quantities as string[])[0];
          return response({
            quantities: [
              slug === "stall-speed"
                ? quantity(slug, { status: "error", value: null, error: upstream, unit: null })
                : quantity(slug, {
                    status: "error",
                    value: null,
                    unit: null,
                    error: {
                      code: "missing_input",
                      category: "invalid_input",
                      message: "air-density is not supplied",
                      hint: "Supply it.",
                      formula: "air-density",
                      input_path: "values.aircraft-mass",
                      detail: {},
                    },
                  }),
            ],
          });
        }),
      );
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      expect(badgeState(nav, "stall-speed")).toBe("error");
      expect(badgeState(nav, "air-density")).toBe("error");
      const goto = nav.document.querySelector<HTMLButtonElement>('#kres button[data-goto="air-density"]')!;
      expect(goto.textContent).toContain("Go to cause");
      nav.click(goto);
      await settle();
      expect(nav.document.getElementById("kres")!.dataset.for).toBe("air-density");
      expect(computeCalls(nav).at(-1)!.body!.quantities).toEqual(["air-density"]);
      const panel = nav.document.getElementById("kres")!.textContent!;
      expect(panel).toContain("missing_input");
      expect(panel).toContain("at formula air-density");
      expect(panel).toContain("input path values.aircraft-mass");
      const input = nav.document.querySelector<HTMLButtonElement>('#kres button[data-goto="aircraft-mass"]')!;
      nav.click(input);
      await settle();
      expect(nav.document.getElementById("ovIn")).not.toBeNull();
    });

    it("of a failed request becomes an error at every requested node", async () => {
      const nav = openNavigator(QUERY, (url) =>
        url.endsWith("/canon/fleet") ? { body: FLEET } : { status: 500, body: { error: { message: "boom" } } },
      );
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      expect(badgeState(nav, "stall-speed")).toBe("error");
      expect(nav.document.getElementById("kres")!.textContent).toContain("boom");
      expect(nav.document.getElementById("loglines")!.textContent).toContain("compute failed: boom");
    });

    it("of rejected input shows its path", async () => {
      const nav = openNavigator(
        QUERY,
        backend(() =>
          response({
            input_errors: [
              { code: "non_positive_value", category: "invalid_input", message: "mass must be positive", hint: "Raise it.", input_path: "values.aircraft-mass", detail: {} },
            ],
          }),
        ),
      );
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      expect(badgeState(nav, "stall-speed")).toBe("error");
      expect(nav.document.getElementById("kres")!.textContent).toContain("mass must be positive");
    });
  });

  it("asks before a long run and resends with include_long_runs", async () => {
    const nav = openNavigator(
      QUERY,
      backend((body) =>
        body.include_long_runs
          ? response({ quantities: [quantity("neutral-point")] })
          : response({
              quantities: [{ slug: "neutral-point", status: "skipped", warnings: [], reason: { code: "long_run_not_included", message: "takes minutes" } }],
              needs_confirmation: ["neutral-point"],
            }),
      ),
    );
    await settle();
    nav.click(nav.node("neutral-point"));
    await settle();
    expect(badgeState(nav, "neutral-point")).toBe("skipped");
    const box = nav.document.getElementById("confirmbox")!;
    expect(box.hidden).toBe(false);
    expect(box.textContent).toContain("neutral-point");
    nav.click(nav.document.getElementById("runLong")!);
    await settle();
    expect(box.hidden).toBe(true);
    expect(computeCalls(nav).at(-1)!.body!.include_long_runs).toBe(true);
    expect(badgeState(nav, "neutral-point")).toBe("ok");
  });

  it("keeps the skipped state when the confirmation is declined", async () => {
    const nav = openNavigator(
      QUERY,
      backend(() =>
        response({
          quantities: [{ slug: "neutral-point", status: "skipped", warnings: [], reason: { code: "long_run_not_included", message: "x" } }],
          needs_confirmation: ["neutral-point"],
        }),
      ),
    );
    await settle();
    nav.click(nav.node("neutral-point"));
    await settle();
    nav.click(nav.document.getElementById("skipLong")!);
    expect(nav.document.getElementById("confirmbox")!.hidden).toBe(true);
    expect(computeCalls(nav)).toHaveLength(1);
    expect(badgeState(nav, "neutral-point")).toBe("skipped");
  });

  it("computes all implemented quantities", async () => {
    const nav = openNavigator(QUERY, answerOk);
    await settle();
    nav.click(nav.document.getElementById("computeAll")!);
    await settle();
    const [call] = computeCalls(nav);
    const slugs = call.body!.quantities as string[];
    expect(slugs.length).toBeGreaterThan(20);
    expect(slugs).toContain("stall-speed");
    expect(slugs).not.toContain("aircraft-mass");
    expect(nav.document.getElementById("connStat")!.textContent).toContain(`${slugs.length} computed`);
    nav.click(nav.document.getElementById("clearAll")!);
    expect(badgeState(nav, "stall-speed")).toBeNull();
  });

  describe("an input", () => {
    it("shows the fleet value and recomputes the dependent quantities with an override", async () => {
      const nav = openNavigator(QUERY, answerOk);
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      nav.click(nav.node("aircraft-mass"));
      await settle();
      let panel = nav.document.getElementById("kres")!.textContent!;
      expect(panel).toContain("0.151");
      expect(panel).toContain("fleet value");
      expect(computeCalls(nav)).toHaveLength(1); // an input is not computed
      const field = nav.document.getElementById("ovIn") as HTMLInputElement;
      field.value = "0.2";
      nav.click(nav.document.getElementById("ovSet")!);
      await settle();
      const resent = computeCalls(nav).at(-1)!;
      expect(resent.body!.values).toEqual({ "aircraft-mass": 0.2 });
      expect(resent.body!.quantities).toContain("stall-speed");
      panel = nav.document.getElementById("kres")!.textContent!;
      expect(panel).toContain("your override");
      nav.click(nav.document.getElementById("ovReset")!);
      await settle();
      expect(computeCalls(nav).at(-1)!.body!.values).toEqual({});
    });

    it("ignores an override that is not a number", async () => {
      const nav = openNavigator(QUERY, answerOk);
      await settle();
      nav.click(nav.node("aircraft-mass"));
      await settle();
      (nav.document.getElementById("ovIn") as HTMLInputElement).value = "";
      nav.click(nav.document.getElementById("ovSet")!);
      await settle();
      expect(computeCalls(nav)).toHaveLength(0);
    });

    it("shows the canon default where the fleet has no value", async () => {
      const nav = openNavigator(QUERY, answerOk);
      await settle();
      nav.click(nav.node("altitude"));
      await settle();
      expect(nav.document.getElementById("kres")!.textContent).toMatch(/default/);
    });
  });

  it("says so for a quantity the kernel does not implement", async () => {
    const nav = openNavigator(QUERY, answerOk);
    await settle();
    const open = nav.window.eval(
      "Object.keys(Q).find(q=>STATUS[q]==='open')",
    ) as string;
    nav.click(nav.node(open));
    await settle();
    expect(nav.document.getElementById("kres")!.textContent).toContain("Not in the kernel yet");
    expect(computeCalls(nav)).toHaveLength(0);
  });

  describe("the evaluation", () => {
    const verdict = (severity: string | null, status: string) => ({
      rule_id: "horizontal-tail-volume",
      quantity: "horizontal-tail-volume",
      status,
      severity,
      unit: "1",
      value: 0.2,
      explanation: "e",
      text: "Horizontal tail volume (rule, Drela): 0.2 lies below the band.",
    });

    it("marks the rule node red or yellow and carries the LLM-ready text", async () => {
      for (const [severity, state] of [["bad", "error"], ["caution", "warning"]] as const) {
        const nav = openNavigator(
          QUERY,
          backend(() =>
            response({
              quantities: [quantity("horizontal-tail-volume", { unit: "1" })],
              verdicts: [verdict(severity, "below")],
            }),
          ),
        );
        await settle();
        nav.click(nav.node("horizontal-tail-volume"));
        await settle();
        expect(badgeState(nav, "rule:horizontal-tail-volume")).toBe(state);
        expect(nav.document.getElementById("kres")!.textContent).toContain("lies below the band");
        nav.click(nav.node("rule:horizontal-tail-volume"));
        await settle();
        expect(nav.document.getElementById("kres")!.textContent).toContain("lies below the band");
      }
    });

    it("marks an inside verdict green and says when a rule is not judged yet", async () => {
      const nav = openNavigator(
        QUERY,
        backend(() =>
          response({
            quantities: [quantity("horizontal-tail-volume", { unit: "1" })],
            verdicts: [verdict(null, "inside")],
          }),
        ),
      );
      await settle();
      nav.click(nav.node("rule:horizontal-tail-volume"));
      await settle();
      expect(nav.document.getElementById("kres")!.textContent).toContain("Not judged yet");
      nav.click(nav.node("horizontal-tail-volume"));
      await settle();
      expect(badgeState(nav, "rule:horizontal-tail-volume")).toBe("ok");
    });
  });

  describe("the log panel", () => {
    const logs = [
      { time: "2026-10-28T08:00:00.123Z", level: "DEBUG", logger: "aero_kernel.engine", message: "node started", formula: "stall-speed", quantity: null },
      { time: "2026-10-28T08:00:00.456Z", level: "WARNING", logger: "aero_kernel.engine", message: "cache miss", formula: null, quantity: "air-density" },
    ];

    it("lists the kernel records of the request and filters by level", async () => {
      const nav = openNavigator(QUERY, backend(() => response({ quantities: [quantity("stall-speed")], logs })));
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      const lines = nav.document.getElementById("loglines")!;
      expect(lines.textContent).toContain("08:00:00.123");
      expect(lines.textContent).toContain("node started");
      expect(lines.textContent).toContain("compute stall-speed");
      const level = nav.document.getElementById("logLevel") as HTMLSelectElement;
      level.value = "WARNING";
      level.dispatchEvent(new nav.window.Event("change"));
      expect(lines.textContent).not.toContain("node started");
      expect(lines.textContent).toContain("cache miss");
      nav.click(nav.document.getElementById("logClear")!);
      expect(lines.textContent).toBe("");
    });

    it("selects the node of a line on click", async () => {
      const nav = openNavigator(QUERY, backend(() => response({ quantities: [quantity("stall-speed")], logs })));
      await settle();
      nav.click(nav.node("stall-speed"));
      await settle();
      const line = nav.document.querySelector<HTMLElement>('#loglines [data-q="air-density"]')!;
      nav.click(line);
      await settle();
      expect(computeCalls(nav).at(-1)!.body!.quantities).toEqual(["air-density"]);
    });

    it("collapses", async () => {
      const nav = openNavigator(QUERY, answerOk);
      await settle();
      const toggle = nav.document.getElementById("logToggle")!;
      nav.click(toggle);
      expect(nav.document.getElementById("logpanel")!.classList.contains("shut")).toBe(true);
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
    });
  });
});
