"""gh-1479: the wing rebuilt after a telescoping spar split keeps the wing's surface type."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services import spar_insert_service


def test_persist_passes_the_surface_type_of_the_wing_to_the_converter():
    wing = SimpleNamespace(
        name="main_wing",
        surface_type="v_tail",
        surface_type_inferred=True,
        x_secs=["old"],
    )
    rebuilt = SimpleNamespace(x_secs=["a", "b", "c"])
    new_config = object()
    db = MagicMock()
    with (
        patch(
            "app.converters.model_schema_converters.wing_config_to_wing_model",
            return_value=rebuilt,
        ) as convert,
        patch("app.services.wing_service._recompute_spare_vectors") as recompute,
    ):
        spar_insert_service._persist_wing_config(db, "uuid", wing, new_config)

    convert.assert_called_once_with(
        wing_config=new_config,
        wing_name="main_wing",
        surface_type="v_tail",
        scale=spar_insert_service._MM_TO_M,
        surface_type_inferred=True,
    )
    assert wing.x_secs == ["a", "b", "c"]
    assert rebuilt.x_secs == []
    assert (wing.surface_type, wing.surface_type_inferred) == ("v_tail", True)
    db.flush.assert_called_once_with()
    recompute.assert_called_once_with(wing)
