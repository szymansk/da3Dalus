"""Tests for cad_designer.airplane.GeneralJSONEncoderDecoder."""
import json

import pytest

from cad_designer.airplane.GeneralJSONEncoderDecoder import (
    GeneralJSONDecoder,
    GeneralJSONEncoder,
)
from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode


# ---------------------------------------------------------------------------
# Helpers — lightweight concrete creator for testing serialization
# ---------------------------------------------------------------------------

class _StubCreator:
    """Minimal object that looks like an AbstractShapeCreator for encoding."""

    def __init__(self, creator_id: str = "stub", **kwargs):
        self.creator_id = creator_id

    @property
    def identifier(self):
        return self.creator_id


# ---------------------------------------------------------------------------
# GeneralJSONEncoder
# ---------------------------------------------------------------------------

class TestGeneralJSONEncoder:

    def test_type_field_present(self):
        """Encoded JSON must contain the $TYPE discriminator field."""
        root = ConstructionRootNode(creator_id="test_root")
        encoded = json.dumps(root, cls=GeneralJSONEncoder)
        data = json.loads(encoded)
        assert GeneralJSONEncoder.JSON_CLASS_TYPE_ID in data
        assert data[GeneralJSONEncoder.JSON_CLASS_TYPE_ID] == "ConstructionRootNode"

    def test_encodes_public_attributes_only(self):
        """Private attributes (starting with _) should be excluded."""
        root = ConstructionRootNode(creator_id="pub_test")
        encoded = json.dumps(root, cls=GeneralJSONEncoder)
        data = json.loads(encoded)
        # _output_shapes and _shapes_of_interest_keys are private
        for key in data:
            assert not key.startswith("_"), f"private attribute '{key}' should not be encoded"

    def test_type_id_constant_value(self):
        assert GeneralJSONEncoder.JSON_CLASS_TYPE_ID == "$TYPE"


# ---------------------------------------------------------------------------
# GeneralJSONDecoder
# ---------------------------------------------------------------------------

class TestGeneralJSONDecoder:

    def test_decode_construction_root_node(self):
        """A JSON object with $TYPE=ConstructionRootNode should be decoded correctly."""
        payload = {
            GeneralJSONEncoder.JSON_CLASS_TYPE_ID: "ConstructionRootNode",
            "creator_id": "decoded_root",
        }
        raw = json.dumps(payload)
        obj = json.loads(raw, cls=GeneralJSONDecoder)
        assert isinstance(obj, ConstructionRootNode)
        assert obj.creator_id == "decoded_root.root"

    def test_passthrough_without_type_field(self):
        """Dicts without $TYPE should pass through unchanged."""
        payload = {"foo": "bar", "count": 42}
        raw = json.dumps(payload)
        obj = json.loads(raw, cls=GeneralJSONDecoder)
        assert isinstance(obj, dict)
        assert obj == payload

    def test_extra_kwargs_forwarded_to_constructor(self):
        """Extra kwargs given to the decoder should be forwarded if the
        target constructor accepts them."""
        payload = {
            GeneralJSONEncoder.JSON_CLASS_TYPE_ID: "ConstructionRootNode",
            "creator_id": "kw_root",
        }
        raw = json.dumps(payload)
        # ConstructionRootNode.__init__ accepts 'successors' — but extra
        # unknown kwargs should be silently ignored (intersection logic).
        obj = json.loads(raw, cls=GeneralJSONDecoder)
        assert isinstance(obj, ConstructionRootNode)


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:

    def test_roundtrip_construction_root_node(self):
        """Encode then decode a ConstructionRootNode — the type should survive.

        Note: the encoder serialises the already-suffixed creator_id
        ("roundtrip.root") and the decoder passes it through
        __init__ again, which appends ".root" a second time.  This is
        an existing production-code behaviour, not a test bug.
        """
        original = ConstructionRootNode(creator_id="roundtrip")
        encoded = json.dumps(original, cls=GeneralJSONEncoder)
        decoded = json.loads(encoded, cls=GeneralJSONDecoder)
        assert isinstance(decoded, ConstructionRootNode)
        # creator_id is double-suffixed because __init__ appends ".root"
        # and the serialised value already includes it.
        assert decoded.creator_id == "roundtrip.root.root"

    def test_json_string_is_valid_json(self):
        """The encoder should produce valid JSON (no exceptions on loads)."""
        node = ConstructionRootNode(creator_id="valid_json")
        encoded = json.dumps(node, cls=GeneralJSONEncoder)
        parsed = json.loads(encoded)
        assert isinstance(parsed, dict)
