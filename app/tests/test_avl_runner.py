"""Tests for app/services/avl_runner.py — standalone AVL runner.

Covers: parse_stability_output, AVLRunner._build_keystrokes,
AVLRunner._post_process_results, AVLRunner.run (mocked subprocess).
"""

from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Sample AVL stability output for parser tests
# ---------------------------------------------------------------------------

SAMPLE_STABILITY_OUTPUT = """\
 Standard axis orientation,  X fwd, Z down

 Run case:  -unnamed-

  Alpha =   5.00000     pb/2V =   0.00000     p'b/2V =   0.00000
  Beta  =   0.00000     qc/2V =   0.00000
  Mach  =     0.000     rb/2V =   0.00000     r'b/2V =   0.00000

  CXtot =  -0.00230     Cltot =   0.00000     Cl'tot =   0.00000
  CYtot =   0.00000     Cmtot =  -0.02270
  CZtot =  -0.54780     Cntot =   0.00000     Cn'tot =   0.00000

  CLtot =   0.54690
  CDtot =   0.04509
  CDvis =   0.00000     CDind = 0.0291513
  CLff  =   0.54690     CDff  = 0.0297201    | Trefftz
  CYff  =   0.00000         e =    0.9860    | Plane

  CL_a =   6.09800
  CL_b =   0.00000
  CY_a =   0.00000
  CY_b =  -0.31200
  Cm_a =  -1.23400
  Cn_b =   0.08900
  Cl_b =  -0.12300
"""


# =========================================================================== #
# parse_stability_output
# =========================================================================== #


class TestParseStabilityOutput:
    """Verify parsing of AVL stability output into a flat dict."""

    def test_parses_canonical_flight_condition_keys(self):
        from app.services.avl_runner import parse_stability_output

        result = parse_stability_output(SAMPLE_STABILITY_OUTPUT)
        assert result["Alpha"] == pytest.approx(5.0)
        assert result["Beta"] == pytest.approx(0.0)
        assert result["Mach"] == pytest.approx(0.0)

    def test_parses_total_coefficients(self):
        from app.services.avl_runner import parse_stability_output

        result = parse_stability_output(SAMPLE_STABILITY_OUTPUT)
        assert result["CLtot"] == pytest.approx(0.54690)
        assert result["CDtot"] == pytest.approx(0.04509)
        assert result["CXtot"] == pytest.approx(-0.00230)
        assert result["CYtot"] == pytest.approx(0.0)
        assert result["CZtot"] == pytest.approx(-0.54780)
        assert result["Cmtot"] == pytest.approx(-0.02270)
        assert result["Cntot"] == pytest.approx(0.0)
        assert result["Cltot"] == pytest.approx(0.0)

    def test_parses_stability_derivatives(self):
        from app.services.avl_runner import parse_stability_output

        result = parse_stability_output(SAMPLE_STABILITY_OUTPUT)
        assert result["CL_a"] == pytest.approx(6.098)
        assert result["Cm_a"] == pytest.approx(-1.234)
        assert result["CY_b"] == pytest.approx(-0.312)
        assert result["Cn_b"] == pytest.approx(0.089)
        assert result["Cl_b"] == pytest.approx(-0.123)

    def test_parses_induced_drag(self):
        from app.services.avl_runner import parse_stability_output

        result = parse_stability_output(SAMPLE_STABILITY_OUTPUT)
        assert result["CDind"] == pytest.approx(0.0291513)
        assert result["CDff"] == pytest.approx(0.0297201)
        assert result["e"] == pytest.approx(0.9860)

    def test_first_occurrence_wins(self):
        """When duplicate keys exist, the first value is kept."""
        from app.services.avl_runner import parse_stability_output

        text = "  foo =   1.000\n  foo =   2.000\n"
        result = parse_stability_output(text)
        assert result["foo"] == pytest.approx(1.0)

    def test_unparseable_value_becomes_nan(self):
        from app.services.avl_runner import parse_stability_output

        text = "  broken =   NaN_string\n"
        result = parse_stability_output(text)
        assert math.isnan(result["broken"])

    def test_empty_input(self):
        from app.services.avl_runner import parse_stability_output

        result = parse_stability_output("")
        assert result == {}


# =========================================================================== #
# AVLRunner._build_keystrokes
# =========================================================================== #


class TestBuildKeystrokes:
    """Verify keystroke sequence construction."""

    def _make_runner(self, airplane=None, op_point=None):
        """Create an AVLRunner with minimal mocks."""
        from app.services.avl_runner import AVLRunner

        if airplane is None:
            airplane = MagicMock()
            airplane.wings = []
            airplane.b_ref = 2.0
            airplane.c_ref = 0.25
        if op_point is None:
            op_point = MagicMock()
            op_point.velocity = 20.0
            op_point.alpha = 5.0
            op_point.beta = 1.0
            op_point.p = 0.0
            op_point.q = 0.0
            op_point.r = 0.0
            op_point.mach.return_value = 0.058
            op_point.atmosphere.density.return_value = 1.225
        return AVLRunner(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_starts_with_oper(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        assert ks[0] == "OPER"

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_ends_with_quit(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        assert ks[-1] == "quit"

    @patch(
        "app.services.avl_strip_forces.build_control_deflection_commands",
        return_value=["d1 d1 5.0", "d2 d2 0.0"],
    )
    def test_includes_control_deflection_commands(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        assert "d1 d1 5.0" in ks
        assert "d2 d2 0.0" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_execute_and_output_sequence(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        x_idx = ks.index("x")
        st_idx = ks.index("st")
        fn_idx = ks.index("output.txt")
        o_idx = ks.index("o")
        assert x_idx < st_idx < fn_idx < o_idx

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_strip_forces_includes_fs(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt", include_strip_forces=True)
        assert "fs" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_no_strip_forces_excludes_fs(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt", include_strip_forces=False)
        assert "fs" not in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_extra_keystrokes_inserted(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt", extra_keystrokes=["a a 5.0"])
        assert "a a 5.0" in ks
        # Extra keystrokes should appear between control commands and "x"
        extra_idx = ks.index("a a 5.0")
        x_idx = ks.index("x")
        assert extra_idx < x_idx

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_control_overrides_passed_through(self, mock_bcc):
        runner = self._make_runner()
        overrides = {"aileron": 10.0}
        runner._build_keystrokes("output.txt", control_overrides=overrides)
        mock_bcc.assert_called_once_with(runner.airplane, overrides)

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_injects_mass_parameters(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        assert "m" in ks
        m_idx = ks.index("m")
        assert ks[m_idx + 1] == "mn 0.058"
        assert ks[m_idx + 2] == "v 20.0"
        assert ks[m_idx + 3] == "d 1.225"
        assert ks[m_idx + 4] == "g 9.81"
        assert ks[m_idx + 5] == ""  # exit mass submenu

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_injects_alpha_beta(self, mock_bcc):
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        assert "a a 5.0" in ks
        assert "b b 1.0" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_injects_nondimensional_rates(self, mock_bcc):
        op = MagicMock()
        op.velocity = 20.0
        op.alpha = 0.0
        op.beta = 0.0
        op.p = 0.5  # roll rate rad/s
        op.q = 0.1  # pitch rate rad/s
        op.r = 0.2  # yaw rate rad/s
        op.mach.return_value = 0.0
        op.atmosphere.density.return_value = 1.225

        airplane = MagicMock()
        airplane.wings = []
        airplane.b_ref = 2.0
        airplane.c_ref = 0.25

        runner = self._make_runner(airplane=airplane, op_point=op)
        ks = runner._build_keystrokes("output.txt")

        pb2v = 0.5 * 2.0 / (2 * 20.0)  # = 0.025
        qc2v = 0.1 * 0.25 / (2 * 20.0)  # = 0.000625
        rb2v = 0.2 * 2.0 / (2 * 20.0)  # = 0.01

        assert f"r r {pb2v}" in ks
        assert f"p p {qc2v}" in ks
        assert f"y y {rb2v}" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_zero_velocity_zeroes_rates(self, mock_bcc):
        op = MagicMock()
        op.velocity = 0.0
        op.alpha = 0.0
        op.beta = 0.0
        op.p = 1.0
        op.q = 1.0
        op.r = 1.0
        op.mach.return_value = 0.0
        op.atmosphere.density.return_value = 1.225

        runner = self._make_runner(op_point=op)
        ks = runner._build_keystrokes("output.txt")

        assert "r r 0" in ks
        assert "p p 0" in ks
        assert "y y 0" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_zero_span_zeroes_roll_yaw_rates(self, mock_bcc):
        airplane = MagicMock()
        airplane.wings = []
        airplane.b_ref = 0.0
        airplane.c_ref = 0.25

        op = MagicMock()
        op.velocity = 20.0
        op.alpha = 0.0
        op.beta = 0.0
        op.p = 1.0
        op.q = 1.0
        op.r = 1.0
        op.mach.return_value = 0.0
        op.atmosphere.density.return_value = 1.225

        runner = self._make_runner(airplane=airplane, op_point=op)
        ks = runner._build_keystrokes("output.txt")

        assert "r r 0" in ks  # pb2v=0 because b=0
        assert "y y 0" in ks  # rb2v=0 because b=0
        # pitch rate should still compute since c_ref != 0
        qc2v = 1.0 * 0.25 / (2 * 20.0)
        assert f"p p {qc2v}" in ks

    @patch("app.services.avl_strip_forces.build_control_deflection_commands", return_value=[])
    def test_op_params_before_control_deflections(self, mock_bcc):
        """Operating point params must appear before control deflection commands."""
        mock_bcc.return_value = ["d1 d1 5.0"]
        runner = self._make_runner()
        ks = runner._build_keystrokes("output.txt")
        alpha_idx = ks.index("a a 5.0")
        defl_idx = ks.index("d1 d1 5.0")
        assert alpha_idx < defl_idx


# =========================================================================== #
# AVLRunner._post_process_results
# =========================================================================== #


class TestPostProcessResults:
    """Verify result post-processing: key lowercasing, tot stripping, derived quantities."""

    def _make_runner(self):
        from app.services.avl_runner import AVLRunner

        airplane = MagicMock()
        airplane.s_ref = 0.5
        airplane.b_ref = 2.0
        airplane.c_ref = 0.25

        op_point = MagicMock()
        op_point.dynamic_pressure.return_value = 245.0  # ~0.5 * 1.225 * 20^2
        op_point.velocity = 20.0
        op_point.convert_axes = MagicMock(return_value=(1.0, 2.0, 3.0))

        return AVLRunner(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    def test_lowercases_canonical_keys(self):
        runner = self._make_runner()
        result = {"Alpha": 5.0, "Beta": 0.0, "Mach": 0.1}
        processed = runner._post_process_results(result)
        assert "alpha" in processed
        assert "beta" in processed
        assert "mach" in processed
        assert "Alpha" not in processed
        assert "Beta" not in processed
        assert "Mach" not in processed

    def test_strips_tot_suffix(self):
        runner = self._make_runner()
        result = {
            "CLtot": 0.5,
            "CDtot": 0.04,
            "CYtot": 0.0,
            "Cmtot": -0.02,
            "Cltot": 0.0,
            "Cntot": 0.0,
        }
        processed = runner._post_process_results(result)
        assert "CL" in processed
        assert "CD" in processed
        assert "CLtot" not in processed
        assert "CDtot" not in processed
        assert processed["CL"] == pytest.approx(0.5)
        assert processed["CD"] == pytest.approx(0.04)

    def test_computes_dimensional_forces(self):
        runner = self._make_runner()
        result = {"CL": 0.5, "CY": 0.0, "CD": 0.04}
        processed = runner._post_process_results(result)
        q = 245.0
        S = 0.5
        assert processed["L"] == pytest.approx(q * S * 0.5)
        assert processed["D"] == pytest.approx(q * S * 0.04)
        assert processed["Y"] == pytest.approx(0.0)

    def test_computes_dimensional_moments(self):
        runner = self._make_runner()
        result = {"Cl": 0.01, "Cm": -0.02, "Cn": 0.005}
        processed = runner._post_process_results(result)
        q = 245.0
        S = 0.5
        b = 2.0
        c = 0.25
        assert processed["l_b"] == pytest.approx(q * S * b * 0.01)
        assert processed["m_b"] == pytest.approx(q * S * c * (-0.02))
        assert processed["n_b"] == pytest.approx(q * S * b * 0.005)

    def test_axis_conversion_vectors_present(self):
        runner = self._make_runner()
        result = {"CL": 0.5, "CY": 0.0, "CD": 0.04, "Cl": 0.0, "Cm": -0.02, "Cn": 0.0}
        processed = runner._post_process_results(result)
        for key in ("F_w", "F_b", "F_g", "M_b", "M_g", "M_w"):
            assert key in processed, f"Missing key: {key}"

    def test_division_by_zero_produces_nan(self):
        runner = self._make_runner()
        result = {"Clb": 1.0, "Cnr": 2.0, "Clr": 0.0, "Cnb": 0.0}
        processed = runner._post_process_results(result)
        assert math.isnan(processed["Clb Cnr / Clr Cnb"])

    def test_dutch_roll_ratio_computed(self):
        runner = self._make_runner()
        result = {"Clb": -0.1, "Cnr": -0.05, "Clr": 0.02, "Cnb": 0.08}
        processed = runner._post_process_results(result)
        expected = (-0.1 * -0.05) / (0.02 * 0.08)
        assert processed["Clb Cnr / Clr Cnb"] == pytest.approx(expected)


# =========================================================================== #
# AVLRunner.run — mocked subprocess
# =========================================================================== #


class TestAVLRunnerRun:
    """Verify the full run() lifecycle with mocked subprocess."""

    def _make_runner(self, working_directory=None, timeout=30):
        from app.services.avl_runner import AVLRunner

        airplane = MagicMock()
        airplane.s_ref = 0.5
        airplane.b_ref = 2.0
        airplane.c_ref = 0.25
        airplane.wings = []

        op_point = MagicMock()
        op_point.dynamic_pressure.return_value = 245.0
        op_point.velocity = 20.0
        op_point.convert_axes = MagicMock(return_value=(1.0, 2.0, 3.0))

        return AVLRunner(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=[0.0, 0.0, 0.0],
            timeout=timeout,
            working_directory=working_directory,
        )

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_returns_parsed_result(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir)

            # Mock the subprocess to write the stability output file
            def fake_communicate(input=None, timeout=None):
                output_path = Path(tmpdir) / "output.txt"
                output_path.write_text(SAMPLE_STABILITY_OUTPUT)
                return b"", b""

            mock_proc = MagicMock()
            mock_proc.communicate = fake_communicate
            mock_popen.return_value = mock_proc

            result = runner.run(avl_file_content="FAKE AVL CONTENT")

            # Should have post-processed keys
            assert "alpha" in result
            assert result["alpha"] == pytest.approx(5.0)
            assert "CL" in result  # CLtot stripped to CL
            assert "L" in result  # dimensional force

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_writes_avl_file(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir)

            def fake_communicate(input=None, timeout=None):
                (Path(tmpdir) / "output.txt").write_text(SAMPLE_STABILITY_OUTPUT)
                return b"", b""

            mock_proc = MagicMock()
            mock_proc.communicate = fake_communicate
            mock_popen.return_value = mock_proc

            runner.run(avl_file_content="MY AVL GEOMETRY")

            avl_path = Path(tmpdir) / "airplane.avl"
            assert avl_path.exists()
            assert avl_path.read_text() == "MY AVL GEOMETRY"

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_with_strip_forces(self, mock_popen):
        from app.services.avl_strip_forces import parse_strip_forces_output

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir)

            sample_strip_stdout = """
  Surface # 1     Main Wing
     # Chordwise = 10   # Spanwise = 10     First strip =  1
     Surface area Ssurf =    0.100000     Ave. chord Cave =    0.200000
 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
     1   0.0001   0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128  -0.0759    0.214
"""

            def fake_communicate(input=None, timeout=None):
                (Path(tmpdir) / "output.txt").write_text(SAMPLE_STABILITY_OUTPUT)
                return sample_strip_stdout.encode(), b""

            mock_proc = MagicMock()
            mock_proc.communicate = fake_communicate
            mock_popen.return_value = mock_proc

            result = runner.run(
                avl_file_content="FAKE AVL CONTENT",
                include_strip_forces=True,
            )

            assert "strip_forces" in result
            assert len(result["strip_forces"]) == 1
            assert result["strip_forces"][0]["surface_name"] == "Main Wing"

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_timeout_raises_runtime_error(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir, timeout=5)

            mock_proc = MagicMock()
            # First communicate() call raises timeout, second (after kill) returns empty
            mock_proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="avl", timeout=5),
                (b"", b""),
            ]
            mock_proc.kill = MagicMock()
            mock_popen.return_value = mock_proc

            with pytest.raises(RuntimeError, match="AVL timed out"):
                runner.run(avl_file_content="FAKE AVL CONTENT")

            mock_proc.kill.assert_called_once()

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_missing_output_raises_file_not_found(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir)

            # Subprocess completes but does NOT write the output file
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_popen.return_value = mock_proc

            with pytest.raises(FileNotFoundError, match="AVL didn't produce stability output"):
                runner.run(avl_file_content="FAKE AVL CONTENT")

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_uses_temp_dir_when_no_working_directory(self, mock_popen):
        runner = self._make_runner(working_directory=None)

        def fake_communicate(input=None, timeout=None):
            # Need to find the temp dir from the Popen call
            call_args = mock_popen.call_args
            cwd = call_args.kwargs.get("cwd") or call_args[1].get("cwd")
            (Path(cwd) / "output.txt").write_text(SAMPLE_STABILITY_OUTPUT)
            return b"", b""

        mock_proc = MagicMock()
        mock_proc.communicate = fake_communicate
        mock_popen.return_value = mock_proc

        result = runner.run(avl_file_content="FAKE AVL CONTENT")
        assert "alpha" in result

    @patch("app.services.avl_runner.subprocess.Popen")
    def test_run_passes_correct_command(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self._make_runner(working_directory=tmpdir)
            runner.avl_command = "/path/to/avl"

            def fake_communicate(input=None, timeout=None):
                (Path(tmpdir) / "output.txt").write_text(SAMPLE_STABILITY_OUTPUT)
                return b"", b""

            mock_proc = MagicMock()
            mock_proc.communicate = fake_communicate
            mock_popen.return_value = mock_proc

            runner.run(avl_file_content="FAKE")

            call_args = mock_popen.call_args
            assert call_args[0][0] == ["/path/to/avl", "airplane.avl"]
            assert call_args.kwargs["cwd"] == tmpdir


# =========================================================================== #
# AVLRunner default AVL command path
# =========================================================================== #


class TestAVLRunnerDefaults:
    """Verify default configuration of AVLRunner."""

    def test_default_avl_command_resolves_to_avl_binary(self):
        from pathlib import Path

        from app.services.avl_runner import AVLRunner

        runner = AVLRunner(
            airplane=MagicMock(),
            op_point=MagicMock(),
            xyz_ref=[0, 0, 0],
        )
        assert Path(runner.avl_command).name == "avl"
        assert Path(runner.avl_command).exists()

    def test_custom_avl_command_used(self):
        from app.services.avl_runner import AVLRunner

        runner = AVLRunner(
            airplane=MagicMock(),
            op_point=MagicMock(),
            xyz_ref=[0, 0, 0],
            avl_command="/custom/avl",
        )
        assert runner.avl_command == "/custom/avl"


# =========================================================================== #
# AVLRunner.run_trim
# =========================================================================== #


class TestAVLRunnerRunTrim:
    """Verify run_trim() delegates to run() with indirect constraint keystrokes."""

    def _make_runner(self):
        from app.services.avl_runner import AVLRunner

        airplane = MagicMock()
        airplane.wings = []
        op_point = MagicMock()
        return AVLRunner(
            airplane=airplane,
            op_point=op_point,
            xyz_ref=[0.0, 0.0, 0.0],
        )

    @patch("app.services.avl_strip_forces.build_indirect_constraint_commands")
    def test_run_trim_delegates_with_extra_keystrokes(self, mock_build):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        mock_build.return_value = ["d1 PM 0.0"]
        runner = self._make_runner()
        runner.run = MagicMock(return_value={"CL": 0.5})

        tc = TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT)
        result = runner.run_trim(
            avl_file_content="FAKE",
            trim_constraints=[tc],
            control_overrides={"aileron": 5.0},
        )

        mock_build.assert_called_once_with(runner.airplane, [tc])
        runner.run.assert_called_once_with(
            avl_file_content="FAKE",
            control_overrides={"aileron": 5.0},
            extra_keystrokes=["d1 PM 0.0"],
        )
        assert result == {"CL": 0.5}
