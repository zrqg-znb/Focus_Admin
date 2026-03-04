from datetime import date
from typing import List, Dict

from django.core.mail import EmailMultiAlternatives
from django.template.defaultfilters import escape

from .integration_schema import MetricCell

CODE_COLUMNS = [
    ("codecheck_error_num", "CodeCheck 错误数"),
    ("bin_scope_error_num", "Bin Scope 错误数"),
    ("build_check_error_num", "Build 检测错误数"),
    ("compile_error_num", "Compile 错误数"),
    ("tscan_error_num", "TScan 问题数"),
    ("tsan_error_num", "TSan 问题数"),
    ("cppcheck_error_num", "Cppcheck 问题数"),
    ("weggli_error_num", "Weggli 问题数"),
    ("cooddy_error_num", "Cooddy 问题数"),
    ("binexplorer_error_num", "BinExplorer 问题数"),
    ("clang_tidy_error_num", "Clang-Tidy 问题数"),
]

DT_COLUMNS = [
    ("dt_pass_rate", "DT 通过率"),
    ("dt_pass_num", "DT 通过数"),
    ("dt_line_coverage", "行覆盖率"),
    ("dt_method_coverage", "方法覆盖率"),
]


def _cell_html(cell: MetricCell) -> str:
    value = "-"
    if cell.text:
        value = escape(cell.text)
    elif cell.value is not None:
        v = f"{cell.value:g}"
        if cell.unit:
            v = f"{v}{cell.unit}"
        value = v

    color = ""
    if cell.level == "danger":
        color = "color:#dc2626;font-weight:700;"
    elif cell.level == "warning":
        color = "color:#f97316;font-weight:700;"

    style = (
        "display:inline-block;"
        "padding:2px 8px;"
        "border-radius:999px;"
        "font-size:12px;"
        "font-weight:600;"
        f"{color}"
    )
    if cell.url:
        return f'<a href="{escape(cell.url)}" style="{style}text-decoration:none;">{value}</a>'
    return f'<span style="{style}">{value}</span>'


def _render_table(title: str, subtitle: str, rows: List[Dict], columns: List[tuple[str, str]]) -> str:
    header_html = "".join([f"<th>{escape(col_name)}</th>" for _, col_name in columns])
    body_rows = []

    for row in rows:
        metric_map = {metric.key: metric for metric in row["code_metrics"] + row["dt_metrics"]}
        value_cells = "".join(
            [f"<td>{_cell_html(metric_map.get(metric_key) or MetricCell(key=metric_key, name=metric_name))}</td>" for metric_key, metric_name in columns]
        )
        body_rows.append(
            f"""
            <tr>
              <td class="project-cell">
                <div class="project-name">{escape(row["project_name"])}</div>
                <div class="project-domain">{escape(row.get("project_domain") or "")}</div>
              </td>
              {value_cells}
            </tr>
            """
        )

    if not body_rows:
        body_rows.append(
            f'<tr><td colspan="{len(columns) + 1}" class="empty-row">暂无数据</td></tr>',
        )

    return f"""
    <div class="section">
      <div class="section-title">{escape(title)}</div>
      <div class="section-subtitle">{escape(subtitle)}</div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th style="min-width:180px;">项目</th>
              {header_html}
            </tr>
          </thead>
          <tbody>
            {"".join(body_rows)}
          </tbody>
        </table>
      </div>
    </div>
    """


def build_daily_email_html(record_date: date, projects: List[Dict]) -> str:
    style = """
    <style>
      body{margin:0;padding:24px;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:#111827;}
      .container{max-width:1320px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;}
      .header{padding:20px 24px;background:linear-gradient(90deg,#eff6ff 0%,#f8fafc 100%);border-bottom:1px solid #e5e7eb;}
      .title{margin:0;font-size:20px;font-weight:700;color:#111827;}
      .sub{margin-top:6px;font-size:12px;color:#6b7280;}
      .section{padding:18px 24px 6px 24px;}
      .section-title{font-size:15px;font-weight:700;color:#111827;}
      .section-subtitle{margin-top:4px;margin-bottom:10px;font-size:12px;color:#6b7280;}
      .table-wrapper{overflow-x:auto;border:1px solid #e5e7eb;border-radius:10px;}
      table{width:100%;border-collapse:collapse;min-width:780px;background:#ffffff;}
      th,td{padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:12px;text-align:left;vertical-align:middle;white-space:nowrap;}
      th{background:#f9fafb;color:#374151;font-weight:700;}
      tbody tr:last-child td{border-bottom:none;}
      .project-cell{min-width:180px;}
      .project-name{font-weight:600;color:#111827;}
      .project-domain{font-size:11px;color:#9ca3af;margin-top:2px;}
      .empty-row{color:#9ca3af;text-align:center;padding:16px 12px;}
      .footer{padding:16px 24px 24px 24px;color:#6b7280;font-size:12px;}
      .warn-note{color:#b91c1c;font-weight:700;}
    </style>
    """

    html = f"""
    <html>
      <head>{style}</head>
      <body>
        <div class="container">
          <div class="header">
            <h2 class="title">每日集成报告 · {record_date.isoformat()}</h2>
            <div class="sub">本邮件仅包含你订阅的配置；<span class="warn-note">红色指标表示预警</span>，支持点击跳转详情。</div>
          </div>
          {_render_table("代码检测与代码扫描数据", "CODE_KEYS 大表格（含 tscan / tsan / cppcheck / weggli / cooddy / binexplorer / clang-tidy）", projects, CODE_COLUMNS)}
          {_render_table("DT 测试数据", "覆盖率、通过率与通过数", projects, DT_COLUMNS)}
          <div class="footer">
            自动发送于每日任务，如数据缺失会显示为“-”或“0”。
          </div>
        </div>
      </body>
    </html>
    """
    return html


def send_html_email(to_email: str, subject: str, html: str):
    msg = EmailMultiAlternatives(subject=subject, to=[to_email])
    msg.attach_alternative(html, "text/html")
    msg.send()
