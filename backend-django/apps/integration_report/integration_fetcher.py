import random
from datetime import date
from typing import Dict, Tuple, Optional


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

    def fetch_metrics(self) -> Dict[str, Tuple[Optional[float], str]]:
        """
        获取所有指标。
        返回字典: { key: (value_number, detail_url) }
        """
        # 设置随机种子，保证同一天同一个项目的数据一致性（模拟真实数据）
        seed = f"{self.config.id}-{self.record_date.isoformat()}"
        random.seed(seed)

        results = {}

        # 1. Code Check
        results["codecheck_error_num"] = self._fetch_single_metric(
            self.config.code_check_task_id, "codecheck", lambda: float(random.choice([0, 0, 0, random.randint(1, 5)]))
        )

        # 2. Bin Scope
        results["bin_scope_error_num"] = self._fetch_single_metric(
            self.config.bin_scope_task_id, "bin-scope", lambda: float(random.choice([0, 0, random.randint(1, 3)]))
        )

        # 3. Build Check
        results["build_check_error_num"] = self._fetch_single_metric(
            self.config.build_check_task_id, "build-check", lambda: float(random.choice([0, 0, random.randint(1, 2)]))
        )

        # 4. Compile Check
        results["compile_error_num"] = self._fetch_single_metric(
            self.config.compile_check_task_id, "compile-check", lambda: float(random.choice([0, random.randint(1, 2)]))
        )

        # 5. DT Metrics
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
