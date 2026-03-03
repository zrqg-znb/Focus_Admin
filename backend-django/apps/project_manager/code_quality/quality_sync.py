from __future__ import annotations

from datetime import date
from random import Random
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.utils import timezone

from apps.project_manager.code_quality.code_quality_model import (
    CodeMetric,
    CodeMetricNode,
    CodeModule,
    CodeNodeOwnerConfig,
)
from apps.project_manager.project.project_model import Project

DEFAULT_CLEAN_CODE_INDICATOR_TOTAL = 11
TREE_RESERVED_KEYS = {"children", "versionName", "title", "unachieved_clean_code"}

QUALITY_METRIC_LABELS: Dict[str, str] = {
    "UT_branch_coverage": "UT分支覆盖率",
    "UT_line_coverage": "UT行覆盖率",
    "UT_file_coverage": "UT文件覆盖率",
    "UT_function_coverage": "UT函数覆盖率",
    "UT_mcdc_coverage": "UT MCDC覆盖率",
    "cmetrics_pass_rate": "Cmetrics通过率",
    "code_size": "代码规模",
    "code_duplication_ratio": "代码重复率",
    "lines_per_file": "平均每文件行数",
    "line_per_method": "平均每函数行数",
    "misra_delay_num": "MISRA遗留问题数",
    "misra_dismiss_num": "MISRA豁免问题数",
    "huge_headerfile_ratio": "超大头文件占比",
    "redundant_code_kloc": "冗余代码KLOC",
    "redundant_code_total": "冗余代码总量",
    "safety_defect_density": "安全缺陷密度",
}

PERCENT_METRIC_KEYS = {
    "UT_branch_coverage",
    "UT_line_coverage",
    "UT_file_coverage",
    "UT_function_coverage",
    "UT_mcdc_coverage",
    "cmetrics_pass_rate",
    "code_duplication_ratio",
    "huge_headerfile_ratio",
}

QUALITY_WARNING_RULES: Dict[str, Dict[str, float | str]] = {
    "UT_branch_coverage": {"op": "<", "threshold": 90.0},
    "UT_line_coverage": {"op": "<", "threshold": 90.0},
    "UT_file_coverage": {"op": "<", "threshold": 90.0},
    "UT_function_coverage": {"op": "<", "threshold": 90.0},
    "UT_mcdc_coverage": {"op": "<", "threshold": 85.0},
    "cmetrics_pass_rate": {"op": "<", "threshold": 100.0},
    "code_duplication_ratio": {"op": ">", "threshold": 2.5},
    "misra_delay_num": {"op": ">", "threshold": 0},
    "huge_headerfile_ratio": {"op": ">", "threshold": 1.0},
    "redundant_code_kloc": {"op": ">", "threshold": 0},
    "redundant_code_total": {"op": ">", "threshold": 0},
    "safety_defect_density": {"op": ">", "threshold": 0},
}

DEFAULT_UNACHIEVED_ITEMS = [
    "总代码重复率未达标",
    "Misra/AutoSAR 问题数未达标",
    "UT覆盖率未达标",
    "安全缺陷密度未达标",
    "超大头文件占比未达标",
]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for candidate in ("num", "value", "rate"):
            parsed = _to_float(value.get(candidate))
            if parsed is not None:
                return parsed
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("%"):
            text = text[:-1]
        if text.lower().endswith("k"):
            text = text[:-1]
        text = text.replace(",", "")
        try:
            return float(text)
        except Exception:
            return None
    return None


def _to_display(metric_key: str, value: Any, num_value: Optional[float]) -> str:
    if num_value is None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "-"

    if metric_key in PERCENT_METRIC_KEYS:
        return f"{round(num_value, 2)}%"

    if float(num_value).is_integer():
        return str(int(num_value))
    return str(round(num_value, 4))


def _resolve_node_title(node_payload: Dict[str, Any], fallback: str = "") -> str:
    for key in ("title", "versionName", "name"):
        value = node_payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return fallback


def _check_warning(metric_key: str, num_value: Optional[float]) -> bool:
    if num_value is None:
        return False
    rule = QUALITY_WARNING_RULES.get(metric_key)
    if not rule:
        return False

    threshold = float(rule.get("threshold", 0))
    op = str(rule.get("op", "")).strip()
    if op == ">":
        return num_value > threshold
    if op == ">=":
        return num_value >= threshold
    if op == "<":
        return num_value < threshold
    if op == "<=":
        return num_value <= threshold
    if op == "==":
        return num_value == threshold
    if op == "!=":
        return num_value != threshold
    return False


def _normalize_metric_values(node_payload: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    metric_values: Dict[str, Dict[str, Any]] = {}
    warning_metrics: List[str] = []

    for key, label in QUALITY_METRIC_LABELS.items():
        if key not in node_payload:
            continue
        value = node_payload.get(key)

        num_value = _to_float(value)
        is_warning = _check_warning(key, num_value)
        if is_warning:
            warning_metrics.append(key)

        metric_values[key] = {
            "key": key,
            "label": label,
            "display": _to_display(key, value, num_value),
            "num": num_value,
            "is_warning": is_warning,
            "raw": None,
        }
    return metric_values, warning_metrics


def _compute_clean_code(node_payload: Dict[str, Any]) -> Tuple[List[str], float, bool]:
    raw_list = node_payload.get("unachieved_clean_code") or []
    if not isinstance(raw_list, list):
        raw_list = [raw_list]
    unachieved = [str(item).strip() for item in raw_list if str(item).strip()]
    clean_code_rate = max(
        0.0,
        (DEFAULT_CLEAN_CODE_INDICATOR_TOTAL - len(unachieved))
        / DEFAULT_CLEAN_CODE_INDICATOR_TOTAL,
    )
    is_clean_code = len(unachieved) == 0
    return unachieved, clean_code_rate, is_clean_code


def _find_node_by_version_name(
    root: Dict[str, Any],
    version_name: str,
) -> Optional[Dict[str, Any]]:
    target = (version_name or "").strip()
    if not target:
        return None

    stack: List[Dict[str, Any]] = [root]
    while stack:
        node = stack.pop()
        current = _resolve_node_title(node)
        if current == target:
            return node
        if current.lower() == target.lower():
            return node
        children = node.get("children") or []
        if isinstance(children, list):
            for child in reversed(children):
                if isinstance(child, dict):
                    stack.append(child)
    return None


def _metric_num(metric_values: Dict[str, Dict[str, Any]], key: str, default: float = 0.0) -> float:
    item = metric_values.get(key) or {}
    value = item.get("num")
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _build_summary_metrics(metric_values: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    summary = {}
    for key, value in metric_values.items():
        summary[key] = {
            "label": value.get("label", key),
            "display": value.get("display", ""),
            "num": value.get("num"),
            "is_warning": bool(value.get("is_warning", False)),
        }
    return summary


def _mark_deleted_node_owner_configs(
    module: CodeModule,
    valid_node_keys: set[str],
) -> None:
    query = CodeNodeOwnerConfig.objects.filter(
        module=module,
        is_deleted=False,
    )
    if valid_node_keys:
        query = query.exclude(node_key__in=list(valid_node_keys))
    query.update(
        is_deleted=True,
        sys_update_datetime=timezone.now(),
    )


def _save_empty_metric(module: CodeModule, record_date: date) -> None:
    message = f"未找到模块节点: {module.module}"
    metric, _ = CodeMetric.objects.update_or_create(
        module=module,
        record_date=record_date,
        defaults={
            "loc": 0,
            "function_count": 0,
            "dangerous_func_count": 0,
            "duplication_rate": 0.0,
            "is_clean_code": False,
            "clean_code_rate": 0.0,
            "clean_code_total": DEFAULT_CLEAN_CODE_INDICATOR_TOTAL,
            "unachieved_clean_code": [message],
            "warning_count": 1,
            "warning_metrics": ["module_not_found"],
            "total_node_count": 0,
            "warning_node_count": 1,
            "version_name": "",
            "summary_metrics": {},
            "raw_tree": {},
        },
    )
    CodeMetricNode.objects.filter(metric=metric).delete()
    _mark_deleted_node_owner_configs(module, valid_node_keys=set())


def _save_module_tree_metric(
    module: CodeModule,
    record_date: date,
    subtree: Dict[str, Any],
) -> None:
    root_name = _resolve_node_title(subtree, module.module or "unknown")
    metric_values, warning_metrics = _normalize_metric_values(subtree)
    unachieved, clean_code_rate, is_clean_code = _compute_clean_code(subtree)

    if unachieved and "clean_code" not in warning_metrics:
        warning_metrics.append("clean_code")

    metric, _ = CodeMetric.objects.update_or_create(
        module=module,
        record_date=record_date,
        defaults={
            "loc": int(_metric_num(metric_values, "code_size", 0)),
            "function_count": int(_metric_num(metric_values, "function_count", 0)),
            "dangerous_func_count": int(_metric_num(metric_values, "misra_delay_num", 0)),
            "duplication_rate": round(_metric_num(metric_values, "code_duplication_ratio", 0.0), 4),
            "is_clean_code": is_clean_code,
            "clean_code_rate": round(clean_code_rate, 6),
            "clean_code_total": DEFAULT_CLEAN_CODE_INDICATOR_TOTAL,
            "unachieved_clean_code": unachieved,
            "warning_count": len(warning_metrics),
            "warning_metrics": warning_metrics,
            "total_node_count": 0,
            "warning_node_count": 0,
            "version_name": root_name,
            "summary_metrics": _build_summary_metrics(metric_values),
            "raw_tree": {},
        },
    )

    CodeMetricNode.objects.filter(metric=metric).delete()

    total_node_count = 0
    warning_node_count = 0
    latest_node_keys: set[str] = set()

    def save_node(
        node_payload: Dict[str, Any],
        parent: Optional[CodeMetricNode],
        depth: int,
        order_index: int,
        parent_key: str,
    ) -> None:
        nonlocal total_node_count, warning_node_count
        version_name = _resolve_node_title(node_payload, "unknown")
        node_key = (
            f"{parent_key}/{version_name}"
            if parent_key
            else f"{version_name}"
        )
        latest_node_keys.add(node_key)

        node_metric_values, node_warning_metrics = _normalize_metric_values(node_payload)
        node_unachieved, node_clean_rate, node_is_clean = _compute_clean_code(node_payload)
        if node_unachieved and "clean_code" not in node_warning_metrics:
            node_warning_metrics.append("clean_code")

        node = CodeMetricNode.objects.create(
            metric=metric,
            parent=parent,
            node_key=node_key,
            version_name=version_name,
            depth=depth,
            order_index=order_index,
            metric_values=node_metric_values,
            warning_metrics=node_warning_metrics,
            warning_count=len(node_warning_metrics),
            clean_code_rate=round(node_clean_rate, 6),
            clean_code_total=DEFAULT_CLEAN_CODE_INDICATOR_TOTAL,
            unachieved_clean_code=node_unachieved,
            is_clean_code=node_is_clean,
            raw_payload={},
        )
        total_node_count += 1
        if node.warning_count > 0:
            warning_node_count += 1

        children = node_payload.get("children") or []
        if not isinstance(children, list):
            children = []
        for child_index, child in enumerate(children):
            if not isinstance(child, dict):
                continue
            save_node(
                child,
                parent=node,
                depth=depth + 1,
                order_index=child_index,
                parent_key=node_key,
            )

    save_node(
        subtree,
        parent=None,
        depth=0,
        order_index=0,
        parent_key="",
    )

    metric.total_node_count = total_node_count
    metric.warning_node_count = warning_node_count
    metric.save(update_fields=["total_node_count", "warning_node_count", "sys_update_datetime"])
    _mark_deleted_node_owner_configs(module, valid_node_keys=latest_node_keys)


class CodeQualityMock:
    @staticmethod
    def _coverage_item(rng: Random, base: float, offset: float = 0.0) -> Dict[str, Any]:
        num = max(0.0, min(100.0, base + offset + rng.uniform(-8, 6)))
        last_num = max(0.0, min(100.0, num + rng.uniform(-2, 2)))
        return {
            "last_num": round(last_num, 2),
            "num": round(num, 2),
            "rate": f"{round(num, 2)}%",
        }

    @staticmethod
    def _build_node_payload(
        rng: Random,
        version_name: str,
        level: int,
    ) -> Dict[str, Any]:
        base_coverage = 92 - level * 2
        duplication = max(0.2, rng.uniform(1.0, 5.2))
        misra_delay = max(0, int(rng.gauss(2.5, 2)))
        safety_density = max(0.0, round(rng.uniform(0.0, 1.2), 3))
        cmetrics = max(90.0, min(100.0, rng.uniform(95.0, 100.0)))

        unachieved_candidates: List[str] = []
        if duplication > 2.5:
            unachieved_candidates.append("总代码重复率未达标")
        if misra_delay > 0:
            unachieved_candidates.append("Misra/AutoSAR 问题数未达标")
        if cmetrics < 100:
            unachieved_candidates.append("Cmetrics通过率未达标")
        if base_coverage < 90:
            unachieved_candidates.append("UT覆盖率未达标")
        if safety_density > 0:
            unachieved_candidates.append("安全缺陷密度未达标")

        random_extra = [item for item in DEFAULT_UNACHIEVED_ITEMS if item not in unachieved_candidates]
        rng.shuffle(random_extra)
        if rng.random() > 0.7:
            unachieved_candidates.extend(random_extra[:1])

        code_size = max(1000, int(rng.uniform(15_000, 300_000) / (level + 1)))
        redundant_total = max(0, int(rng.gauss(30, 25)))

        return {
            "UT_branch_coverage": CodeQualityMock._coverage_item(rng, base_coverage),
            "UT_line_coverage": CodeQualityMock._coverage_item(rng, base_coverage + 1),
            "UT_file_coverage": CodeQualityMock._coverage_item(rng, base_coverage + 2),
            "UT_function_coverage": CodeQualityMock._coverage_item(rng, base_coverage - 1),
            "UT_mcdc_coverage": CodeQualityMock._coverage_item(rng, base_coverage - 3),
            "cmetrics_pass_rate": f"{round(cmetrics, 2)}%",
            "code_size": code_size,
            "code_duplication_ratio": f"{round(duplication, 2)}%",
            "lines_per_file": round(rng.uniform(80, 260), 2),
            "line_per_method": round(rng.uniform(8, 35), 2),
            "unachieved_clean_code": unachieved_candidates,
            "misra_delay_num": misra_delay,
            "misra_dismiss_num": max(0, int(rng.gauss(10, 6))),
            "huge_headerfile_ratio": f"{round(rng.uniform(0.01, 1.8), 2)}%",
            "redundant_code_kloc": round(redundant_total / 1000, 3),
            "redundant_code_total": redundant_total,
            "safety_defect_density": safety_density,
            "versionName": version_name,
            "children": [],
        }

    @staticmethod
    def get_oem_quality_tree(
        project: Project,
        oem_name: str,
        module_names: Iterable[str],
    ) -> Dict[str, Any]:
        seed = f"{project.id}|{project.code}|{oem_name}|{date.today().isoformat()}"
        rng = Random(seed)

        root_name = f"{oem_name}-ROOT"
        root = CodeQualityMock._build_node_payload(rng, root_name, level=0)
        root_children: List[Dict[str, Any]] = []

        for module_name in module_names:
            module_node = CodeQualityMock._build_node_payload(rng, module_name, level=1)
            child_count = rng.randint(1, 3)
            module_children: List[Dict[str, Any]] = []
            for idx in range(child_count):
                child_name = f"{module_name}-Sub{idx + 1}"
                child_node = CodeQualityMock._build_node_payload(rng, child_name, level=2)
                if rng.random() > 0.55:
                    grand_count = rng.randint(1, 2)
                    grand_children = []
                    for grand_idx in range(grand_count):
                        grand_name = f"{child_name}-Leaf{grand_idx + 1}"
                        grand_children.append(
                            CodeQualityMock._build_node_payload(rng, grand_name, level=3),
                        )
                    child_node["children"] = grand_children
                module_children.append(child_node)
            module_node["children"] = module_children
            root_children.append(module_node)

        root["children"] = root_children
        return root


def sync_project_quality_metrics(project: Project) -> None:
    if not project.enable_quality:
        return

    modules = list(
        CodeModule.objects.filter(project=project, is_deleted=False),
    )
    if not modules:
        return

    today = date.today()
    modules_by_oem: Dict[str, List[CodeModule]] = {}
    for module in modules:
        oem_key = (module.oem_name or "").strip() or "UNKNOWN_OEM"
        modules_by_oem.setdefault(oem_key, []).append(module)

    for oem_name, group_modules in modules_by_oem.items():
        oem_tree = CodeQualityMock.get_oem_quality_tree(
            project,
            oem_name=oem_name,
            module_names=[item.module for item in group_modules],
        )
        for module in group_modules:
            subtree = _find_node_by_version_name(oem_tree, module.module)
            if not subtree:
                _save_empty_metric(module, today)
                continue
            _save_module_tree_metric(module, today, subtree)


def sync_all_projects_quality() -> Dict[str, Any]:
    projects = Project.objects.filter(
        enable_quality=True,
        is_deleted=False,
        is_closed=False,
    )
    summary: Dict[str, Any] = {
        "total": projects.count(),
        "success": 0,
        "failed": 0,
        "failed_projects": [],
    }
    for project in projects:
        try:
            sync_project_quality_metrics(project)
            summary["success"] += 1
        except Exception as exc:
            summary["failed"] += 1
            summary["failed_projects"].append(
                {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "error": str(exc),
                }
            )
            print(f"Failed to sync quality for project {project.name}: {exc}")
    return summary
