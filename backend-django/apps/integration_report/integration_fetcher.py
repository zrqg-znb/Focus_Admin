import os
import random
from collections import defaultdict
from datetime import date, datetime
from hashlib import sha256
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache


DOMAIN_METRICS = {
    "codecheck_error_num": (
        "code_check_task_ids",
        "code_check_task_id",
        "CodeCheck 错误数",
    ),
    "dt_bin_error_num": ("dt_bin_task_ids", "dt_bin_task_id", "DT_Bin错误数"),
    "cooddy_check_error_num": (
        "cooddy_check_task_ids",
        "cooddy_check_task_id",
        "Cooddy Check错误数",
    ),
    "bin_scope_error_num": (
        "bin_scope_task_ids",
        "bin_scope_task_id",
        "Bin Scope错误数",
    ),
}
DOMAIN_ISSUE_PAGE_SIZE = 100
DOMAIN_DETAIL_CACHE_TTL = 24 * 60 * 60
DOMAIN_DETAIL_CACHE_PREFIX = "integration_report:domain_metric_detail"


def get_domain_metric_detail_snapshot(
    config_id: str, record_date: date, metric_key: str
) -> dict:
    """读取每日采集写入的领域问题 Redis 快照。"""
    if metric_key not in DOMAIN_METRICS:
        raise ValueError("该指标不支持按责任田领域查看详情")
    snapshot = cache.get(_domain_detail_cache_key(config_id, record_date, metric_key))
    if not isinstance(snapshot, dict):
        raise LookupError("当日领域问题明细缓存不存在或已过期")
    return snapshot


def _domain_detail_cache_key(config_id: str, record_date: date, metric_key: str) -> str:
    return ":".join(
        [
            DOMAIN_DETAIL_CACHE_PREFIX,
            record_date.isoformat(),
            str(config_id),
            metric_key,
        ]
    )


class IntegrationDataFetcher:
    """
    数据获取器类，根据配置中的各个 ID 获取指标数据。
    如果获取失败，数值部分返回 None。
    """

    def __init__(self, config):
        self.config = config
        self.record_date = date.today()

    def set_date(self, record_date: date):
        self.record_date = record_date
        return self

    def _get_url(self, kind: str, task_id: str) -> str:
        if not task_id:
            return ""
        return f"https://dataplatform.example.com/{kind}?id={task_id}&date={self.record_date.isoformat()}"

    def build_dt_fuzz_payload(self, branch: str, due_date: str) -> dict:
        return {
            "versionName": self.config.dt_fuzz_version_name,
            "branch": branch,
            "pbiId": self.config.dt_fuzz_pbi_id,
            "domian-id": self.config.dt_fuzz_domain_id,
            "project-id": self.config.dt_fuzz_project_id,
            "dueDate": due_date,
        }

    def fetch_dt_fuzz(self, branch: str, due_date: str) -> dict:
        """
        Fetch DT_FUZZ tree data.
        The local environment cannot reach the data lake yet, so this method
        returns deterministic mock data while preserving the request payload
        shape that the real integration will use.
        """
        payload = self.build_dt_fuzz_payload(branch, due_date)
        return self._mock_dt_fuzz_tree(payload)

    def fetch_metrics(self) -> Dict[str, Tuple[Optional[float], str]]:
        """
        获取所有指标。
        返回字典: { key: (value_number, detail_url) }
        """
        # 设置随机种子，保证同一天同一个项目的数据一致性（模拟真实数据）
        seed = f"{self.config.id}-{self.record_date.isoformat()}"
        random.seed(seed)

        results = {}

        # 1-4. 领域模式在 Fetcher 内完成目录遍历、详情缓存和数值汇总。
        if getattr(self.config, "enable_domain_metrics", False):
            results.update(self._fetch_domain_metrics())
        else:
            results["codecheck_error_num"] = self._fetch_single_metric(
                self.config.code_check_task_id,
                "codecheck",
                lambda: float(random.choice([0, 0, 0, random.randint(1, 5)])),
            )
            results["dt_bin_error_num"] = self._fetch_single_metric(
                self.config.dt_bin_task_id,
                "dt-bin",
                lambda: float(random.choice([0, 0, random.randint(1, 3)])),
            )
            results["cooddy_check_error_num"] = self._fetch_single_metric(
                self.config.cooddy_check_task_id,
                "cooddy-check",
                lambda: float(random.choice([0, 0, 0, random.randint(1, 4)])),
            )
            results["bin_scope_error_num"] = self._fetch_single_metric(
                self.config.bin_scope_task_id,
                "bin-scope",
                lambda: float(random.choice([0, 0, random.randint(1, 3)])),
            )

        # 5. Build Check
        results["build_check_error_num"] = self._fetch_single_metric(
            self.config.build_check_task_id,
            "build-check",
            lambda: float(random.choice([0, 0, random.randint(1, 2)])),
        )

        # 6. Compile Check
        results["compile_error_num"] = self._fetch_single_metric(
            self.config.compile_check_task_id,
            "compile-check",
            lambda: float(random.choice([0, random.randint(1, 2)])),
        )

        # 7. DT Metrics
        dt_url = self._get_url("dt", self.config.dt_project_id)
        if not self.config.dt_project_id:
            results.update(
                {
                    "dt_pass_rate": (None, ""),
                    "dt_pass_num": (None, ""),
                    "dt_line_coverage": (None, ""),
                    "dt_method_coverage": (None, ""),
                }
            )
        else:
            # 模拟偶尔获取失败
            if random.random() < 0.05:  # 5% 概率失败
                results.update(
                    {
                        "dt_pass_rate": (None, dt_url),
                        "dt_pass_num": (None, dt_url),
                        "dt_line_coverage": (None, dt_url),
                        "dt_method_coverage": (None, dt_url),
                    }
                )
            else:
                results.update(
                    {
                        "dt_pass_rate": (round(random.uniform(85, 100), 2), dt_url),
                        "dt_pass_num": (float(random.randint(20, 300)), dt_url),
                        "dt_line_coverage": (round(random.uniform(55, 95), 2), dt_url),
                        "dt_method_coverage": (
                            round(random.uniform(50, 92), 2),
                            dt_url,
                        ),
                    }
                )

        return results

    def _fetch_single_metric(
        self, task_id: str, kind: str, generator
    ) -> Tuple[Optional[float], str]:
        """按旧版单 task_id 接口获取指标。"""
        url = self._get_url(kind, task_id)
        if not task_id:
            return None, ""

        # 模拟偶尔获取失败
        if random.random() < 0.05:  # 5% 概率失败
            return None, url

        try:
            return generator(), url
        except Exception:
            return None, url

    def _fetch_domain_metrics(self) -> Dict[str, Tuple[Optional[float], str]]:
        """按任务 ID 和责任田目录采集四项领域指标，并写入 Redis 明细快照。"""
        rules = self._domain_rules()
        results = {}
        for metric_key, (
            ids_field,
            legacy_field,
            metric_name,
        ) in DOMAIN_METRICS.items():
            task_ids = self._task_ids(
                getattr(self.config, ids_field, []),
                getattr(self.config, legacy_field, ""),
            )
            if not task_ids or not rules:
                results[metric_key] = (None, "")
                continue

            domains = []
            domain_map = {}
            request_cache = {}
            for domain_name, directory in rules:
                domain = domain_map.get(domain_name)
                if domain is None:
                    domain = {
                        "domain_name": domain_name,
                        "issue_count": 0,
                        "issues": [],
                    }
                    domain_map[domain_name] = domain
                    domains.append(domain)
                for task_id in task_ids:
                    cache_key = (task_id, directory)
                    if cache_key not in request_cache:
                        request_cache[cache_key] = self._fetch_domain_issue_info(
                            task_id, directory
                        )
                    info_items = request_cache[cache_key]
                    domain["issue_count"] += len(info_items)
                    domain["issues"].extend(
                        self._build_issue_rows(task_id, directory, info_items)
                    )

            total = sum(domain["issue_count"] for domain in domains)
            cache.set(
                _domain_detail_cache_key(
                    str(self.config.id), self.record_date, metric_key
                ),
                {
                    "config_id": str(self.config.id),
                    "config_name": self.config.name,
                    "project_name": (
                        self.config.project.name if self.config.project else ""
                    ),
                    "record_date": self.record_date,
                    "metric_key": metric_key,
                    "metric_name": metric_name,
                    "domain_directory_set_name": self.config.domain_directory_set.name,
                    "issue_count": total,
                    "domains": domains,
                },
                timeout=DOMAIN_DETAIL_CACHE_TTL,
            )
            results[metric_key] = (float(total), "")
        return results

    def _domain_rules(self) -> list[tuple[str, str]]:
        """返回已启用目录，保留跨领域相同目录。"""
        directory_set = getattr(self.config, "domain_directory_set", None)
        if not directory_set:
            return []
        seen_by_domain = defaultdict(set)
        rules = []
        for rule in directory_set.rules.filter(is_deleted=False, enabled=True).order_by(
            "sort_order",
            "sys_create_datetime",
        ):
            domain_name = (rule.domain_name or "").strip() or "未命名领域"
            directory = (rule.directory or "").strip()
            if directory and directory not in seen_by_domain[domain_name]:
                seen_by_domain[domain_name].add(directory)
                rules.append((domain_name, directory))
        return rules

    @staticmethod
    def _task_ids(raw_value, legacy_value: str) -> list[str]:
        values = (
            raw_value.replace(",", "\n").splitlines()
            if isinstance(raw_value, str)
            else raw_value or []
        )
        seen = set()
        task_ids = []
        for value in values:
            task_id = str(value).strip()
            if task_id and task_id not in seen:
                seen.add(task_id)
                task_ids.append(task_id)
        legacy = (legacy_value or "").strip()
        return task_ids or ([legacy] if legacy else [])

    def _fetch_domain_issue_info(self, task_id: str, directory: str) -> list[dict]:
        """拉取一个任务和目录组合的全部上游分页。"""
        page = 1
        total, items = self._request_domain_issue_page(task_id, directory, page)
        all_items = list(items)
        while len(all_items) < total:
            page += 1
            _, items = self._request_domain_issue_page(task_id, directory, page)
            all_items.extend(items)
        return all_items

    def _request_domain_issue_page(
        self, task_id: str, directory: str, page: int
    ) -> tuple[int, list[dict]]:
        """请求一页领域问题；本地未配置接口时返回稳定 Mock 数据。"""
        url = (os.environ.get("INTEGRATION_REPORT_DOMAIN_ISSUE_API_URL") or "").strip()
        if not url and settings.DEBUG:
            return self._mock_domain_issue_page(task_id, directory, page)
        response = requests.post(
            url,
            json={
                "task_id": task_id,
                "file_path": directory,
                "page": page,
                "pageSize": DOMAIN_ISSUE_PAGE_SIZE,
            },
            timeout=15,
        )
        result = response.json()["result"]
        return int(result["total"]), result["info"]

    def _mock_domain_issue_page(
        self, task_id: str, directory: str, page: int
    ) -> tuple[int, list[dict]]:
        """生成与数据湖返回结构一致的本地问题数据。"""
        seed = sha256(f"{task_id}:{directory}".encode("utf-8")).hexdigest()
        total = int(seed[:2], 16) % 3 + 1
        items = []
        for index in range(total):
            line_num = 20 + int(seed[2 + index * 2 : 4 + index * 2], 16) % 180
            file_path = f"{directory.rstrip('/')}/mock_issue_{index + 1}.c"
            items.append(
                {
                    "file_name": f"mock_issue_{index + 1}.c",
                    "file_path": file_path,
                    "function_name": f"mock_function_{index + 1}",
                    "fragment": [
                        {
                            "line_num": str(line_num),
                            "file_path": file_path,
                            "description": f"Mock 问题 {index + 1}（任务 {task_id}）",
                            "codeContextStartLine": max(1, line_num - 2),
                            "codeContext": f"// Mock data for {task_id}\nint mock_function_{index + 1}(void) {{\n  return 0;\n}}",
                        }
                    ],
                }
            )
        start = (page - 1) * DOMAIN_ISSUE_PAGE_SIZE
        return total, items[start : start + DOMAIN_ISSUE_PAGE_SIZE]

    @staticmethod
    def _build_issue_rows(
        task_id: str, directory: str, info_items: list[dict]
    ) -> list[dict]:
        """将每个文件下的 fragment 展平为表格问题行。"""
        rows = []
        for info_index, info in enumerate(info_items):
            fragments = info.get("fragment") or [{}]
            for fragment_index, fragment in enumerate(fragments):
                start_line = fragment.get("codeContextStartLine")
                rows.append(
                    {
                        "id": f"{task_id}:{directory}:{info_index}:{fragment_index}",
                        "task_id": task_id,
                        "task_detail_url": f"http://codecheck.rnd.com/{quote(task_id, safe='')}",
                        "directory": directory,
                        "file_name": str(info.get("file_name") or ""),
                        "file_path": str(
                            fragment.get("file_path") or info.get("file_path") or ""
                        ),
                        "function_name": str(info.get("function_name") or ""),
                        "line_num": str(fragment.get("line_num") or ""),
                        "description": str(fragment.get("description") or ""),
                        "code_context_start_line": (
                            int(start_line) if start_line is not None else None
                        ),
                        "code_context": str(fragment.get("codeContext") or ""),
                    }
                )
        return rows

    def _mock_dt_fuzz_tree(self, payload: dict) -> dict:
        seed = f"{self.config.id}-{payload.get('branch')}-{payload.get('dueDate')}"
        random.seed(seed)

        due_date = payload.get("dueDate") or ""
        try:
            due_day = datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S").day
        except ValueError:
            due_day = 0

        # Simulate an occasionally-late data lake so fallback behavior is visible.
        if due_day and due_day % 11 == 0:
            return {}

        name = self.config.dt_fuzz_version_name or self.config.name
        branch = payload.get("branch") or ""

        def make_node(label: str, node_type: str, depth: int) -> dict:
            api_total = random.randint(1800, 7600)
            api_cover = random.randint(int(api_total * 0.25), int(api_total * 0.9))
            sec_total = random.randint(9000, 24000)
            sec_cover = random.randint(int(sec_total * 0.55), int(sec_total * 0.96))
            lcov_total = random.randint(16000, 86000)
            lcov_cover = random.randint(int(lcov_total * 0.3), int(lcov_total * 0.84))
            case_total = random.randint(900, 2800)
            case_pass = random.randint(int(case_total * 0.35), int(case_total * 0.96))
            case_active = random.randint(int(case_total * 0.18), int(case_total * 0.76))
            node = {
                "name": label,
                "type": node_type,
                "highRiskApiCover": str(api_cover),
                "highRiskApiTotal": str(api_total),
                "highRiskApiCoverage": f"{api_cover / api_total * 100:.2f}",
                "secLineCover": str(sec_cover),
                "secLineTotal": str(sec_total),
                "secLineCoverage": f"{sec_cover / sec_total * 100:.2f}",
                "secReportUrl": f"https://dataplatform.example.com/dt-fuzz/sec?branch={branch}&node={label}",
                "lcovLineCover": str(lcov_cover),
                "lcovLineTotal": str(lcov_total),
                "lcovLineCoverage": f"{lcov_cover / lcov_total * 100:.2f}",
                "lcovReportUrl": f"https://dataplatform.example.com/dt-fuzz/lcov?branch={branch}&node={label}",
                "defectNumber": str(random.randint(0, 28)),
                "casePass": str(case_pass),
                "casePassRate": f"{case_pass / case_total * 100:.2f}",
                "caseActive": str(case_active),
                "caseActiveRate": f"{case_active / case_total * 100:.2f}",
                "caseTotal": str(case_total),
                "reportUrl": f"https://dataplatform.example.com/dt-fuzz/report?branch={branch}&node={label}",
                "children": [],
            }
            if depth > 0:
                node["children"] = [
                    make_node(f"{label} / Module {index}", "module", depth - 1)
                    for index in range(1, random.randint(2, 4))
                ]
            return node

        return make_node(name, "version", 2)
