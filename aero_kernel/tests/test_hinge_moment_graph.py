"""Requesting a ``per_control_surface`` quantity: every producing application is in the subtree."""

from aero_kernel.build import shipped_build
from aero_kernel.errors import KernelError
from aero_kernel.graph import Resolved


def resolved(slug: str) -> Resolved:
    found = shipped_build().graph.resolve(slug)
    assert not isinstance(found, KernelError)
    return found


def test_hinge_moment_resolves_to_every_application() -> None:
    found = resolved("hinge-moment")
    assert [p.application for p in found.producers] == [
        "aileron",
        "elevator_up",
        "elevator_down",
        "rudder",
        "flap_takeoff",
        "flap_landing",
    ]
    assert found.producer == found.producers[0]


def test_a_scalar_quantity_has_its_one_producer() -> None:
    found = resolved("stall-speed")
    assert found.producers == (found.producer,)


def test_the_subtree_of_hinge_moment_runs_every_application() -> None:
    subtree = shipped_build().graph.subtree(["hinge-moment"])
    applications = {
        n.id.application for n in subtree.nodes if n.id.formula.endswith("hinge-moments")
    }
    assert applications == {
        "aileron",
        "elevator_up",
        "elevator_down",
        "rudder",
        "flap_takeoff",
        "flap_landing",
    }


def test_another_non_scalar_quantity_is_still_refused() -> None:
    found = shipped_build().graph.resolve("polar-stall")
    assert isinstance(found, KernelError)
    assert found.code == "non_scalar_result"
