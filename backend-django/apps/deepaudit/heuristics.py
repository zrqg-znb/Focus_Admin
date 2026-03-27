from __future__ import annotations

import fnmatch
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .constants import SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_LOW, SEVERITY_MEDIUM


@dataclass(frozen=True)
class RulePattern:
    code: str
    issue_type: str
    title: str
    severity: str
    patterns: tuple[str, ...]
    suggestion: str
    description: str


DEFAULT_RULE_PATTERNS: tuple[RulePattern, ...] = (
    RulePattern(
        code='SEC_SQLI',
        issue_type='sql_injection',
        title='Potential SQL injection',
        severity=SEVERITY_HIGH,
        patterns=(r'execute\s*\(\s*f[\"\']', r'execute\s*\(.*\+.*select', r'SELECT .*\+ .*WHERE'),
        suggestion='Use parameterized queries instead of string concatenation.',
        description='Detected SQL query construction patterns that may include untrusted input.',
    ),
    RulePattern(
        code='SEC_XSS',
        issue_type='xss',
        title='Potential XSS sink',
        severity=SEVERITY_HIGH,
        patterns=(r'dangerouslySetInnerHTML', r'innerHTML\s*=', r'v-html\s*='),
        suggestion='Sanitize user-controlled HTML before rendering it into the DOM.',
        description='Detected direct HTML rendering sinks that can lead to XSS.',
    ),
    RulePattern(
        code='SEC_CMD',
        issue_type='command_injection',
        title='Potential command injection',
        severity=SEVERITY_CRITICAL,
        patterns=(r'os\.system\s*\(', r'subprocess\..*shell\s*=\s*True', r'Runtime\.getRuntime\(\)\.exec', r'child_process\.exec\s*\('),
        suggestion='Avoid shell execution with string interpolation; pass argument arrays and validate input.',
        description='Detected shell execution APIs that commonly lead to command injection.',
    ),
    RulePattern(
        code='SEC_PATH',
        issue_type='path_traversal',
        title='Potential path traversal',
        severity=SEVERITY_HIGH,
        patterns=(r'open\s*\(.*request', r'os\.path\.join\s*\(.*request', r'SendFile\(.*request', r'Path\(.*request'),
        suggestion='Normalize and validate file paths against an allowlisted base directory.',
        description='Detected filesystem access patterns that may use request-controlled path fragments.',
    ),
    RulePattern(
        code='SEC_SSRF',
        issue_type='ssrf',
        title='Potential SSRF',
        severity=SEVERITY_HIGH,
        patterns=(r'requests\.(get|post|put|delete)\s*\(\s*[^\"\']', r'httpx\.(get|post|put|delete)\s*\(\s*[^\"\']', r'fetch\(\s*url', r'axios\.(get|post)\(\s*url'),
        suggestion='Validate outbound URLs and block access to internal network ranges.',
        description='Detected outbound HTTP calls that may accept user-controlled URLs.',
    ),
    RulePattern(
        code='SEC_DESER',
        issue_type='insecure_deserialization',
        title='Potential unsafe deserialization',
        severity=SEVERITY_HIGH,
        patterns=(r'pickle\.loads\s*\(', r'yaml\.load\s*\(', r'ObjectInputStream', r'BinaryFormatter'),
        suggestion='Use safe parsers or signed payloads for untrusted serialized content.',
        description='Detected deserialization APIs that are unsafe with untrusted input.',
    ),
    RulePattern(
        code='SEC_CRYPTO',
        issue_type='weak_crypto',
        title='Weak crypto primitive',
        severity=SEVERITY_MEDIUM,
        patterns=(r'hashlib\.md5\s*\(', r'hashlib\.sha1\s*\(', r'MD5\(', r'SHA1\('),
        suggestion='Use SHA-256 or stronger modern primitives unless compatibility requires otherwise.',
        description='Detected legacy cryptographic primitives.',
    ),
    RulePattern(
        code='SEC_SECRET',
        issue_type='hardcoded_secret',
        title='Potential hardcoded secret',
        severity=SEVERITY_HIGH,
        patterns=(r'API[_-]?KEY\s*=\s*[\"\'][^\"\']{8,}[\"\']', r'SECRET[_-]?KEY\s*=\s*[\"\'][^\"\']{8,}[\"\']', r'password\s*=\s*[\"\'][^\"\']{8,}[\"\']'),
        suggestion='Move secrets into environment variables or a dedicated secret manager.',
        description='Detected hardcoded credential-like values.',
    ),
    RulePattern(
        code='SEC_EVAL',
        issue_type='unsafe_eval',
        title='Potential unsafe dynamic execution',
        severity=SEVERITY_HIGH,
        patterns=(r'\beval\s*\(', r'\bexec\s*\('),
        suggestion='Avoid dynamic code execution or strictly sandbox and validate the input source.',
        description='Detected dynamic execution primitives.',
    ),
    RulePattern(
        code='SEC_XXE',
        issue_type='xxe',
        title='Potential XXE parser configuration',
        severity=SEVERITY_MEDIUM,
        patterns=(r'DocumentBuilderFactory\.newInstance', r'lxml\.etree\.parse', r'xml\.dom\.minidom\.parse'),
        suggestion='Disable external entity resolution in XML parsers before processing untrusted XML.',
        description='Detected XML parsing APIs that may require XXE hardening.',
    ),
    RulePattern(
        code='C_BUF',
        issue_type='buffer_overflow',
        title='Potential buffer overflow',
        severity=SEVERITY_CRITICAL,
        patterns=(r'\bstrcpy\s*\(', r'\bstrcat\s*\(', r'\bsprintf\s*\(', r'\bvsprintf\s*\(', r'\bgets\s*\(', r'\bscanf\s*\([^)]*%s'),
        suggestion='Use bounded APIs such as snprintf, strlcpy, strlcat, and always validate destination sizes.',
        description='Detected classic unsafe C string APIs that can overflow fixed-size buffers.',
    ),
    RulePattern(
        code='C_MEM',
        issue_type='memory_corruption',
        title='Potential memory corruption',
        severity=SEVERITY_HIGH,
        patterns=(r'\bmemcpy\s*\(', r'\bmemmove\s*\(', r'\bmemset\s*\(', r'\bfree\s*\(', r'\bdelete\s*\w+', r'\bdelete\[\]\s*\w+'),
        suggestion='Verify pointer validity, object lifetime, and length arguments before memory operations.',
        description='Detected manual memory-management and bulk-memory APIs that need careful bounds and lifetime checks.',
    ),
    RulePattern(
        code='C_LEAK',
        issue_type='memory_leak',
        title='Potential memory leak',
        severity=SEVERITY_MEDIUM,
        patterns=(r'\bmalloc\s*\(', r'\bcalloc\s*\(', r'\brealloc\s*\(', r'\bnew\s+\w+', r'\bnew\[\]\s+\w+'),
        suggestion='Ensure every allocation has a matching free/delete on all control-flow paths.',
        description='Detected allocation sites that should be paired with explicit release logic.',
    ),
    RulePattern(
        code='C_RACE',
        issue_type='race_condition',
        title='Potential race condition',
        severity=SEVERITY_HIGH,
        patterns=(r'\bpthread_create\s*\(', r'\bstd::thread\b', r'\bstd::async\b', r'\bCreateThread\s*\(', r'\bTask\s+\w+\s*=', r'\bvolatile\b'),
        suggestion='Protect shared mutable state with mutexes, atomics, or explicit synchronization primitives.',
        description='Detected thread creation and shared-state markers that merit synchronization review.',
    ),
    RulePattern(
        code='C_FMT',
        issue_type='format_string',
        title='Potential format string bug',
        severity=SEVERITY_HIGH,
        patterns=(r'\bprintf\s*\([^,]+$', r'\bfprintf\s*\([^,]+$', r'\bsyslog\s*\([^,]+$', r'\bscanf\s*\([^)]*%n'),
        suggestion='Always use a fixed format string and pass user data as arguments, never as the format itself.',
        description='Detected format-style functions that can mis-handle attacker-controlled format strings.',
    ),
)

TEXT_EXTENSIONS = {
    '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.cc', '.hh', '.cxx', '.hpp', '.hxx',
    '.cs', '.php', '.rb', '.kt', '.swift', '.sql', '.sh', '.json', '.yml', '.yaml', '.vue', '.xml', '.html', '.mjs', '.mts', '.cts'
}

DEFAULT_EXCLUDES = ['node_modules/**', '.git/**', 'dist/**', 'build/**', '__pycache__/**', '.venv/**', 'vendor/**']
DEPTH_CONTEXT_RADIUS = {'quick': 1, 'standard': 2, 'deep': 4}
DEPTH_CONFIDENCE_DELTA = {'quick': -0.05, 'standard': 0.0, 'deep': 0.08}


def is_text_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in TEXT_EXTENSIONS



def should_exclude(path: str, exclude_patterns: Iterable[str] | None = None) -> bool:
    path = path.replace('\\', '/')
    patterns = list(DEFAULT_EXCLUDES)
    if exclude_patterns:
        patterns.extend(str(item).strip() for item in exclude_patterns if str(item).strip())
    for pattern in patterns:
        normalized = pattern.replace('\\', '/')
        if fnmatch.fnmatch(path, normalized) or fnmatch.fnmatch(f'/{path}', normalized):
            return True
        if normalized.endswith('/**') and path.startswith(normalized[:-3].rstrip('/')):
            return True
    return False



def normalize_severity_weight(severity: str) -> int:
    if severity == SEVERITY_CRITICAL:
        return 18
    if severity == SEVERITY_HIGH:
        return 10
    if severity == SEVERITY_MEDIUM:
        return 5
    return 2



def normalize_severity_weights(severity_weights: dict[str, Any] | None = None) -> dict[str, int]:
    normalized = {
        SEVERITY_CRITICAL: normalize_severity_weight(SEVERITY_CRITICAL),
        SEVERITY_HIGH: normalize_severity_weight(SEVERITY_HIGH),
        SEVERITY_MEDIUM: normalize_severity_weight(SEVERITY_MEDIUM),
        SEVERITY_LOW: normalize_severity_weight(SEVERITY_LOW),
    }
    for key, value in (severity_weights or {}).items():
        severity = str(key or '').strip().lower()
        if severity not in normalized:
            continue
        try:
            weight = int(float(value))
        except (TypeError, ValueError):
            continue
        if weight > 0:
            normalized[severity] = weight
    return normalized



def detect_language_from_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.h': 'c',
        '.hh': 'cpp',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        '.vue': 'vue',
    }
    return mapping.get(ext, 'text')



def _context_radius(analysis_depth: str) -> int:
    return DEPTH_CONTEXT_RADIUS.get(str(analysis_depth or 'standard').strip().lower(), DEPTH_CONTEXT_RADIUS['standard'])



def _confidence_delta(analysis_depth: str) -> float:
    return DEPTH_CONFIDENCE_DELTA.get(str(analysis_depth or 'standard').strip().lower(), 0.0)



def _build_ai_explanation(
    rule: RulePattern,
    file_path: str,
    *,
    analysis_depth: str,
    prompt_context: dict[str, Any] | None,
) -> dict[str, Any]:
    explanation: dict[str, Any] = {
        'what': rule.title,
        'why': rule.description,
        'how': rule.suggestion,
        'learn_more': f'Language: {detect_language_from_path(file_path)}',
        'analysis_depth': analysis_depth,
    }
    if prompt_context:
        if prompt_context.get('name'):
            explanation['template_name'] = prompt_context['name']
        if prompt_context.get('focus'):
            explanation['prompt_focus'] = list(prompt_context.get('focus') or [])
        if prompt_context.get('hint'):
            explanation['analysis_strategy'] = prompt_context['hint']
    return explanation



def scan_content(
    content: str,
    file_path: str,
    *,
    target_vulnerabilities: Iterable[str] | None = None,
    rule_patterns: Iterable[RulePattern] | None = None,
    prompt_context: dict[str, Any] | None = None,
    analysis_depth: str = 'standard',
) -> list[dict]:
    issues: list[dict] = []
    lines = content.splitlines() or ['']
    active_rules = tuple(rule_patterns) if rule_patterns is not None else DEFAULT_RULE_PATTERNS
    target_set = {str(item).strip() for item in (target_vulnerabilities or []) if str(item).strip()}
    prompt_focus = {str(item).strip() for item in (prompt_context or {}).get('focus', []) if str(item).strip()}
    seen: set[tuple[str, int, str]] = set()
    context_radius = _context_radius(analysis_depth)
    confidence_delta = _confidence_delta(analysis_depth)

    for index, line in enumerate(lines, start=1):
        for rule in active_rules:
            if target_set and rule.issue_type not in target_set:
                continue
            if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in rule.patterns):
                key = (file_path, index, rule.issue_type)
                if key in seen:
                    continue
                seen.add(key)
                start = max(0, index - 1 - context_radius)
                end = min(len(lines), index + context_radius)
                code_snippet = '\n'.join(lines[start:end])
                confidence = 0.55 + (normalize_severity_weight(rule.severity) / 40) + confidence_delta
                if rule.issue_type in prompt_focus:
                    confidence += 0.05
                issues.append(
                    {
                        'rule_code': rule.code,
                        'issue_type': rule.issue_type,
                        'severity': rule.severity,
                        'title': rule.title,
                        'description': rule.description,
                        'suggestion': rule.suggestion,
                        'file_path': file_path,
                        'line_number': index,
                        'column_number': 1,
                        'code_snippet': code_snippet,
                        'ai_explanation': _build_ai_explanation(
                            rule,
                            file_path,
                            analysis_depth=analysis_depth,
                            prompt_context=prompt_context,
                        ),
                        'confidence': round(max(0.2, min(0.99, confidence)), 2),
                    }
                )
    return issues



def build_summary(
    issues: list[dict],
    total_lines: int,
    total_files: int,
    *,
    severity_weights: dict[str, Any] | None = None,
    analysis_depth: str = 'standard',
    prompt_context: dict[str, Any] | None = None,
    rule_patterns: Iterable[RulePattern] | None = None,
) -> dict[str, Any]:
    severity_counts = {SEVERITY_CRITICAL: 0, SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 0, SEVERITY_LOW: 0}
    for issue in issues:
        severity = str(issue.get('severity') or '').strip().lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    effective_weights = normalize_severity_weights(severity_weights)
    penalty = sum(effective_weights.get(str(issue.get('severity') or '').strip().lower(), normalize_severity_weight(str(issue.get('severity') or '').strip().lower())) for issue in issues)
    quality_score = max(0.0, 100.0 - penalty)
    security_score = max(0.0, 100.0 - penalty * 1.2)
    issue_types: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get('issue_type') or '').strip() or 'unknown'
        issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

    complexity = min(100.0, (len(issues) * 7) + math.log(max(total_lines, 1), 2))
    maintainability = max(0.0, 100.0 - len(issues) * 4)
    performance = max(0.0, 100.0 - severity_counts[SEVERITY_HIGH] * 3 - severity_counts[SEVERITY_CRITICAL] * 6)
    active_rule_count = len(tuple(rule_patterns)) if rule_patterns is not None else len(DEFAULT_RULE_PATTERNS)

    return {
        'summary': {
            'total_issues': len(issues),
            'critical_issues': severity_counts[SEVERITY_CRITICAL],
            'high_issues': severity_counts[SEVERITY_HIGH],
            'medium_issues': severity_counts[SEVERITY_MEDIUM],
            'low_issues': severity_counts[SEVERITY_LOW],
        },
        'severity_distribution': severity_counts,
        'issue_types': issue_types,
        'quality_score': round(quality_score, 2),
        'security_score': round(security_score, 2),
        'metrics': {
            'complexity': round(complexity, 2),
            'maintainability': round(maintainability, 2),
            'security': round(security_score, 2),
            'performance': round(performance, 2),
        },
        'analysis_profile': {
            'analysis_depth': analysis_depth,
            'prompt_focus': list((prompt_context or {}).get('focus') or []),
            'prompt_template_name': (prompt_context or {}).get('name'),
            'severity_weights': effective_weights,
            'rule_count': active_rule_count,
        },
        'total_files': total_files,
        'total_lines': total_lines,
    }
