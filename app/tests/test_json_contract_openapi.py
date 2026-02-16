from fastapi.testclient import TestClient

from app.main import create_app


TARGET_JSON_ENDPOINTS: list[tuple[str, str]] = [
    ("post", "/aeroplanes"),
    ("post", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}"),
    ("get", "/aeroplanes/{aeroplane_id}/status"),
    ("get", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/html_view"),
    ("post", "/aeroplanes/{aeroplane_id}/alpha_sweep/diagram"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view"),
    ("get", "/aeroplanes/{aeroplane_id}/three_view"),
    ("get", "/aeroplanes/{aeroplane_id}/three_view/url"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url"),
    ("delete", "/aeroplanes/{aeroplane_id}"),
    ("post", "/aeroplanes/{aeroplane_id}/total_mass_kg"),
    ("put", "/aeroplanes/{aeroplane_id}/wings/{wing_name}"),
    ("post", "/aeroplanes/{aeroplane_id}/wings/{wing_name}"),
    ("delete", "/aeroplanes/{aeroplane_id}/wings/{wing_name}"),
    ("delete", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections"),
    ("post", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}"),
    ("put", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}"),
    ("delete", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}"),
    ("post", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface"),
    ("delete", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface"),
    ("put", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}"),
    ("post", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}"),
    ("delete", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}"),
    ("delete", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections"),
    ("post", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}"),
    ("put", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}"),
    ("delete", "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}"),
    ("delete", "/flight-profiles/{profile_id}"),
]

DTO_MODELED_ENDPOINTS: set[tuple[str, str]] = {
    ("post", "/aeroplanes"),
    ("post", "/aeroplanes/{aeroplane_id}/total_mass_kg"),
    ("post", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}"),
    ("get", "/aeroplanes/{aeroplane_id}/status"),
    ("get", "/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/html_view"),
    ("post", "/aeroplanes/{aeroplane_id}/alpha_sweep/diagram"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view"),
    ("get", "/aeroplanes/{aeroplane_id}/three_view"),
    ("get", "/aeroplanes/{aeroplane_id}/three_view/url"),
    ("post", "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url"),
}


def test_target_endpoints_document_json_success_responses() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()

    paths = schema["paths"]

    for method, path in TARGET_JSON_ENDPOINTS:
        assert path in paths, f"Missing path in OpenAPI: {path}"
        operation = paths[path].get(method)
        assert operation is not None, f"Missing operation in OpenAPI: {method.upper()} {path}"

        success_responses = {
            code: response
            for code, response in operation.get("responses", {}).items()
            if code.startswith("2")
        }
        assert success_responses, f"Missing success response for {method.upper()} {path}"

        for code, response in success_responses.items():
            content = response.get("content", {})
            assert "application/json" in content, (
                f"Expected application/json for {method.upper()} {path} ({code}), got {list(content.keys())}"
            )

            if (method, path) in DTO_MODELED_ENDPOINTS:
                schema = content["application/json"].get("schema", {})
                assert ("$ref" in schema) or (schema.get("type") == "object"), (
                    f"Expected object schema for {method.upper()} {path} ({code}), got {schema}"
                )


def test_set_total_mass_documents_200_and_201_models() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/aeroplanes/{aeroplane_id}/total_mass_kg"]["post"]
    responses = operation["responses"]

    assert "200" in responses
    assert "201" in responses

    for status_code in ("200", "201"):
        content = responses[status_code]["content"]["application/json"]
        model_schema = content["schema"]
        assert "$ref" in model_schema
