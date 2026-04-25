from __future__ import annotations

import io
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.deepaudit.analysis_payload import normalize_analysis_result

REPORT_FONT_NAME = 'FocusAuditUnicode'
FALLBACK_CJK_FONT_NAME = 'STSong-Light'
FONT_DIR = Path(__file__).resolve().parent / 'assets' / 'fonts'
FONT_CANDIDATES = (
    FONT_DIR / 'ArialUnicode.ttf',
    FONT_DIR / 'NotoSansCJKsc-Regular.otf',
)
MAX_REPORT_ISSUES = 30
CODE_TABLE_CHUNK_SIZE = 120


class ReportBuilder:
    @staticmethod
    def _load_reportlab() -> dict[str, Any]:
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as exc:
            raise RuntimeError('缺少 reportlab 依赖，无法生成 PDF 报告，请先安装 backend-django/requirements.txt 中的依赖') from exc

        return {
            'A4': A4,
            'Paragraph': Paragraph,
            'ParagraphStyle': ParagraphStyle,
            'SimpleDocTemplate': SimpleDocTemplate,
            'Spacer': Spacer,
            'Table': Table,
            'TableStyle': TableStyle,
            'TA_LEFT': TA_LEFT,
            'cm': cm,
            'colors': colors,
            'getSampleStyleSheet': getSampleStyleSheet,
            'pdfmetrics': pdfmetrics,
            'TTFont': TTFont,
            'UnicodeCIDFont': UnicodeCIDFont,
        }

    @classmethod
    def _ensure_pdf_font(cls, reportlab: dict[str, Any]) -> str:
        pdfmetrics = reportlab['pdfmetrics']
        if REPORT_FONT_NAME in pdfmetrics.getRegisteredFontNames():
            return REPORT_FONT_NAME
        for font_path in FONT_CANDIDATES:
            if not font_path.exists():
                continue
            pdfmetrics.registerFont(reportlab['TTFont'](REPORT_FONT_NAME, str(font_path)))
            return REPORT_FONT_NAME
        if FALLBACK_CJK_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(reportlab['UnicodeCIDFont'](FALLBACK_CJK_FONT_NAME))
        return FALLBACK_CJK_FONT_NAME

    @classmethod
    def _build_styles(cls, reportlab: dict[str, Any], *, font_name: str) -> dict[str, Any]:
        ParagraphStyle = reportlab['ParagraphStyle']
        TA_LEFT = reportlab['TA_LEFT']
        styles = reportlab['getSampleStyleSheet']()
        return {
            'title': ParagraphStyle(
                'FocusAuditTitle',
                parent=styles['Title'],
                fontName=font_name,
                fontSize=18,
                leading=24,
                alignment=TA_LEFT,
                textColor='#172554',
                spaceAfter=10,
            ),
            'meta': ParagraphStyle(
                'FocusAuditMeta',
                parent=styles['BodyText'],
                fontName=font_name,
                fontSize=9,
                leading=13,
                textColor='#475569',
                spaceAfter=3,
            ),
            'heading': ParagraphStyle(
                'FocusAuditHeading',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=12,
                leading=16,
                textColor='#0f172a',
                spaceBefore=10,
                spaceAfter=6,
            ),
            'body': ParagraphStyle(
                'FocusAuditBody',
                parent=styles['BodyText'],
                fontName=font_name,
                fontSize=9.5,
                leading=14,
                textColor='#111827',
                wordWrap='CJK',
                spaceAfter=4,
            ),
            'code': ParagraphStyle(
                'FocusAuditCode',
                parent=styles['BodyText'],
                fontName=font_name,
                fontSize=8,
                leading=10,
                textColor='#111827',
                wordWrap='CJK',
                leftIndent=0,
                rightIndent=0,
                spaceAfter=0,
            ),
            'line_number': ParagraphStyle(
                'FocusAuditLineNumber',
                parent=styles['BodyText'],
                fontName=font_name,
                fontSize=7.5,
                leading=10,
                textColor='#64748b',
                alignment=TA_LEFT,
            ),
        }

    @staticmethod
    def _escape_text(value: str) -> str:
        return html.escape(str(value or '')).replace('\n', '<br/>')

    @staticmethod
    def _build_lines(title: str, sections: list[tuple[str, list[str]]]) -> list[str]:
        lines = [title, f'Generated: {datetime.now().isoformat(timespec="seconds")}', '']
        for header, items in sections:
            lines.append(header)
            lines.append('-' * len(header))
            lines.extend(items or ['(empty)'])
            lines.append('')
        return lines

    @staticmethod
    def _render_minimal_pdf(lines: list[str]) -> bytes:
        def escape(value: str) -> str:
            return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        text_lines = ['BT', '/F1 10 Tf', '50 760 Td']
        leading = 14
        first = True
        for line in lines[:45]:
            escaped = escape(line[:110])
            if first:
                text_lines.append(f'({escaped}) Tj')
                first = False
            else:
                text_lines.append(f'0 -{leading} Td ({escaped}) Tj')
        text_lines.append('ET')
        stream = '\n'.join(text_lines).encode('utf-8')

        objects: list[bytes] = []
        objects.append(b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n')
        objects.append(b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n')
        objects.append(
            b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj\n'
        )
        objects.append(f'4 0 obj << /Length {len(stream)} >> stream\n'.encode('utf-8') + stream + b'\nendstream endobj\n')
        objects.append(b'5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n')

        output = io.BytesIO()
        output.write(b'%PDF-1.4\n')
        offsets = [0]
        for obj in objects:
            offsets.append(output.tell())
            output.write(obj)
        xref_offset = output.tell()
        output.write(f'xref\n0 {len(objects) + 1}\n'.encode('utf-8'))
        output.write(b'0000000000 65535 f \n')
        for offset in offsets[1:]:
            output.write(f'{offset:010d} 00000 n \n'.encode('utf-8'))
        output.write(
            (
                f'trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n'
                f'startxref\n{xref_offset}\n%%EOF'
            ).encode('utf-8')
        )
        return output.getvalue()

    @classmethod
    def _render_pdf(
        cls,
        title: str,
        sections: list[tuple[str, list[str]]],
        *,
        code_content: str = '',
        code_language: str = '',
    ) -> bytes:
        reportlab = cls._load_reportlab()
        font_name = cls._ensure_pdf_font(reportlab)
        styles = cls._build_styles(reportlab, font_name=font_name)
        buffer = io.BytesIO()
        document = reportlab['SimpleDocTemplate'](
            buffer,
            pagesize=reportlab['A4'],
            topMargin=1.6 * reportlab['cm'],
            bottomMargin=1.4 * reportlab['cm'],
            leftMargin=1.6 * reportlab['cm'],
            rightMargin=1.6 * reportlab['cm'],
            title=title,
            author='FocusAudit',
        )
        Paragraph = reportlab['Paragraph']
        Spacer = reportlab['Spacer']
        Table = reportlab['Table']
        TableStyle = reportlab['TableStyle']
        colors = reportlab['colors']

        story: list[Any] = [
            Paragraph(cls._escape_text(title), styles['title']),
            Paragraph(
                cls._escape_text(
                    f'生成时间: {datetime.now().isoformat(timespec="seconds")}'
                ),
                styles['meta'],
            ),
            Spacer(1, 0.18 * reportlab['cm']),
        ]

        for header, items in sections:
            story.append(Paragraph(cls._escape_text(header), styles['heading']))
            if not items:
                story.append(Paragraph('(empty)', styles['body']))
            else:
                for item in items:
                    story.append(Paragraph(cls._escape_text(item), styles['body']))
            story.append(Spacer(1, 0.12 * reportlab['cm']))

        normalized_code = str(code_content or '').replace('\r\n', '\n').replace('\r', '\n')
        if normalized_code.strip():
            story.append(Paragraph('原始代码附录', styles['heading']))
            if code_language:
                story.append(
                    Paragraph(
                        cls._escape_text(f'语言: {code_language}'),
                        styles['meta'],
                    )
                )
            lines = normalized_code.split('\n')
            for offset in range(0, len(lines), CODE_TABLE_CHUNK_SIZE):
                chunk = lines[offset:offset + CODE_TABLE_CHUNK_SIZE]
                rows = []
                for index, raw_line in enumerate(chunk, start=offset + 1):
                    line_text = raw_line.expandtabs(4)
                    rows.append(
                        [
                            Paragraph(str(index), styles['line_number']),
                            Paragraph(
                                cls._escape_text(line_text) or '&nbsp;',
                                styles['code'],
                            ),
                        ]
                    )
                code_table = Table(
                    rows,
                    colWidths=[1.1 * reportlab['cm'], document.width - (1.1 * reportlab['cm'])],
                    repeatRows=0,
                )
                code_table.setStyle(
                    TableStyle(
                        [
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f8fafc'), colors.HexColor('#ffffff')]),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 4),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 2),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                            ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
                            ('LINEAFTER', (0, 0), (0, -1), 0.25, colors.HexColor('#cbd5e1')),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
                        ]
                    )
                )
                story.append(code_table)
                story.append(Spacer(1, 0.16 * reportlab['cm']))

        document.build(story)
        return buffer.getvalue()

    @classmethod
    def build_task_report(cls, task: dict[str, Any], issues: list[dict[str, Any]], project_name: str) -> bytes:
        sections = [
            ('Task', [
                f"Project: {project_name}",
                f"Task ID: {task.get('id', '')}",
                f"Status: {task.get('status', '')}",
                f"Quality Score: {task.get('quality_score', 0)}",
                f"Issues Count: {task.get('issues_count', len(issues))}",
            ]),
            ('Issues', [
                f"[{issue.get('severity', '').upper()}] {issue.get('title', issue.get('issue_type', 'issue'))} - {issue.get('file_path', '')}:{issue.get('line_number', '')}"
                for issue in issues[:MAX_REPORT_ISSUES]
            ]),
        ]
        return cls._render_pdf('FocusAudit 扫描任务报告', sections)

    @classmethod
    def build_agent_report(cls, task: dict[str, Any], findings: list[dict[str, Any]], project_name: str) -> bytes:
        sections = [
            ('Agent Task', [
                f"Project: {project_name}",
                f"Task ID: {task.get('id', '')}",
                f"Status: {task.get('status', '')}",
                f"Security Score: {task.get('security_score', 0)}",
                f"Findings Count: {task.get('findings_count', len(findings))}",
            ]),
            ('Findings', [
                f"[{finding.get('severity', '').upper()}] {finding.get('title', '')} - {finding.get('file_path', '')}:{finding.get('line_start', '')}"
                for finding in findings[:MAX_REPORT_ISSUES]
            ]),
        ]
        return cls._render_pdf('FocusAudit Agent 审计报告', sections)

    @classmethod
    def build_instant_report(
        cls,
        language: str,
        result: dict[str, Any],
        *,
        code_content: str = '',
    ) -> bytes:
        result = normalize_analysis_result(result)
        issues = result.get('issues', [])
        sections = [
            ('Instant Analysis', [
                f'Language: {language}',
                f"Quality Score: {result.get('quality_score', 0)}",
                f"Issues Count: {len(issues)}",
            ]),
            ('Issues', [
                f"[{issue.get('severity', '').upper()}] {issue.get('title', '')} - line {issue.get('line_number', '')}"
                for issue in issues[:MAX_REPORT_ISSUES]
            ]),
        ]
        return cls._render_pdf(
            'FocusAudit 即时分析报告',
            sections,
            code_content=code_content,
            code_language=language,
        )
