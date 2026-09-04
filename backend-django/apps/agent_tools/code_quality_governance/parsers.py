import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .models import SEVERITIES


@dataclass(frozen=True)
class ParsedFinding:
    """单条第三方问题的规范化结果。"""

    identity_key: str
    issue_key: str
    fingerprint: str
    rule_id: str
    rule_version: str
    category: str
    severity: str
    confidence: float | None
    file_path: str
    start_line: int
    end_line: int
    message: str
    evidence: list[dict[str, Any]]
    identity: dict[str, Any]
    legacy_fingerprints: list[str]
    raw_finding: dict[str, Any]


@dataclass(frozen=True)
class ParsedReport:
    """第三方扫描报告的规范化结果。"""

    repository: str
    complete: bool
    raw_created_at: str
    summary: dict[str, int]
    findings: list[ParsedFinding]


def _as_bool(value: Any) -> bool:
    """兼容第三方工具使用字符串或布尔值表达扫描完成状态。"""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {'false', '0', 'no', 'incomplete'}


def _as_int(value: Any, default: int = 0) -> int:
    """安全转换行号和统计数字。"""
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any) -> float | None:
    """安全转换可选置信度。"""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _fallback_identity(finding: dict[str, Any]) -> str:
    """在第三方身份字段缺失时生成稳定的内容身份。"""
    location = finding.get('location') or {}
    payload = {
        'rule_id': finding.get('rule_id', ''),
        'path': location.get('path', ''),
        'start_line': _as_int(location.get('start_line')),
        'end_line': _as_int(location.get('end_line')),
        'message': str(finding.get('message') or '').strip(),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return f'platform:{digest}'


def parse_report(payload: dict[str, Any]) -> ParsedReport:
    """校验并解析第三方 JSON 报告，不对原始字段做破坏性改写。"""
    if not isinstance(payload, dict):
        raise ValueError('扫描报告必须是 JSON 对象')
    raw_findings = payload.get('findings')
    if not isinstance(raw_findings, list):
        raise ValueError('扫描报告缺少有效的 findings 数组')

    parsed: list[ParsedFinding] = []
    for index, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f'第 {index} 条 finding 不是 JSON 对象')
        location = raw.get('location') or {}
        if not isinstance(location, dict):
            raise ValueError(f'第 {index} 条 finding 的 location 无效')
        identity = raw.get('identity') or {}
        if not isinstance(identity, dict):
            identity = {}
        legacy = raw.get('legacy_fingerprints') or []
        if not isinstance(legacy, list):
            legacy = [str(legacy)]
        issue_key = str(identity.get('issue_key') or '').strip()
        fingerprint = str(raw.get('fingerprint') or '').strip()
        identity_key = issue_key or next((str(item).strip() for item in legacy if str(item).strip()), '') or fingerprint or _fallback_identity(raw)
        severity = str(raw.get('severity') or 'info').strip().lower()
        if severity not in SEVERITIES:
            severity = 'info'
        evidence = raw.get('evidence') or []
        if not isinstance(evidence, list):
            evidence = [evidence]
        parsed.append(ParsedFinding(
            identity_key=identity_key,
            issue_key=issue_key,
            fingerprint=fingerprint,
            rule_id=str(raw.get('rule_id') or ''),
            rule_version=str(raw.get('rule_version') or ''),
            category=str(identity.get('category') or ''),
            severity=severity,
            confidence=_as_float(raw.get('confidence')),
            file_path=str(location.get('path') or ''),
            start_line=_as_int(location.get('start_line')),
            end_line=_as_int(location.get('end_line')), 
            message=str(raw.get('message') or ''),
            evidence=evidence,
            identity=identity,
            legacy_fingerprints=[str(item) for item in legacy],
            raw_finding=raw,
        ))
    summary_raw = payload.get('summary') or {}
    summary = {severity: _as_int(summary_raw.get(severity), sum(item.severity == severity for item in parsed)) for severity in SEVERITIES}
    summary['file_scanned'] = _as_int(summary_raw.get('file_scanned'))
    return ParsedReport(
        repository=str(payload.get('repository') or ''),
        complete=_as_bool(payload.get('complete', True)),
        raw_created_at=str(payload.get('created_at') or ''),
        summary=summary,
        findings=parsed,
    )
