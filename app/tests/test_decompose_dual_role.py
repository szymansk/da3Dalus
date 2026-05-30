"""gh-772 #H — decompose_dual_role: L/R reconstruction + sign-branched differential."""

from app.services.trim_enrichment_service import compute_enrichment, decompose_dual_role


class TestRuddervatorPair:
    def test_symmetric_no_differential(self):
        controls = {
            "[ruddervator]pitch_vtail_0": 3.0,
            "[ruddervator]yaw_vtail_0": 2.0,
        }
        out = decompose_dual_role(controls)
        mv = next(iter(out.values()))
        assert mv.role == "ruddervator"
        assert mv.symmetric_offset == 3.0
        assert mv.differential_throw == 2.0
        # left = 3 - 2 = 1, right = 3 + 2 = 5
        assert mv.deflection_left == 1.0
        assert mv.deflection_right == 5.0
        assert mv.differential_ratio == 1.0

    def test_two_axes_grouped_into_one_surface(self):
        controls = {
            "[ruddervator]pitch_vtail_0": 1.0,
            "[ruddervator]yaw_vtail_0": 1.0,
        }
        out = decompose_dual_role(controls)
        assert len(out) == 1  # not the old "needs 2 surfaces -> 0 differential" bug


class TestDifferentialSignBranched:
    def test_positive_command_up_going_side_throws_more(self):
        controls = {"[elevon]pitch_w_0": 3.0, "[elevon]roll_w_0": 2.0}
        mix = {"elevon:w_0": (1.0, 1.0, 2.0)}  # differential_ratio 2.0
        mv = next(iter(decompose_dual_role(controls, mix).values()))
        # right_anti=+2 (down, unscaled); left_anti=-2*2=-4 (up, scaled)
        assert mv.deflection_right == 5.0   # 3 + 2
        assert mv.deflection_left == -1.0   # 3 - 4
        # up-going (left) carries the larger antisymmetric magnitude
        assert abs(mv.deflection_left - mv.symmetric_offset) > abs(
            mv.deflection_right - mv.symmetric_offset
        )

    def test_negative_command_up_going_side_flips_but_still_larger(self):
        controls = {"[elevon]pitch_w_0": 3.0, "[elevon]roll_w_0": -2.0}
        mix = {"elevon:w_0": (1.0, 1.0, 2.0)}
        mv = next(iter(decompose_dual_role(controls, mix).values()))
        # right_anti=-2 (up, scaled ->-4); left_anti=+2 (down, unscaled)
        assert mv.deflection_right == -1.0  # 3 - 4
        assert mv.deflection_left == 5.0    # 3 + 2
        # for the opposite sign the up-going side is now the right
        assert abs(mv.deflection_right - mv.symmetric_offset) > abs(
            mv.deflection_left - mv.symmetric_offset
        )


class TestGains:
    def test_gains_scale_components(self):
        controls = {"[ruddervator]pitch_t_1": 2.0, "[ruddervator]yaw_t_1": 4.0}
        mix = {"ruddervator:t_1": (1.5, 0.5, 1.0)}
        mv = next(iter(decompose_dual_role(controls, mix).values()))
        assert mv.symmetric_offset == 3.0   # 1.5 * 2
        assert mv.differential_throw == 2.0  # 0.5 * 4


class TestAileronDifferential:
    def test_single_aileron_produces_left_right(self):
        controls = {"[aileron]Aileron": 5.0}
        mix = {"aileron:Aileron": (1.0, 1.0, 1.5)}
        out = decompose_dual_role(controls, mix)
        mv = next(iter(out.values()))
        assert mv.role == "aileron"
        assert mv.symmetric_offset == 0.0
        # right_anti=+5 (down); left_anti=-5*1.5=-7.5 (up, scaled)
        assert mv.deflection_right == 5.0
        assert mv.deflection_left == -7.5

    def test_aileron_default_ratio_symmetric(self):
        out = decompose_dual_role({"[aileron]Aileron": 5.0})
        mv = next(iter(out.values()))
        assert mv.deflection_left == -5.0
        assert mv.deflection_right == 5.0


class TestNonMixedIgnored:
    def test_elevator_not_decomposed(self):
        out = decompose_dual_role({"[elevator]Elevator": -3.0})
        assert out == {}


class TestAeroBuildupMixedSurfaceWarning:
    def _enrich(self, trim_method):
        return compute_enrichment(
            controls={"[ruddervator]pitch_t_0": 2.0, "[ruddervator]yaw_t_0": 1.0},
            limits={},
            trim_method=trim_method,
            trim_score=None,
            trim_residuals={},
            op_name="cruise",
            alpha_deg=2.0,
        )

    def test_aerobuildup_mixed_surface_emits_solver_warning(self):
        enr = self._enrich("aerobuildup")
        assert any(w.category == "solver" for w in enr.design_warnings)

    def test_avl_mixed_surface_has_no_solver_warning(self):
        enr = self._enrich("avl")
        assert not any(w.category == "solver" for w in enr.design_warnings)
