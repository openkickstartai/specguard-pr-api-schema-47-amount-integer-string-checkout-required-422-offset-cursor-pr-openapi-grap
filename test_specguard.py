"""SpecGuard tests — breaking change detection, linting, scoring."""
import copy
import pytest
from specguard import diff_specs, lint_spec, score_spec, has_breaking

SPEC_V1 = {
    "openapi": "3.0.0",
    "info": {"title": "Payment API", "version": "1.0.0"},
    "paths": {
        "/users": {"get": {
            "operationId": "listUsers",
            "parameters": [{"name": "limit", "in": "query", "required": False}],
            "responses": {"200": {"content": {"application/json": {"schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }}}}}}
        }},
        "/orders": {"post": {
            "operationId": "createOrder",
            "parameters": [],
            "responses": {"201": {"content": {"application/json": {"schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "amount": {"type": "integer"}
                }}}}}}
        }}
    }
}


def test_endpoint_removed():
    v2 = copy.deepcopy(SPEC_V1)
    del v2["paths"]["/orders"]
    changes = diff_specs(SPEC_V1, v2)
    assert has_breaking(changes)
    assert any(t == "endpoint-removed" for _, t, *_ in changes)


def test_field_type_changed_integer_to_string():
    v2 = copy.deepcopy(SPEC_V1)
    schema = v2["paths"]["/orders"]["post"]["responses"]["201"]
    schema["content"]["application/json"]["schema"]["properties"]["amount"]["type"] = "string"
    changes = diff_specs(SPEC_V1, v2)
    assert has_breaking(changes)
    assert any(t == "field-type-changed" for _, t, *_ in changes)


def test_required_param_added():
    v2 = copy.deepcopy(SPEC_V1)
    v2["paths"]["/users"]["get"]["parameters"].append(
        {"name": "tenant_id", "in": "header", "required": True})
    changes = diff_specs(SPEC_V1, v2)
    assert has_breaking(changes)
    assert any(t == "required-param-added" for _, t, *_ in changes)


def test_response_field_removed():
    v2 = copy.deepcopy(SPEC_V1)
    props = v2["paths"]["/users"]["get"]["responses"]["200"]
    del props["content"]["application/json"]["schema"]["properties"]["email"]
    changes = diff_specs(SPEC_V1, v2)
    assert has_breaking(changes)
    assert any(t == "field-removed" for _, t, *_ in changes)


def test_compatible_endpoint_added():
    v2 = copy.deepcopy(SPEC_V1)
    v2["paths"]["/health"] = {"get": {"operationId": "health",
                                       "responses": {"200": {}}}}
    changes = diff_specs(SPEC_V1, v2)
    assert not has_breaking(changes)
    assert any(t == "endpoint-added" for _, t, *_ in changes)


def test_deprecation_detected():
    v2 = copy.deepcopy(SPEC_V1)
    v2["paths"]["/users"]["get"]["deprecated"] = True
    changes = diff_specs(SPEC_V1, v2)
    assert not has_breaking(changes)
    assert any(t == "operation-deprecated" for _, t, *_ in changes)


def test_lint_missing_operation_id():
    spec = {"openapi": "3.0.0", "info": {"title": "X", "version": "1.0"},
            "paths": {"/users": {"get": {"responses": {"200": {}}}}}}
    issues = lint_spec(spec)
    assert any(r == "missing-operation-id" for _, r, *_ in issues)


def test_lint_bad_path_and_field_naming():
    spec = {"openapi": "3.0.0", "info": {"title": "X", "version": "1.0"},
            "paths": {"/User_Profiles": {"get": {
                "operationId": "listUsers",
                "responses": {"200": {"content": {"application/json": {"schema": {
                    "type": "object",
                    "properties": {"firstName": {"type": "string"}}
                }}}}}}}}}
    issues = lint_spec(spec)
    rules = [r for _, r, *_ in issues]
    assert "path-naming" in rules
    assert "field-naming" in rules


def test_score_perfect():
    assert score_spec(SPEC_V1) == 100


def test_score_degrades():
    bad = {"openapi": "3.0.0", "info": {"title": "Bad"},
           "paths": {"/Bad_Path": {"get": {"responses": {"200": {}}}}}}
    s = score_spec(bad)
    assert s < 100
    assert 0 <= s <= 100


def test_no_changes_identical_specs():
    changes = diff_specs(SPEC_V1, copy.deepcopy(SPEC_V1))
    assert len(changes) == 0
    assert not has_breaking(changes)
