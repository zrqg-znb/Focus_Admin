from datetime import date
from typing import List, Dict

from django.core.mail import EmailMultiAlternatives
from django.template.defaultfilters import escape

from .integration_schema import MetricCell


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

    if cell.url:
        return f'<a href="{escape(cell.url)}" style="{color}text-decoration:none;">{value}</a>'
    return f'<span style="{color}">{value}</span>'


def build_daily_email_html(record_date: date, projects: List[Dict]) -> str:
    style = """
    <style>
      body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial;line-height:1.5;color:#111827;}
      .card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:12px 0;background:#ffffff;}
      h2{margin:0 0 10px 0;font-size:16px;}
      table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border:1px solid #e5e7eb;border-radius:12px;}
      th,td{padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;vertical-align:middle;}
      th{background:#f9fafb;text-align:left;color:#374151;font-weight:700;}
      tr:last-child td{border-bottom:none;}
      .muted{color:#6b7280;font-size:12px;}
      .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;}
      .badge-ok{background:#ecfdf5;color:#047857;}
      .badge-warn{background:#fff7ed;color:#c2410c;}
      .badge-bad{background:#fef2f2;color:#b91c1c;}
    </style>
    """

    def project_row(cells: Dict[str, MetricCell], keys: List[str]) -> str:
        tds = "".join([f"<td>{_cell_html(cells.get(k) or MetricCell(key=k,name=k))}</td>" for k in keys])
        return tds

    code_keys = ["codecheck_error_num", "bin_scope_error_num", "build_check_error_num", "compile_error_num"]
    dt_keys = ["dt_pass_rate", "dt_pass_num", "dt_line_coverage", "dt_method_coverage"]

    code_header = """
      <tr>
        <th style="width:180px;">项目</th>
        <th>CodeCheck 错误数</th>
        <th>Bin Scope 错误数</th>
        <th>Build 错误数</th>
        <th>Compile 错误数</th>
      </tr>
    """
    dt_header = """
      <tr>
        <th style="width:180px;">项目</th>
        <th>DT 通过率</th>
        <th>DT 通过数</th>
        <th>行覆盖率</th>
        <th>方法覆盖率</th>
      </tr>
    """

    code_rows = []
    dt_rows = []
    for p in projects:
        cells = {c.key: c for c in p["code_metrics"] + p["dt_metrics"]}
        code_rows.append(f"<tr><td><b>{escape(p['project_name'])}</b><div class='muted'>{escape(p.get('project_domain') or '')}</div></td>{project_row(cells, code_keys)}</tr>")
        dt_rows.append(f"<tr><td><b>{escape(p['project_name'])}</b><div class='muted'>{escape(p.get('project_domain') or '')}</div></td>{project_row(cells, dt_keys)}</tr>")

    html = f"""
    <html>
      <head>{style}</head>
      <body>
        <div class="card">
          <h2>每日集成报告 · {record_date.isoformat()}</h2>
          <div class="muted">本邮件仅包含你订阅的项目；红色为预警项，可点击指标跳转详情。</div>
        </div>

        <div class="card">
          <h2>代码检测类</h2>
          <table>{code_header}{''.join(code_rows) or '<tr><td class=\"muted\">暂无数据</td></tr>'}</table>
        </div>

        <div class="card">
          <h2>DT 测试数据</h2>
          <table>{dt_header}{''.join(dt_rows) or '<tr><td class=\"muted\">暂无数据</td></tr>'}</table>
        </div>
      </body>
    </html>
    """
    return html


def send_html_email(to_email: str, subject: str, html: str):
    msg = EmailMultiAlternatives(subject=subject, to=[to_email])
    msg.attach_alternative(html, "text/html")
    msg.send()

