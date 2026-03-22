from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from apps.deepaudit.analysis_payload import normalize_analysis_result


class ReportBuilder:
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
                for issue in issues[:30]
            ]),
        ]
        return cls._render_minimal_pdf(cls._build_lines('DeepAudit Task Report', sections))

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
                for finding in findings[:30]
            ]),
        ]
        return cls._render_minimal_pdf(cls._build_lines('DeepAudit Agent Report', sections))

    @classmethod
    def build_instant_report(cls, language: str, result: dict[str, Any]) -> bytes:
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
                for issue in issues[:30]
            ]),
        ]
        return cls._render_minimal_pdf(cls._build_lines('DeepAudit Instant Analysis', sections))
