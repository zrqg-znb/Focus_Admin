import random
from datetime import date, datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode


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

        # 1-4. 四个数据湖问题数指标在普通模式下走旧单 ID 接口，按领域开启后走目录遍历接口。
        results["codecheck_error_num"] = self._fetch_metric(
            self.config.code_check_task_id,
            getattr(self.config, "code_check_task_ids", []),
            "codecheck",
            lambda: float(random.choice([0, 0, 0, random.randint(1, 5)])),
        )
        results["dt_bin_error_num"] = self._fetch_metric(
            self.config.dt_bin_task_id,
            getattr(self.config, "dt_bin_task_ids", []),
            "dt-bin",
            lambda: float(random.choice([0, 0, random.randint(1, 3)])),
        )
        results["cooddy_check_error_num"] = self._fetch_metric(
            self.config.cooddy_check_task_id,
            getattr(self.config, "cooddy_check_task_ids", []),
            "cooddy-check",
            lambda: float(random.choice([0, 0, 0, random.randint(1, 4)])),
        )
        results["bin_scope_error_num"] = self._fetch_metric(
            self.config.bin_scope_task_id,
            getattr(self.config, "bin_scope_task_ids", []),
            "bin-scope",
            lambda: float(random.choice([0, 0, random.randint(1, 3)])),
        )

        # 5. Build Check
        results["build_check_error_num"] = self._fetch_single_metric(
            self.config.build_check_task_id, "build-check", lambda: float(random.choice([0, 0, random.randint(1, 2)]))
        )

        # 6. Compile Check
        results["compile_error_num"] = self._fetch_single_metric(
            self.config.compile_check_task_id, "compile-check", lambda: float(random.choice([0, random.randint(1, 2)]))
        )

        # 7. DT Metrics
        dt_url = self._get_url("dt", self.config.dt_project_id)
        if not self.config.dt_project_id:
            results.update({
                "dt_pass_rate": (None, ""),
                "dt_pass_num": (None, ""),
                "dt_line_coverage": (None, ""),
                "dt_method_coverage": (None, ""),
            })
        else:
            # 模拟偶尔获取失败
            if random.random() < 0.05:  # 5% 概率失败
                results.update({
                    "dt_pass_rate": (None, dt_url),
                    "dt_pass_num": (None, dt_url),
                    "dt_line_coverage": (None, dt_url),
                    "dt_method_coverage": (None, dt_url),
                })
            else:
                results.update({
                    "dt_pass_rate": (round(random.uniform(85, 100), 2), dt_url),
                    "dt_pass_num": (float(random.randint(20, 300)), dt_url),
                    "dt_line_coverage": (round(random.uniform(55, 95), 2), dt_url),
                    "dt_method_coverage": (round(random.uniform(50, 92), 2), dt_url),
                })

        return results

    def _fetch_single_metric(self, task_id: str, kind: str, generator) -> Tuple[Optional[float], str]:
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

    def _fetch_metric(
        self,
        legacy_task_id: str,
        task_ids,
        kind: str,
        generator,
    ) -> Tuple[Optional[float], str]:
        """按配置获取指标：关闭按领域时走旧单 ID，开启后按 ID 和目录笛卡尔积累加。"""
        if not getattr(self.config, "enable_domain_metrics", False):
            return self._fetch_single_metric((legacy_task_id or "").strip(), kind, generator)

        normalized_task_ids = []
        seen_task_ids = set()
        if isinstance(task_ids, str):
            candidates = task_ids.replace(",", "\n").splitlines()
        elif isinstance(task_ids, (list, tuple, set)):
            candidates = task_ids
        else:
            candidates = []
        for item in candidates:
            task_id = str(item).strip()
            if task_id and task_id not in seen_task_ids:
                normalized_task_ids.append(task_id)
                seen_task_ids.add(task_id)
        legacy = (legacy_task_id or "").strip()
        if not normalized_task_ids and legacy:
            normalized_task_ids.append(legacy)
        if not normalized_task_ids:
            return None, ""

        directory_set = getattr(self.config, "domain_directory_set", None)
        if not directory_set:
            return None, ""
        directory_rules = []
        for rule in directory_set.rules.filter(is_deleted=False, enabled=True).order_by(
            "sort_order",
            "sys_create_datetime",
        ):
            directory = (rule.directory or "").strip()
            if directory:
                directory_rules.append((rule.domain_name, directory))
        if not directory_rules:
            return None, ""

        total = 0.0
        has_value = False
        for task_id in normalized_task_ids:
            for domain_name, directory in directory_rules:
                # 真实环境中这里会访问按目录过滤的接口；当前保留 mock 入口和 URL 形状。
                value, url = self._fetch_domain_directory_single_metric(
                    task_id,
                    kind,
                    directory,
                    domain_name,
                    generator,
                )
                if value is not None:
                    total += value
                    has_value = True
        # 一条汇总记录对应多个 task_id 和目录，不存在可安全保存的单一详情 URL。
        # 详情链接由 history 页的领域详情接口按目录和 task_id 分别返回，避免写入 512 长度字段时溢出。
        return total if has_value else None, ""

    def _fetch_domain_directory_single_metric(
        self,
        task_id: str,
        kind: str,
        directory: str,
        domain_name: str,
        generator,
    ) -> Tuple[Optional[float], str]:
        """按单个 task_id 和目录请求领域目录指标。"""
        if not task_id or not directory:
            return None, ""
        params = {
            "id": task_id,
            "date": self.record_date.isoformat(),
            "directory": directory,
        }
        if domain_name:
            params["domain"] = domain_name
        url = f"https://dataplatform.example.com/{kind}/domain-directory?{urlencode(params)}"

        if random.random() < 0.05:
            return None, url

        try:
            return generator(), url
        except Exception:
            return None, url

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
