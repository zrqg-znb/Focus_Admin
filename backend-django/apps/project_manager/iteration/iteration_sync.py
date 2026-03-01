from datetime import date, timedelta
import random
from typing import Any

from django.core.cache import cache

from apps.project_manager.project.project_model import Project

from .iteration_model import Iteration, IterationMetric

_IDPCA_STATES = ("I", "D", "P", "C", "A")
_REQUIREMENT_TYPES = ("sr", "dr", "ar")
_ITERATION_REQUIREMENT_CACHE_TTL_SECONDS = 14 * 24 * 60 * 60


def _get_iteration_requirement_cache_key(iteration_id: str) -> str:
    return f"iteration:requirements:{iteration_id}"


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _cache_iteration_requirements(iteration: Iteration, requirements: list[dict]) -> None:
    payload = {
        "iteration_id": str(iteration.id),
        "iteration_code": iteration.code,
        "items": requirements,
    }
    cache.set(
        _get_iteration_requirement_cache_key(str(iteration.id)),
        payload,
        _ITERATION_REQUIREMENT_CACHE_TTL_SECONDS,
    )


def get_cached_iteration_requirements(iteration: Iteration) -> list[dict]:
    key = _get_iteration_requirement_cache_key(str(iteration.id))
    cached = cache.get(key)

    if isinstance(cached, dict) and isinstance(cached.get("items"), list):
        return cached["items"]
    if isinstance(cached, list):
        return cached

    requirements = DataPlatformMock.get_iteration_requirements(
        iteration_code=iteration.code,
        sub_teams=iteration.project.sub_teams if isinstance(iteration.project.sub_teams, list) else [],
    )
    _cache_iteration_requirements(iteration, requirements)
    return requirements


def _calculate_metrics_from_requirements(requirements: list[dict]) -> dict:
    def count_items(predicate):
        return sum(1 for item in requirements if predicate(item))

    sr_num = count_items(lambda item: str(item.get("requirement_type", "")).lower() == "sr")
    dr_num = count_items(lambda item: str(item.get("requirement_type", "")).lower() == "dr")
    ar_num = count_items(lambda item: str(item.get("requirement_type", "")).lower() == "ar")

    need_break_sr_num = count_items(
        lambda item: str(item.get("requirement_type", "")).lower() == "sr"
        and _safe_bool(item.get("need_breakdown"))
    )
    need_break_dr_num = count_items(
        lambda item: str(item.get("requirement_type", "")).lower() == "dr"
        and _safe_bool(item.get("need_breakdown"))
    )
    need_break_but_un_break_sr_num = count_items(
        lambda item: str(item.get("requirement_type", "")).lower() == "sr"
        and _safe_bool(item.get("need_breakdown"))
        and not _safe_bool(item.get("is_decomposed"))
    )
    need_break_but_un_break_dr_num = count_items(
        lambda item: str(item.get("requirement_type", "")).lower() == "dr"
        and _safe_bool(item.get("need_breakdown"))
        and not _safe_bool(item.get("is_decomposed"))
    )

    metrics = {
        "sr_num": sr_num,
        "dr_num": dr_num,
        "ar_num": ar_num,
        "need_break_sr_num": need_break_sr_num,
        "need_break_dr_num": need_break_dr_num,
        "need_break_but_un_break_sr_num": need_break_but_un_break_sr_num,
        "need_break_but_un_break_dr_num": need_break_but_un_break_dr_num,
        "workload_man_dr_count": count_items(
            lambda item: str(item.get("requirement_type", "")).lower() == "dr"
            and _safe_bool(item.get("workload_man_filled"))
        ),
        "workload_loc_dr_count": count_items(
            lambda item: str(item.get("requirement_type", "")).lower() == "dr"
            and _safe_bool(item.get("workload_loc_filled"))
        ),
        "workload_man_ar_count": count_items(
            lambda item: str(item.get("requirement_type", "")).lower() == "ar"
            and _safe_bool(item.get("workload_man_filled"))
        ),
        "workload_loc_ar_count": count_items(
            lambda item: str(item.get("requirement_type", "")).lower() == "ar"
            and _safe_bool(item.get("workload_loc_filled"))
        ),
    }

    for req_type in ("ar", "dr"):
        for status in _IDPCA_STATES:
            metrics[f"{status.lower()}_state_{req_type}_num"] = count_items(
                lambda item: str(item.get("requirement_type", "")).lower() == req_type
                and str(item.get("idpca_status", "")).upper() == status
            )

    return metrics


def refresh_iteration_requirements_cache(iteration: Iteration) -> tuple[list[dict], dict]:
    requirements = DataPlatformMock.get_iteration_requirements(
        iteration_code=iteration.code,
        sub_teams=iteration.project.sub_teams if isinstance(iteration.project.sub_teams, list) else [],
    )
    _cache_iteration_requirements(iteration, requirements)
    metrics_data = _calculate_metrics_from_requirements(requirements)
    metrics_data.update(DataPlatformMock.get_iteration_quality_metrics(iteration.code))
    return requirements, metrics_data


class DataPlatformMock:
    @staticmethod
    def get_iterations(design_id: str, sub_teams: list):
        """
        模拟从数据中台获取项目的所有迭代期
        """
        today = date.today()
        base_start = today - timedelta(days=60)

        iterations = []
        for i in range(5):
            start = base_start + timedelta(days=i * 30)
            end = start + timedelta(days=29)
            code = f"{design_id}-IT-{i + 1:02d}"
            name = f"迭代-{code}"

            iterations.append(
                {
                    "name": name,
                    "code": code,
                    "start_date": start,
                    "end_date": end,
                }
            )
        return iterations

    @staticmethod
    def get_iteration_requirements(iteration_code: str, sub_teams: list) -> list[dict]:
        """
        模拟获取某个迭代的需求明细（真实场景应替换为数据湖接口）。
        """
        rng = random.Random(f"{iteration_code}:{date.today().isoformat()}:requirements")
        requirement_total = rng.randint(90, 180)
        teams = [str(team).strip() for team in sub_teams if str(team).strip()] or ["DefaultTeam"]
        owners = ["张三", "李四", "王五", "赵六", "钱七", "孙八"]
        items: list[dict] = []

        for idx in range(requirement_total):
            requirement_type = rng.choices(
                _REQUIREMENT_TYPES,
                weights=(0.35, 0.45, 0.20),
                k=1,
            )[0]

            if requirement_type == "sr":
                idpca_status = rng.choices(
                    _IDPCA_STATES,
                    weights=(0.20, 0.32, 0.30, 0.13, 0.05),
                    k=1,
                )[0]
            elif requirement_type == "dr":
                idpca_status = rng.choices(
                    _IDPCA_STATES,
                    weights=(0.10, 0.20, 0.33, 0.22, 0.15),
                    k=1,
                )[0]
            else:
                idpca_status = rng.choices(
                    _IDPCA_STATES,
                    weights=(0.08, 0.16, 0.26, 0.24, 0.26),
                    k=1,
                )[0]

            need_breakdown = requirement_type in {"sr", "dr"} and rng.random() < 0.92
            if need_breakdown:
                if idpca_status in {"C", "A"}:
                    is_decomposed = True
                else:
                    is_decomposed = rng.random() < 0.82
            else:
                is_decomposed = True

            workload_man_filled = False
            workload_loc_filled = False
            if requirement_type in {"dr", "ar"}:
                workload_man_filled = idpca_status != "I" and rng.random() < 0.90
                workload_loc_filled = idpca_status not in {"I", "D"} and rng.random() < 0.85

            items.append(
                {
                    "requirement_id": f"{iteration_code}-{requirement_type.upper()}-{idx + 1:04d}",
                    "title": f"{requirement_type.upper()}需求-{idx + 1:04d}",
                    "requirement_type": requirement_type,
                    "idpca_status": idpca_status,
                    "owner_team": rng.choice(teams),
                    "owner": rng.choice(owners),
                    "need_breakdown": need_breakdown,
                    "is_decomposed": is_decomposed,
                    "workload_man_filled": workload_man_filled,
                    "workload_loc_filled": workload_loc_filled,
                }
            )

        return items

    @staticmethod
    def get_iteration_quality_metrics(iteration_code: str) -> dict:
        """
        模拟非需求明细类的出口指标（可被真实接口替换）。
        """
        rng = random.Random(f"{iteration_code}:{date.today().isoformat()}:quality")
        return {
            "bug_fix_rate": rng.uniform(0.50, 0.95),
            "code_review_rate": rng.uniform(0.60, 0.98),
            "code_coverage_rate": rng.uniform(0.30, 0.85),
        }


def sync_project_iterations(project: Project):
    """
    同步单个项目的迭代数据
    """
    if not project.enable_iteration or not project.design_id or not project.sub_teams:
        return

    iterations_data = DataPlatformMock.get_iterations(project.design_id, project.sub_teams)

    today = date.today()
    current_iteration = None

    for it_data in iterations_data:
        iteration, _ = Iteration.objects.update_or_create(
            project=project,
            code=it_data["code"],
            defaults={
                "name": it_data["name"],
                "start_date": it_data["start_date"],
                "end_date": it_data["end_date"],
            },
        )

        is_current = it_data["start_date"] <= today <= it_data["end_date"]
        if is_current:
            current_iteration = iteration

        # 迭代结束后不再更新指标，但保证详情缓存可用
        if today > it_data["end_date"]:
            get_cached_iteration_requirements(iteration)
            continue

        _, metrics_data = refresh_iteration_requirements_cache(iteration)

        existing_metric = IterationMetric.objects.filter(
            iteration=iteration,
            record_date=today,
        ).first()

        if existing_metric:
            for key, value in metrics_data.items():
                setattr(existing_metric, key, value)
            existing_metric.save()
        else:
            latest_prev_metric = IterationMetric.objects.filter(
                iteration=iteration,
                record_date__lt=today,
            ).order_by("-record_date").first()

            if latest_prev_metric:
                metrics_data["test_automation_rate"] = latest_prev_metric.test_automation_rate
                metrics_data["test_case_execution_rate"] = (
                    latest_prev_metric.test_case_execution_rate
                )

            IterationMetric.objects.create(
                iteration=iteration,
                record_date=today,
                **metrics_data,
            )

    project.iterations.update(is_current=False)

    if current_iteration:
        current_iteration.is_current = True
        current_iteration.save(update_fields=["is_current"])


def sync_all_projects_iterations():
    """
    定时任务调用：同步所有开启了迭代统计的项目
    """
    projects = (
        Project.objects.filter(
            enable_iteration=True,
            is_deleted=False,
            is_closed=False,
        )
        .exclude(design_id__isnull=True)
        .exclude(design_id__exact="")
    )

    for project in projects:
        try:
            sync_project_iterations(project)
        except Exception as error:
            print(f"Failed to sync project {project.name}: {error}")
