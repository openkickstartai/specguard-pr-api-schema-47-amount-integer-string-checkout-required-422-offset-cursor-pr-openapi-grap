"""SpecGuard — API Schema Breaking Change Detection Engine."""
import re, json
from pathlib import Path

try:
    import yaml
    def load_spec(path):
        text = Path(path).read_text()
        return yaml.safe_load(text) if str(path).endswith(('.yml', '.yaml')) else json.loads(text)
except ImportError:
    def load_spec(path):
        return json.loads(Path(path).read_text())


def _get_schema(resp):
    for ct in resp.get('content', {}):
        return resp['content'][ct].get('schema', {})
    return resp.get('schema', {})


def _diff_schema(old_s, new_s, loc, out):
    if old_s.get('type') and old_s['type'] != new_s.get('type'):
        out.append(('breaking', 'type-changed', loc,
                    f"Type: {old_s['type']} -> {new_s.get('type')}"))
    old_p = old_s.get('properties', {})
    new_p = new_s.get('properties', {})
    for f in old_p:
        if f not in new_p:
            out.append(('breaking', 'field-removed', f'{loc}.{f}',
                        f'Field "{f}" removed'))
        elif old_p[f].get('type') != new_p[f].get('type'):
            out.append(('breaking', 'field-type-changed', f'{loc}.{f}',
                        f'"{f}": {old_p[f].get("type")} -> {new_p[f].get("type")}'))


def diff_specs(old, new):
    changes = []
    op, np_ = old.get('paths', {}), new.get('paths', {})
    for path in op:
        if path not in np_:
            changes.append(('breaking', 'endpoint-removed', path, 'Endpoint removed'))
            continue
        for m in (k for k in op[path] if not k.startswith('x-')):
            if m not in np_[path]:
                changes.append(('breaking', 'method-removed',
                                f'{m.upper()} {path}', 'Method removed'))
                continue
            old_op, new_op = op[path][m], np_[path][m]
            old_params = {p['name']: p for p in old_op.get('parameters', [])}
            for p in new_op.get('parameters', []):
                if p['name'] not in old_params and p.get('required'):
                    changes.append(('breaking', 'required-param-added',
                                    f'{m.upper()} {path}',
                                    f"New required param \"{p['name']}\""))
            if not old_op.get('deprecated') and new_op.get('deprecated'):
                changes.append(('deprecation', 'operation-deprecated',
                                f'{m.upper()} {path}', 'Marked deprecated'))
            for code in old_op.get('responses', {}):
                nr = new_op.get('responses', {}).get(code)
                if nr:
                    _diff_schema(_get_schema(old_op['responses'][code]),
                                 _get_schema(nr),
                                 f'{m.upper()} {path} [{code}]', changes)
    for path in np_:
        if path not in op:
            changes.append(('compatible', 'endpoint-added', path, 'New endpoint'))
    return changes


def lint_spec(spec):
    issues = []
    for path in spec.get('paths', {}):
        segs = [s for s in path.split('/') if s and not s.startswith('{')]
        for seg in segs:
            if seg != seg.lower() or '_' in seg:
                issues.append(('warning', 'path-naming', path,
                               f'"{seg}" should be kebab-case'))
        for m in (k for k in spec['paths'][path] if not k.startswith('x-')):
            op = spec['paths'][path][m]
            if not op.get('operationId'):
                issues.append(('error', 'missing-operation-id',
                               f'{m.upper()} {path}', 'Missing operationId'))
            resp = op.get('responses', {})
            schema = _get_schema(resp.get('200', resp.get('201', {})))
            for f in schema.get('properties', {}):
                if re.search(r'[A-Z]', f) or '-' in f:
                    issues.append(('warning', 'field-naming',
                                   f'{m.upper()} {path}.{f}',
                                   f'"{f}" should be snake_case'))
    if not spec.get('info', {}).get('version'):
        issues.append(('error', 'missing-version', 'info.version',
                       'API version required'))
    return issues


def score_spec(spec):
    issues = lint_spec(spec)
    s = 100
    s -= sum(10 for lv, *_ in issues if lv == 'error')
    s -= sum(3 for lv, *_ in issues if lv == 'warning')
    return max(0, min(100, s))


def has_breaking(changes):
    return any(sev == 'breaking' for sev, *_ in changes)


def diff_files(old_path, new_path):
    """Auto-dispatch to correct diff engine based on file extension."""
    ext = Path(old_path).suffix.lower()
    if ext in ('.graphql', '.gql'):
        from graphql_diff import diff_graphql_files
        return diff_graphql_files(old_path, new_path)
    return diff_specs(load_spec(old_path), load_spec(new_path))
