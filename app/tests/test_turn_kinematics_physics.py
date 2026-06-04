"""gh-806: deep numeric verification of ``turn_kinematics()``.

Every assertion encodes a flight-mechanics expectation for a steady coordinated
LEVEL turn (right turn, phi > 0), validated against Sadraey "Aircraft Design: A
Systems Engineering Approach" (Wiley 2013):

    * Load factor n = 1/cos(phi).
    * Heading rate psi_dot = g * tan(phi) / V.
    * Turn radius R = V^2 / (g * tan(phi)) = V / psi_dot.
    * Body-rate decomposition at theta = 0:
          p = 0, q = psi_dot*sin(phi), r = psi_dot*cos(phi),
      with the identity sqrt(q^2 + r^2) = psi_dot.
    * Geometry: r > q for phi < 45deg, r < q for phi > 45deg, r == q at 45deg.
    * cl_factor == n (CL_turn = n * CL_1g).
    * alpha_deg != 0 (theta != 0) path: p = -psi_dot*sin(theta) != 0, and
      q, r are scaled by cos(theta).

These pin the FORMULAS, not coverage.
"""

import math

import pytest

from app.services.turn_kinematics import turn_kinematics

_G = 9.81  # must match the gravitational constant baked into the service


# --------------------------------------------------------------------------- #
# Load factor n = 1/cos(phi) at the three default banks.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bank_deg, n_expected",
    [
        (20.0, 1.0642),  # 1/cos(20deg)
        (40.0, 1.3054),  # 1/cos(40deg)
        (60.0, 2.0000),  # 1/cos(60deg) -- cos(60)=0.5 exactly
    ],
)
def test_load_factor_exact_values(bank_deg, n_expected):
    k = turn_kinematics(bank_deg, velocity=50.0)
    assert k.n == pytest.approx(n_expected, abs=1e-4)
    # cross-check against the closed form, tighter tolerance
    assert k.n == pytest.approx(1.0 / math.cos(math.radians(bank_deg)), rel=1e-12)


def test_load_factor_60deg_is_exactly_two():
    # cos(60deg) = 0.5 exactly, so n must be 2.0 to machine precision.
    assert turn_kinematics(60.0, velocity=42.0).n == pytest.approx(2.0, abs=1e-9)


def test_load_factor_monotonic_increasing_with_bank():
    n20 = turn_kinematics(20.0, 50.0).n
    n40 = turn_kinematics(40.0, 50.0).n
    n60 = turn_kinematics(60.0, 50.0).n
    # Steeper bank -> more lift needed to hold altitude -> higher load factor.
    assert 1.0 < n20 < n40 < n60


# --------------------------------------------------------------------------- #
# Heading rate psi_dot = g*tan(phi)/V and turn radius R = V^2/(g*tan phi).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bank_deg, velocity",
    [
        (30.0, 50.0),
        (45.0, 25.0),
    ],
)
def test_psi_dot_and_turn_radius_closed_form(bank_deg, velocity):
    phi = math.radians(bank_deg)
    k = turn_kinematics(bank_deg, velocity)

    psi_dot_expected = _G * math.tan(phi) / velocity
    assert k.psi_dot == pytest.approx(psi_dot_expected, rel=1e-12)
    assert k.psi_dot > 0.0  # right turn: nose swings to the right at a positive rate

    # Turn radius R = V^2 / (g*tan phi) = V / psi_dot (kinematic identity).
    radius_expected = velocity**2 / (_G * math.tan(phi))
    radius_from_psi_dot = velocity / k.psi_dot
    assert radius_from_psi_dot == pytest.approx(radius_expected, rel=1e-12)


def test_psi_dot_inversely_proportional_to_speed():
    # Same bank, double the speed -> half the heading rate (turn radius quadruples).
    slow = turn_kinematics(40.0, 30.0).psi_dot
    fast = turn_kinematics(40.0, 60.0).psi_dot
    assert slow == pytest.approx(2.0 * fast, rel=1e-12)


# --------------------------------------------------------------------------- #
# Body-rate decomposition at theta = 0: p=0, q=psi_dot*sin phi, r=psi_dot*cos phi.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bank_deg, velocity", [(20.0, 45.0), (35.0, 60.0), (60.0, 80.0)])
def test_body_rate_decomposition_theta_zero(bank_deg, velocity):
    phi = math.radians(bank_deg)
    k = turn_kinematics(bank_deg, velocity, alpha_deg=0.0)

    # No body roll rate in a steady turn at zero pitch attitude.
    assert k.p == pytest.approx(0.0, abs=1e-15)

    # Pitch rate is the sin-projection, yaw rate the cos-projection of psi_dot.
    assert k.q == pytest.approx(k.psi_dot * math.sin(phi), rel=1e-12)
    assert k.r == pytest.approx(k.psi_dot * math.cos(phi), rel=1e-12)

    # Both positive: nose-up pull (q>0) and into-turn yaw (r>0).
    assert k.q > 0.0
    assert k.r > 0.0


@pytest.mark.parametrize("bank_deg, velocity", [(20.0, 45.0), (50.0, 60.0)])
def test_rate_magnitude_identity_equals_psi_dot(bank_deg, velocity):
    # The body pitch+yaw rate vector magnitude reconstructs the heading rate:
    #   sqrt(q^2 + r^2) = psi_dot * sqrt(sin^2 + cos^2) = psi_dot.
    k = turn_kinematics(bank_deg, velocity)
    assert math.hypot(k.q, k.r) == pytest.approx(k.psi_dot, rel=1e-12)


# --------------------------------------------------------------------------- #
# Geometry of the q/r split about the 45deg crossover.
# --------------------------------------------------------------------------- #
def test_yaw_dominates_below_45deg():
    # phi < 45deg: cos(phi) > sin(phi) -> r > q (yaw rate dominates).
    k = turn_kinematics(30.0, 50.0)
    assert k.r > k.q


def test_pitch_dominates_above_45deg():
    # phi > 45deg: sin(phi) > cos(phi) -> q > r (pitch rate dominates).
    k = turn_kinematics(60.0, 50.0)
    assert k.q > k.r


def test_q_equals_r_at_45deg():
    # At exactly 45deg, sin(phi) == cos(phi) -> q == r.
    k = turn_kinematics(45.0, 50.0)
    assert k.q == pytest.approx(k.r, rel=1e-12)


# --------------------------------------------------------------------------- #
# cl_factor == n.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bank_deg", [10.0, 20.0, 40.0, 60.0])
def test_cl_factor_equals_load_factor(bank_deg):
    # CL_turn = n * CL_1g, so the reported cl_factor must equal n exactly.
    k = turn_kinematics(bank_deg, velocity=50.0)
    assert k.cl_factor == k.n


# --------------------------------------------------------------------------- #
# alpha_deg != 0 (theta != 0) path.
# --------------------------------------------------------------------------- #
def test_nonzero_alpha_introduces_roll_rate():
    bank_deg, velocity, alpha_deg = 40.0, 55.0, 6.0
    theta = math.radians(alpha_deg)
    k = turn_kinematics(bank_deg, velocity, alpha_deg=alpha_deg)

    # With a non-zero pitch attitude, the heading-rate vector picks up a body-roll
    # component p = -psi_dot*sin(theta); it is now non-zero and negative for theta>0.
    assert k.p != pytest.approx(0.0, abs=1e-9)
    assert k.p == pytest.approx(-k.psi_dot * math.sin(theta), rel=1e-12)
    assert k.p < 0.0


def test_nonzero_alpha_scales_q_and_r_by_cos_theta():
    bank_deg, velocity, alpha_deg = 40.0, 55.0, 6.0
    phi = math.radians(bank_deg)
    theta = math.radians(alpha_deg)

    base = turn_kinematics(bank_deg, velocity, alpha_deg=0.0)
    tilted = turn_kinematics(bank_deg, velocity, alpha_deg=alpha_deg)

    # psi_dot depends only on (phi, V); the pitch attitude must not change it.
    assert tilted.psi_dot == pytest.approx(base.psi_dot, rel=1e-12)

    # q and r are scaled by cos(theta) relative to the theta=0 case.
    assert tilted.q == pytest.approx(base.q * math.cos(theta), rel=1e-12)
    assert tilted.r == pytest.approx(base.r * math.cos(theta), rel=1e-12)

    # Absolute closed forms with the theta projection.
    assert tilted.q == pytest.approx(tilted.psi_dot * math.cos(theta) * math.sin(phi), rel=1e-12)
    assert tilted.r == pytest.approx(tilted.psi_dot * math.cos(theta) * math.cos(phi), rel=1e-12)

    # cos(theta) < 1, so the in-plane rates shrink slightly when pitched up.
    assert tilted.q < base.q
    assert tilted.r < base.r


def test_full_rate_vector_magnitude_preserved_under_pitch():
    # The total body-rate vector magnitude sqrt(p^2+q^2+r^2) must still equal
    # psi_dot regardless of theta, since (sin theta)^2 + (cos theta)^2 = 1.
    k = turn_kinematics(40.0, 55.0, alpha_deg=6.0)
    assert math.sqrt(k.p**2 + k.q**2 + k.r**2) == pytest.approx(k.psi_dot, rel=1e-12)
