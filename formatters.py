"""SpecGuard output formatters for CI/CD integration.

Exports GitHubFormatter, MarkdownFormatter, JSONFormatter with a common
format(changes) -> str interface. Each formatter accepts a list of change
tuples: (severity, type, location, detail).
"""
import json
import os
from typing import List, Optional, Tuple

Change = Tuple[str, str, str, str]  # (severity, type, location, detail)

EMOJI = {'breaking': '\U0001f534', 'deprecation': '\U0001f7e1', 'compatible': '\U0001f7e2',
         'error': '\U0001f534', 'warning': '\U0001f7e1'}

GITHUB_LEVEL = {'breaking': 'error', 'deprecation': 'warning',
                'compatible': 'notice', 'error': 'error', 'warning': 'warning'}


def _count(changes: List[Change]):
    """Count changes by severity category."""
    b = sum(1 for s, *_ in changes if s == 'breaking')
    d = sum(1 for s, *_ in changes if s == 'deprecation')
    c = sum(1 for s, *_ in changes if s == 'compatible')
    return b, d, c


class GitHubFormatter:
    """Format changes as GitHub Actions workflow annotations.

    Outputs ::error, ::warning, and ::notice lines that GitHub renders
    as inline PR annotations.
    """

    def format(self, changes: List[Change]) -> str:
        if not changes:
            return '::notice ::No changes detected'
        lines = []
        for sev, typ, loc, detail in changes:
            level = GITHUB_LEVEL.get(sev, 'notice')
            lines.append(f'::{level} file={loc}::{typ}: {detail}')
        b, d, c = _count(changes)
        summary_level = 'error' if b > 0 else 'notice'
        lines.append(f'::{summary_level} ::Summary: {b} breaking, {d} deprecation, {c} compatible')
        return '\n'.join(lines)


class MarkdownFormatter:
    """Format changes as Markdown report suitable for PR comments.

    Includes a summary table with counts and a detailed list with
    emoji severity indicators.
    """

    def format(self, changes: List[Change]) -> str:
        b, d, c = _count(changes)
        lines = [
            '# \U0001f6e1\ufe0f SpecGuard Report',
            '',
            '## Summary',
            '',
            '| Category | Count |',
            '|----------|-------|',
            f'| \U0001f534 Breaking | {b} |',
            f'| \U0001f7e1 Deprecation | {d} |',
            f'| \U0001f7e2 Compatible | {c} |',
            '',
        ]
        if changes:
            lines.append('## Details')
            lines.append('')
            for sev, typ, loc, detail in changes:
                emoji = EMOJI.get(sev, '\u26aa')
                lines.append(f'- {emoji} **{typ}** `{loc}` \u2014 {detail}')
        else:
            lines.append('\u2705 No changes detected.')
        lines.append('')
        return '\n'.join(lines)


class JSONFormatter:
    """Format changes as machine-readable JSON.

    Output structure:
    {
        "summary": {"breaking": N, "deprecation": N, "compatible": N},
        "changes": [{"type": "...", "path": "...", "description": "...", "change_type": "..."}]
    }
    """

    def format(self, changes: List[Change]) -> str:
        b, d, c = _count(changes)
        result = {
            'summary': {
                'breaking': b,
                'deprecation': d,
                'compatible': c,
            },
            'changes': [
                {
                    'type': sev,
                    'path': loc,
                    'description': f'{typ}: {detail}',
                    'change_type': typ,
                }
                for sev, typ, loc, detail in changes
            ],
        }
        return json.dumps(result, indent=2)


def get_formatter(fmt: str):
    """Return a formatter instance by name.

    Returns None for 'rich' (caller should use default Rich output).
    For 'auto', detects GITHUB_ACTIONS env var.
    """
    if fmt == 'auto':
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            return GitHubFormatter()
        return None
    _map = {
        'github': GitHubFormatter,
        'markdown': MarkdownFormatter,
        'json': JSONFormatter,
        'rich': None,
    }
    cls = _map.get(fmt)
    return cls() if cls else None
