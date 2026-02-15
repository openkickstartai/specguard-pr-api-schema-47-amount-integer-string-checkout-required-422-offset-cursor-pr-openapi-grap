"""Tests for SpecGuard output formatters.

Covers GitHubFormatter, MarkdownFormatter, JSONFormatter with 3+ tests each,
plus auto-detection logic for CI environments.
"""
import json
import os
import pytest
from formatters import (
    GitHubFormatter,
    MarkdownFormatter,
    JSONFormatter,
    get_formatter,
)

SAMPLE_CHANGES = [
    ('breaking', 'endpoint-removed', '/orders', 'Endpoint removed'),
    ('breaking', 'field-type-changed', 'POST /orders.amount',
     '"amount": integer -> string'),
    ('deprecation', 'operation-deprecated', 'GET /v1/users',
     'Operation marked deprecated'),
    ('compatible', 'endpoint-added', 'POST /webhooks',
     'New endpoint added'),
]

EMPTY_CHANGES = []


# ── GitHubFormatter ──────────────────────────────────────────────────────────

class TestGitHubFormatter:
    """GitHub Actions annotation output."""

    def test_breaking_emits_error_annotation(self):
        result = GitHubFormatter().format(SAMPLE_CHANGES)
        lines = result.splitlines()
        error_lines = [l for l in lines if l.startswith('::error ')]
        assert len(error_lines) >= 2  # 2 breaking + possibly summary
        assert 'endpoint-removed' in result

    def test_deprecation_emits_warning_annotation(self):
        result = GitHubFormatter().format(SAMPLE_CHANGES)
        assert '::warning ' in result
        assert 'operation-deprecated' in result

    def test_compatible_emits_notice_annotation(self):
        result = GitHubFormatter().format(SAMPLE_CHANGES)
        assert '::notice file=' in result
        assert 'endpoint-added' in result

    def test_annotation_file_field_present(self):
        result = GitHubFormatter().format(SAMPLE_CHANGES)
        for line in result.splitlines():
            if line.startswith('::') and 'Summary' not in line and 'No changes' not in line:
                assert 'file=' in line, f"Missing file= in: {line}"

    def test_summary_line_counts(self):
        result = GitHubFormatter().format(SAMPLE_CHANGES)
        assert '2 breaking' in result
        assert '1 deprecation' in result
        assert '1 compatible' in result

    def test_empty_changes_returns_notice(self):
        result = GitHubFormatter().format(EMPTY_CHANGES)
        assert result.startswith('::notice')
        assert 'No changes' in result


# ── MarkdownFormatter ────────────────────────────────────────────────────────

class TestMarkdownFormatter:
    """Markdown PR comment output."""

    def test_report_header(self):
        result = MarkdownFormatter().format(SAMPLE_CHANGES)
        assert result.startswith('# ')
        assert 'SpecGuard Report' in result

    def test_summary_table_counts(self):
        result = MarkdownFormatter().format(SAMPLE_CHANGES)
        assert '| \U0001f534 Breaking | 2 |' in result
        assert '| \U0001f7e1 Deprecation | 1 |' in result
        assert '| \U0001f7e2 Compatible | 1 |' in result

    def test_details_section_present(self):
        result = MarkdownFormatter().format(SAMPLE_CHANGES)
        assert '## Details' in result
        assert '`/orders`' in result
        assert '`POST /webhooks`' in result

    def test_emoji_severity_indicators(self):
        result = MarkdownFormatter().format(SAMPLE_CHANGES)
        assert '\U0001f534' in result  # red circle for breaking
        assert '\U0001f7e1' in result  # yellow circle for deprecation
        assert '\U0001f7e2' in result  # green circle for compatible

    def test_empty_changes_no_details(self):
        result = MarkdownFormatter().format(EMPTY_CHANGES)
        assert '## Details' not in result
        assert 'No changes detected' in result

    def test_bold_change_type(self):
        result = MarkdownFormatter().format(SAMPLE_CHANGES)
        assert '**endpoint-removed**' in result
        assert '**endpoint-added**' in result


# ── JSONFormatter ────────────────────────────────────────────────────────────

class TestJSONFormatter:
    """Machine-readable JSON output."""

    def test_valid_json_output(self):
        result = JSONFormatter().format(SAMPLE_CHANGES)
        data = json.loads(result)  # must not raise
        assert isinstance(data, dict)

    def test_summary_counts_correct(self):
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        assert data['summary']['breaking'] == 2
        assert data['summary']['deprecation'] == 1
        assert data['summary']['compatible'] == 1

    def test_changes_array_length(self):
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        assert len(data['changes']) == 4

    def test_change_entry_required_fields(self):
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        for change in data['changes']:
            assert 'type' in change
            assert 'path' in change
            assert 'description' in change

    def test_schema_top_level_keys(self):
        """Validate JSON output matches expected schema structure."""
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        assert set(data.keys()) == {'summary', 'changes'}
        assert set(data['summary'].keys()) == {'breaking', 'deprecation', 'compatible'}

    def test_schema_value_types(self):
        """All summary values must be integers, all change types valid."""
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        for v in data['summary'].values():
            assert isinstance(v, int)
        valid_types = {'breaking', 'deprecation', 'compatible'}
        for change in data['changes']:
            assert change['type'] in valid_types
            assert isinstance(change['path'], str)
            assert isinstance(change['description'], str)

    def test_empty_changes_valid_json(self):
        data = json.loads(JSONFormatter().format(EMPTY_CHANGES))
        assert data['summary'] == {'breaking': 0, 'deprecation': 0, 'compatible': 0}
        assert data['changes'] == []

    def test_change_type_field_present(self):
        """Each change should also include change_type for programmatic use."""
        data = json.loads(JSONFormatter().format(SAMPLE_CHANGES))
        assert data['changes'][0]['change_type'] == 'endpoint-removed'
        assert data['changes'][3]['change_type'] == 'endpoint-added'


# ── get_formatter / auto-detection ───────────────────────────────────────────

class TestGetFormatter:
    """Factory function and GITHUB_ACTIONS auto-detection."""

    def test_auto_github_env_returns_github_formatter(self, monkeypatch):
        monkeypatch.setenv('GITHUB_ACTIONS', 'true')
        fmt = get_formatter('auto')
        assert isinstance(fmt, GitHubFormatter)

    def test_auto_no_env_returns_none(self, monkeypatch):
        monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
        fmt = get_formatter('auto')
        assert fmt is None  # caller uses Rich

    def test_explicit_github(self):
        assert isinstance(get_formatter('github'), GitHubFormatter)

    def test_explicit_markdown(self):
        assert isinstance(get_formatter('markdown'), MarkdownFormatter)

    def test_explicit_json(self):
        assert isinstance(get_formatter('json'), JSONFormatter)

    def test_explicit_rich_returns_none(self):
        assert get_formatter('rich') is None

    def test_auto_github_false_returns_none(self, monkeypatch):
        monkeypatch.setenv('GITHUB_ACTIONS', 'false')
        fmt = get_formatter('auto')
        assert fmt is None
