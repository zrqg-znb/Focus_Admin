from __future__ import annotations

import os
from typing import Any

from apps.deepaudit.scenario_profile import is_inventory_profile
from apps.deepaudit.serialization import normalize_json_payload


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def inventory_items_count(report: dict[str, Any] | None) -> int:
    payload = _dict(report)
    return len(_list(payload.get("items")))


def extract_inventory_report(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = _dict(payload)
    if (
        isinstance(data.get("items"), list)
        and (
            isinstance(data.get("scenario"), dict)
            or isinstance(data.get("scope"), dict)
            or isinstance(data.get("overview"), dict)
        )
    ):
        return data

    direct = _dict(data.get("inventory_report"))
    if direct:
        return direct

    summary = _dict(data.get("summary"))
    nested = _dict(summary.get("inventory_report"))
    if nested:
        return nested

    for value in data.values():
        if isinstance(value, dict):
            nested = extract_inventory_report(value)
            if nested:
                return nested
    return {}


def build_empty_inventory_report(
    *,
    scenario_profile: dict[str, Any] | None,
    target_files: list[str] | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    scenario = _dict(scenario_profile)
    return {
        "scenario": {
            "key": scenario.get("scenario_key") or scenario.get("resolved_scenario_key") or "",
            "name": scenario.get("scenario_name") or "",
            "objective": scenario.get("objective_type") or "inventory",
            "result_mode": "inventory" if is_inventory_profile(scenario) else "audit",
        },
        "scope": {
            "target_files": list(target_files or []),
            "keywords": list(scenario.get("focus_keywords") or []),
            "description": scenario.get("focus_summary") or scenario.get("description") or "",
            "project_root": project_root or "",
        },
        "overview": {
            "summary": "",
            "coverage": "",
            "limitations": "",
        },
        "items": [],
        "chains": [],
        "resources": [],
        "qa": {
            "status": "unchecked",
            "checked_items": 0,
            "warnings": [],
        },
    }


def _normalize_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return {
            "file_path": "",
            "line_start": None,
            "symbol": "",
            "item_type": "note",
            "evidence": text,
            "risk_note": "",
            "suggested_followup": "",
        }
    if not isinstance(item, dict):
        return None
    file_path = _text(item.get("file_path") or item.get("file"))
    line_start = _int_or_none(item.get("line_start") or item.get("line") or item.get("line_number"))
    return {
        "file_path": file_path,
        "line_start": line_start,
        "line_end": _int_or_none(item.get("line_end")) or line_start,
        "symbol": _text(item.get("symbol") or item.get("function") or item.get("name")),
        "item_type": _text(item.get("item_type") or item.get("type"), "code_reference"),
        "evidence": _text(item.get("evidence") or item.get("code_snippet") or item.get("description")),
        "risk_note": _text(item.get("risk_note") or item.get("risk") or item.get("note")),
        "suggested_followup": _text(item.get("suggested_followup") or item.get("followup") or item.get("suggestion")),
        "extras": normalize_json_payload(_dict(item.get("extras"))),
    }


def _file_lines(project_root: str, relative_path: str) -> list[str] | None:
    if not project_root or not relative_path:
        return None
    root = os.path.realpath(project_root)
    full_path = os.path.realpath(os.path.join(root, relative_path))
    if os.path.commonpath([root, full_path]) != root or not os.path.isfile(full_path):
        return None
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read().splitlines()
    except OSError:
        return None


def validate_inventory_report(report: dict[str, Any], *, project_root: str | None = None) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    checked = 0
    for index, item in enumerate(_list(report.get("items")), start=1):
        if not isinstance(item, dict):
            continue
        file_path = _text(item.get("file_path"))
        line_start = _int_or_none(item.get("line_start"))
        evidence = _text(item.get("evidence"))
        if not file_path:
            warnings.append({"index": index, "type": "missing_file_path", "message": "条目缺少文件路径"})
            continue
        lines = _file_lines(project_root or "", file_path)
        if lines is None:
            warnings.append({"index": index, "type": "missing_file", "file_path": file_path, "message": "文件不存在或不可读取"})
            continue
        checked += 1
        if line_start and line_start > len(lines):
            warnings.append({"index": index, "type": "invalid_line", "file_path": file_path, "line_start": line_start, "message": "行号超出文件范围"})
        if evidence and line_start:
            start = max(line_start - 4, 0)
            end = min(line_start + 3, len(lines))
            nearby = "\n".join(lines[start:end])
            if evidence not in nearby and evidence not in "\n".join(lines):
                warnings.append({"index": index, "type": "evidence_mismatch", "file_path": file_path, "line_start": line_start, "message": "证据片段未在文件附近匹配"})

    report["qa"] = {
        **_dict(report.get("qa")),
        "status": "passed" if not warnings else "warnings",
        "checked_items": checked,
        "warnings": warnings,
    }
    return report


def normalize_inventory_report(
    raw_report: dict[str, Any] | None,
    *,
    scenario_profile: dict[str, Any] | None,
    target_files: list[str] | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    report = build_empty_inventory_report(
        scenario_profile=scenario_profile,
        target_files=target_files,
        project_root=project_root,
    )
    raw = _dict(raw_report)
    if raw:
        report["scenario"] = {**report["scenario"], **_dict(raw.get("scenario"))}
        report["scope"] = {**report["scope"], **_dict(raw.get("scope"))}
        report["overview"] = {**report["overview"], **_dict(raw.get("overview"))}
        report["items"] = [
            item
            for item in (_normalize_item(value) for value in _list(raw.get("items")))
            if item
        ]
        report["chains"] = _list(raw.get("chains"))
        report["resources"] = _list(raw.get("resources"))
        report["qa"] = {**report["qa"], **_dict(raw.get("qa"))}
    return validate_inventory_report(normalize_json_payload(report), project_root=project_root)
