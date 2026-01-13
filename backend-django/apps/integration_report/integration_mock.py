import random
from datetime import date


def mock_fetch(project_name: str, record_date: date, task_ids: dict) -> dict:
    seed = f"{project_name}-{record_date.isoformat()}"
    random.seed(seed)

    def url(kind: str) -> str:
        return f"https://dataplatform.example.com/{kind}?project={project_name}&date={record_date.isoformat()}"

    codecheck_error_num = random.choice([0, 0, 0, random.randint(1, 5)])
    bin_scope_error_num = random.choice([0, 0, random.randint(1, 3)])
    build_check_error_num = random.choice([0, 0, random.randint(1, 2)])
    compile_error_num = random.choice([0, random.randint(1, 2)])

    dt_pass_rate = round(random.uniform(85, 100), 2)
    dt_pass_num = random.randint(20, 300)
    dt_line_coverage = round(random.uniform(55, 95), 2)
    dt_method_coverage = round(random.uniform(50, 92), 2)

    return {
        "codecheck_error_num": (float(codecheck_error_num), url("codecheck")),
        "bin_scope_error_num": (float(bin_scope_error_num), url("bin-scope")),
        "build_check_error_num": (float(build_check_error_num), url("build-check")),
        "compile_error_num": (float(compile_error_num), url("compile-check")),
        "dt_pass_rate": (float(dt_pass_rate), url("dt")),
        "dt_pass_num": (float(dt_pass_num), url("dt")),
        "dt_line_coverage": (float(dt_line_coverage), url("dt")),
        "dt_method_coverage": (float(dt_method_coverage), url("dt")),
    }

