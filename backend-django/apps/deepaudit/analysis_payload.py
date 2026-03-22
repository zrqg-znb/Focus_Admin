from __future__ import annotations

from typing import Any


SEVERITY_LEVELS = ('critical', 'high', 'medium', 'low')


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_issues(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _derive_severity_distribution(issues: list[dict[str, Any]]) -> dict[str, int]:
    distribution = {level: 0 for level in SEVERITY_LEVELS}
    for issue in issues:
        severity = str(issue.get('severity') or '').strip().lower()
        if severity in distribution:
            distribution[severity] += 1
    return distribution


def _derive_issue_types(issues: list[dict[str, Any]]) -> dict[str, int]:
    issue_types: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get('issue_type') or issue.get('vulnerability_type') or '').strip() or 'unknown'
        issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
    return issue_types


def _normalize_summary_counts(value: Any, severity_distribution: dict[str, int], issue_count: int) -> dict[str, int]:
    summary = dict(value) if isinstance(value, dict) else {}
    return {
        'total_issues': _to_int(summary.get('total_issues'), issue_count),
        'critical_issues': _to_int(summary.get('critical_issues'), severity_distribution['critical']),
        'high_issues': _to_int(summary.get('high_issues'), severity_distribution['high']),
        'medium_issues': _to_int(summary.get('medium_issues'), severity_distribution['medium']),
        'low_issues': _to_int(summary.get('low_issues'), severity_distribution['low']),
    }


def _is_wrapped_scan_result(payload: dict[str, Any]) -> bool:
    summary = payload.get('summary')
    if not isinstance(summary, dict):
        return False
    return any(
        key in summary
        for key in (
            'quality_score',
            'security_score',
            'severity_distribution',
            'issue_types',
            'metrics',
            'analysis_profile',
        )
    )


def normalize_analysis_result(value: Any) -> dict[str, Any]:
    source = dict(value) if isinstance(value, dict) else {}

    if _is_wrapped_scan_result(source):
        normalized = dict(source.get('summary') or {})
        normalized['issues'] = _normalize_issues(source.get('issues'))
        normalized['total_files'] = _to_int(source.get('total_files'), _to_int(normalized.get('total_files')))
        normalized['total_lines'] = _to_int(source.get('total_lines'), _to_int(normalized.get('total_lines')))
    else:
        normalized = dict(source)
        normalized['issues'] = _normalize_issues(source.get('issues'))

    severity_distribution = normalized.get('severity_distribution')
    if isinstance(severity_distribution, dict):
        severity_distribution = {
            level: _to_int(severity_distribution.get(level), 0)
            for level in SEVERITY_LEVELS
        }
    else:
        severity_distribution = _derive_severity_distribution(normalized['issues'])

    normalized['severity_distribution'] = severity_distribution
    normalized['summary'] = _normalize_summary_counts(
        normalized.get('summary'),
        severity_distribution,
        len(normalized['issues']),
    )

    issue_types = normalized.get('issue_types')
    if isinstance(issue_types, dict):
        normalized['issue_types'] = {
            str(key): _to_int(count, 0)
            for key, count in issue_types.items()
            if str(key).strip()
        }
    else:
        normalized['issue_types'] = _derive_issue_types(normalized['issues'])

    normalized['quality_score'] = _to_float(normalized.get('quality_score'), 0.0)
    normalized['security_score'] = _to_float(normalized.get('security_score'), 0.0)
    normalized['metrics'] = dict(normalized.get('metrics') or {})
    normalized['analysis_profile'] = dict(normalized.get('analysis_profile') or {})
    normalized['total_files'] = _to_int(normalized.get('total_files'), 0)
    normalized['total_lines'] = _to_int(normalized.get('total_lines'), 0)
    return normalized


def get_analysis_summary(value: Any) -> dict[str, Any]:
    return normalize_analysis_result(value)


def get_analysis_issue_count(value: Any) -> int:
    payload = normalize_analysis_result(value)
    return _to_int(payload.get('summary', {}).get('total_issues'), len(payload.get('issues') or []))


def get_analysis_quality_score(value: Any) -> float:
    return _to_float(normalize_analysis_result(value).get('quality_score'), 0.0)


def get_analysis_security_score(value: Any) -> float:
    return _to_float(normalize_analysis_result(value).get('security_score'), 0.0)
