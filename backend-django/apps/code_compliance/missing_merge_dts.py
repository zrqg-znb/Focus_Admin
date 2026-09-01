"""漏合 CR 与 DTS 关联解析，统一处理数据湖请求、快照缓存和 mock。"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Iterable
from urllib.parse import quote

import requests
from django.conf import settings

from apps.project_manager.dts_statistics import dts_statistics_services


logger = logging.getLogger(__name__)
_DTS_PREFIX = "DTS"


def _clean_text(value: Any) -> str:
    """统一清理上游字段，避免空值参与 URL 和缓存查询。"""
    return str(value or "").strip()


def _setting(name: str, default: Any = None) -> Any:
    """读取可被测试覆盖的 Django 配置。"""
    return getattr(settings, name, default)


def _mock_relation(project_id: str, change_request_iid: str) -> list[dict[str, str]]:
    """返回覆盖有效、非 DTS 和空关联场景的稳定开发 mock。"""
    suffix = _clean_text(change_request_iid)[-1:]
    if suffix == "2":
        return [{"issue_num": "BUG260706081102", "title": "Mock 非 DTS 关联"}]
    if suffix == "3":
        return []
    return [{"issue_num": f"DTS260706{_clean_text(project_id)[-4:].zfill(4)}{suffix or '0'}", "title": "Mock CR 关联 DTS"}]


def _mock_statuses(dts_nos: Iterable[str]) -> dict[str, dict[str, str]]:
    """返回稳定 DTS 状态 mock，并保留查无状态的分支。"""
    result: dict[str, dict[str, str]] = {}
    for dts_no in dts_nos:
        if dts_no.endswith("4"):
            continue
        result[dts_no] = {
            "dts_title": f"Mock DTS 简要描述 {dts_no[-4:]}",
            "dts_status_name": "开发人员实施修改",
        }
    return result


class MissingMergeDtsResolver:
    """批量解析 CR 关联 DTS，并以 DTS 快照缓存优先补齐状态。"""

    def __init__(self) -> None:
        self.force_mock = bool(_setting("CODE_COMPLIANCE_DTS_FORCE_MOCK", False))
        self.timeout = float(_setting("CODE_COMPLIANCE_DTS_API_TIMEOUT", 15))
        self.verify_ssl = bool(_setting("CODE_COMPLIANCE_DTS_API_VERIFY_SSL", True))
        self.max_workers = max(1, min(int(_setting("CODE_COMPLIANCE_DTS_RELATION_MAX_WORKERS", 5)), 10))

    def resolve_rows(self, rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, str]]:
        """按 project_id 和 CR IID 去重解析 DTS，返回可直接写入模型的快照字段。"""
        keys = {
            (_clean_text(row.get("project_id")), _clean_text(row.get("change_request_iid")))
            for row in rows
            if _clean_text(row.get("project_id")) and _clean_text(row.get("change_request_iid"))
        }
        if not keys:
            return {}

        relation_by_key: dict[tuple[str, str], dict[str, str]] = {}
        # 大范围扫描时限制关联 GET 并发，避免放大上游接口压力。
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self._fetch_relation, project_id, change_request_iid): (project_id, change_request_iid)
                for project_id, change_request_iid in keys
            }
            for future in concurrent.futures.as_completed(future_map):
                key = future_map[future]
                try:
                    issue = future.result()
                except Exception as exc:  # noqa: BLE001 - 单 CR 失败不能中断整批漏合扫描。
                    logger.warning("Resolve missing merge DTS relation failed key=%s error=%s", key, exc)
                    continue
                # 空字典代表请求成功但 CR 没有关联 DTS；异常 key 不写入，调用方保留历史快照。
                relation_by_key[key] = issue or {}

        linked_dts_nos = {item["dts_no"] for item in relation_by_key.values() if item.get("dts_no")}
        status_by_dts = self._resolve_statuses(linked_dts_nos)
        result: dict[tuple[str, str], dict[str, str]] = {}
        for key, issue in relation_by_key.items():
            if not issue:
                result[key] = {}
                continue
            status = status_by_dts.get(issue["dts_no"], {})
            result[key] = {
                "dts_no": issue["dts_no"],
                # 状态接口只返回状态时，保留关联接口返回的关联标题。
                "dts_title": _clean_text(status.get("dts_title")) or issue["dts_title"],
                "dts_status_name": _clean_text(status.get("dts_status_name")),
            }
        return result

    def _fetch_relation(self, project_id: str, change_request_iid: str) -> dict[str, str] | None:
        """查询单 CR 的关联项，并且只接受列表中的首个 DTS 单号。"""
        if self.force_mock:
            payload: Any = _mock_relation(project_id, change_request_iid)
        else:
            template = _clean_text(_setting("CODE_COMPLIANCE_DTS_RELATION_API_URL_TEMPLATE", ""))
            if not template:
                return None
            url = template.format(
                project_id=quote(project_id, safe=""),
                change_request_iid=quote(change_request_iid, safe=""),
            )
            response = requests.get(url, timeout=self.timeout, verify=self.verify_ssl)
            if response.status_code >= 400:
                raise RuntimeError(f"关联 DTS 接口响应异常: HTTP {response.status_code}")
            payload = response.json()
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            return None
        first = payload[0]
        dts_no = _clean_text(first.get("issue_num"))
        if not dts_no.startswith(_DTS_PREFIX):
            return None
        return {"dts_no": dts_no, "dts_title": _clean_text(first.get("title"))}

    def _resolve_statuses(self, dts_nos: set[str]) -> dict[str, dict[str, str]]:
        """优先读取 DTS 快照缓存，未命中的单号才批量请求 DTS 状态接口。"""
        cached = dts_statistics_services.get_dts_snapshot_statuses(dts_nos)
        unresolved = set(dts_nos) - set(cached)
        if not unresolved:
            return cached
        return {**cached, **self._fetch_statuses(unresolved)}

    def _fetch_statuses(self, dts_nos: set[str]) -> dict[str, dict[str, str]]:
        """按 DTS 单号批量查询状态接口；无返回视为未查询到。"""
        if not dts_nos:
            return {}
        if self.force_mock:
            return _mock_statuses(dts_nos)
        url = _clean_text(_setting("CODE_COMPLIANCE_DTS_STATUS_API_URL", ""))
        if not url:
            logger.warning("DTS status API URL is not configured, dts_nos=%s", sorted(dts_nos))
            return {}
        payload = {"dtsNoList": sorted(dts_nos), "fields": ["briefDes", "dtsStatusName"]}
        response = requests.post(url, json=payload, timeout=self.timeout, verify=self.verify_ssl)
        if response.status_code >= 400:
            raise RuntimeError(f"DTS 状态接口响应异常: HTTP {response.status_code}")
        body = response.json()
        rows = body.get("result") if isinstance(body, dict) else []
        result: dict[str, dict[str, str]] = {}
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            dts_no = _clean_text(row.get("dtsNo"))
            if dts_no in dts_nos:
                result[dts_no] = {
                    "dts_title": _clean_text(row.get("briefDes")),
                    "dts_status_name": _clean_text(row.get("dtsStatusName")),
                }
        return result
