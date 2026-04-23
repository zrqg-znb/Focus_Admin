from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any, Iterable

from apps.deepaudit.rag.splitter import ChunkType, CodeChunk, CodeSplitter


C_FAMILY_EXTENSIONS = {
    '.c',
    '.cc',
    '.cpp',
    '.cxx',
    '.h',
    '.hh',
    '.hpp',
    '.hxx',
}
C_FAMILY_LANGUAGES = {'c', 'cpp'}
C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME = '嵌入式 C/C++ 深度审计'
C_FAMILY_SYSTEM_RULE_SET_NAME = '嵌入式 C/C++ 语义规则集'
C_FAMILY_TARGET_VULNERABILITIES = [
    'buffer_overflow',
    'out_of_bounds',
    'integer_overflow',
    'null_dereference',
    'use_after_free',
    'double_free',
    'uninitialized_memory',
    'resource_leak',
    'race_condition',
    'deadlock',
    'format_string',
    'api_contract_violation',
]
C_FAMILY_KNOWLEDGE_MODULES = [
    'buffer_overflow',
    'use_after_free',
    'integer_overflow',
    'null_dereference',
    'resource_leak',
    'deadlock',
    'embedded_concurrency',
    'api_contract_violation',
]
ANALYSIS_DEPTH_ALIASES = {
    'basic': 'basic',
    'quick': 'basic',
    'standard': 'standard',
    'deep': 'deep',
}
ANALYSIS_DEPTH_BUDGETS = {
    'basic': {
        'max_units': 25,
        'max_verify': 0,
        'max_file_size': 512 * 1024,
        'context_token_budget': 2800,
    },
    'standard': {
        'max_units': 80,
        'max_verify': 5,
        'max_file_size': 1024 * 1024,
        'context_token_budget': 5200,
    },
    'deep': {
        'max_units': 160,
        'max_verify': 12,
        'max_file_size': 2 * 1024 * 1024,
        'context_token_budget': 7600,
    },
}
BUILD_FILE_CANDIDATES = (
    'compile_commands.json',
    'CMakeLists.txt',
    'Makefile',
    'makefile',
    'GNUmakefile',
)
BUILD_FILE_SUFFIXES = ('.mk',)

_DANGEROUS_API_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'\bstrcpy\s*\('), 'strcpy', 28),
    (re.compile(r'\bstrcat\s*\('), 'strcat', 26),
    (re.compile(r'\bsprintf\s*\('), 'sprintf', 26),
    (re.compile(r'\bvsprintf\s*\('), 'vsprintf', 28),
    (re.compile(r'\bgets\s*\('), 'gets', 30),
    (re.compile(r'\bscanf\s*\([^)]*%s'), 'scanf_%s', 24),
    (re.compile(r'\bmemcpy\s*\('), 'memcpy', 18),
    (re.compile(r'\bmemmove\s*\('), 'memmove', 16),
    (re.compile(r'\bmemset\s*\('), 'memset', 14),
    (re.compile(r'\bmalloc\s*\('), 'malloc', 18),
    (re.compile(r'\bcalloc\s*\('), 'calloc', 18),
    (re.compile(r'\brealloc\s*\('), 'realloc', 18),
    (re.compile(r'\bfree\s*\('), 'free', 18),
    (re.compile(r'\bpvPortMalloc\s*\('), 'pvPortMalloc', 20),
    (re.compile(r'\bvPortFree\s*\('), 'vPortFree', 20),
    (re.compile(r'\bnew\b'), 'new', 16),
    (re.compile(r'\bdelete\b'), 'delete', 18),
    (re.compile(r'\bprintf\s*\(\s*[^"\']'), 'printf_variable_format', 24),
    (re.compile(r'\bfprintf\s*\(\s*[^"\']'), 'fprintf_variable_format', 24),
)
_BOUNDARY_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'\[[^\]]+\]'), 'array_index', 6),
    (re.compile(r'->'), 'pointer_field_access', 8),
    (re.compile(r'\*\s*[A-Za-z_]\w*'), 'pointer_dereference', 7),
    (re.compile(r'\([^)]*(?:u?int(?:8|16|32|64)_t|size_t|ssize_t|char\s*\*)[^)]*\)'), 'manual_cast', 8),
    (re.compile(r'\b(?:len|length|size|count)\b', re.IGNORECASE), 'length_parameter', 5),
    (re.compile(r'\bsizeof\s*\('), 'sizeof_usage', 4),
)
_CONCURRENCY_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'\bpthread_create\s*\('), 'pthread_create', 20),
    (re.compile(r'\bstd::thread\b'), 'std_thread', 20),
    (re.compile(r'\bstd::mutex\b|\bmutex\b'), 'mutex', 14),
    (re.compile(r'\bstd::lock_guard\b|\block_guard\b'), 'lock_guard', 12),
    (re.compile(r'\bsemaphore\b|\bsem_wait\b|\bsem_post\b', re.IGNORECASE), 'semaphore', 16),
    (re.compile(r'\bvolatile\b'), 'volatile', 10),
    (re.compile(r'\batomic\b', re.IGNORECASE), 'atomic', 12),
    (re.compile(r'\bISR\b|\binterrupt\b', re.IGNORECASE), 'interrupt_context', 18),
    (re.compile(r'\bTaskHandle_t\b|\bxTaskCreate\b|\btaskENTER_CRITICAL\b|\btaskEXIT_CRITICAL\b'), 'rtos_task', 18),
    (re.compile(r'\bxQueue\w+\b|\bxSemaphore\w+\b|\bxTaskNotify\w+\b'), 'rtos_sync_primitive', 18),
    (re.compile(r'\btaskENTER_CRITICAL_FROM_ISR\b|\btaskEXIT_CRITICAL_FROM_ISR\b'), 'rtos_isr_critical', 18),
    (re.compile(r'\b(?:IRQ|NVIC|PendSV|SysTick)\b', re.IGNORECASE), 'mcu_interrupt_primitive', 14),
)
_QUALITY_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'\bNULL\b|\bnullptr\b'), 'null_handling', 8),
    (re.compile(r'\breturn\s*;'), 'empty_return', 4),
    (re.compile(r'\bif\s*\([^)]*<\s*0[^)]*\)'), 'error_branch', 7),
    (re.compile(r'\bassert\s*\('), 'assert_contract', 6),
    (re.compile(r'\bTODO\b|\bFIXME\b'), 'todo_fixme', 4),
)
_RESOURCE_PAIR_OPENERS = {
    'malloc': re.compile(r'\bmalloc\s*\('),
    'calloc': re.compile(r'\bcalloc\s*\('),
    'realloc': re.compile(r'\brealloc\s*\('),
    'pvPortMalloc': re.compile(r'\bpvPortMalloc\s*\('),
    'new': re.compile(r'\bnew\b'),
    'lock': re.compile(r'\block\s*\('),
    'mutex_lock': re.compile(r'\b(?:pthread_mutex_lock|mutex_lock)\s*\('),
}
_RESOURCE_PAIR_CLOSERS = {
    'free': re.compile(r'\bfree\s*\('),
    'vPortFree': re.compile(r'\bvPortFree\s*\('),
    'delete': re.compile(r'\bdelete\b'),
    'unlock': re.compile(r'\bunlock\s*\('),
    'mutex_unlock': re.compile(r'\b(?:pthread_mutex_unlock|mutex_unlock)\s*\('),
}
_HEADER_SOURCE_SUFFIX_GROUPS = (
    (('.c', '.cc', '.cpp', '.cxx'), ('.h', '.hh', '.hpp', '.hxx')),
    (('.h', '.hh', '.hpp', '.hxx'), ('.c', '.cc', '.cpp', '.cxx')),
)
_MACRO_PATTERN = re.compile(r'^\s*#\s*(?:define|if|ifdef|ifndef|elif|endif)\b.*$', re.MULTILINE)
_TYPE_PATTERN = re.compile(r'^\s*(?:typedef\b.*;|struct\s+\w+|enum\s+\w+|class\s+\w+)', re.MULTILINE)
_INCLUDE_PATTERN = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]', re.MULTILINE)
_COMMENT_BLOCK_PATTERN = re.compile(r'/\*.*?\*/', re.DOTALL)
_COMMENT_LINE_PATTERN = re.compile(r'//.*$', re.MULTILINE)
_PRIORITY_PATH_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'(^|/)(src|source|core|kernel|os|rtos)(/|$)', re.IGNORECASE), 'core_runtime_path', 14),
    (re.compile(r'(^|/)(driver|drivers|hal|middleware|service|services|bsp|board|boards)(/|$)', re.IGNORECASE), 'embedded_component_path', 12),
    (re.compile(r'(^|/)(memory|heap|buffer|stream|queue|event|events|task|tasks|timer|timers|scheduler)(/|$)', re.IGNORECASE), 'memory_concurrency_path', 10),
)
_DEPRIORITIZED_PATH_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'(^|/)(portable|arch|startup|cmsis)(/|$)', re.IGNORECASE), 'arch_port_layer', -22),
    (re.compile(r'(^|/)(vendor|thirdparty|third_party|3rdparty|external|extern|generated|gen|autogen|build|out|dist|obj|cmake-build)(/|$)', re.IGNORECASE), 'generated_or_vendor_path', -18),
    (re.compile(r'(^|/)(example|examples|sample|samples|template|templates|doc|docs|test|tests)(/|$)', re.IGNORECASE), 'non_runtime_path', -12),
    (re.compile(r'(^|/)(include|inc)(/|$)', re.IGNORECASE), 'interface_header_path', -8),
)
_EMBEDDED_NAME_PATTERNS: tuple[tuple[re.Pattern[str], str, int], ...] = (
    (re.compile(r'(?:isr|irq|fault|handler)', re.IGNORECASE), 'interrupt_entrypoint', 10),
    (re.compile(r'(?:task|queue|timer|event|stream|buffer|mutex|lock|semaphore|notify)', re.IGNORECASE), 'rtos_sync_unit', 8),
    (re.compile(r'(?:alloc|free|heap|mem|copy|move|write|read)', re.IGNORECASE), 'memory_transfer_unit', 6),
    (re.compile(r'(?:dma|spi|i2c|uart|can|lin|adc|wdg|watchdog|flash|nvic|hal|driver)', re.IGNORECASE), 'embedded_driver_unit', 7),
)
_NOISY_BASENAME_CAPS = {
    'port.c': 2,
    'portmacro.h': 2,
    'portasm.h': 2,
    'portASM.h': 2,
    'ISR_Support.h': 2,
    'secure_context.c': 2,
    'secure_heap.c': 2,
}
_C_FAMILY_CALL_KEYWORDS = {
    'if',
    'for',
    'while',
    'switch',
    'return',
    'sizeof',
    'do',
    'case',
    'typedef',
}


@dataclass(slots=True)
class CandidateUnit:
    file_path: str
    language: str
    content: str
    line_start: int
    line_end: int
    chunk_type: str
    name: str | None = None
    calls: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    score: float = 0.0
    signals: list[str] = field(default_factory=list)
    context_sources: list[str] = field(default_factory=list)


def _strip_c_family_comments(content: str) -> str:
    def _preserve_newlines(match: re.Match[str]) -> str:
        return '\n' * match.group(0).count('\n')

    without_blocks = _COMMENT_BLOCK_PATTERN.sub(_preserve_newlines, content)
    return _COMMENT_LINE_PATTERN.sub('', without_blocks)


def _path_score_adjustment(file_path: str, *, selected_paths: set[str] | None = None) -> tuple[int, list[str]]:
    if selected_paths and file_path in selected_paths:
        return 0, []

    normalized = file_path.replace('\\', '/')
    score = 0
    signals: list[str] = []
    for pattern, label, weight in _PRIORITY_PATH_PATTERNS:
        if pattern.search(normalized):
            score += weight
            signals.append(label)
    for pattern, label, weight in _DEPRIORITIZED_PATH_PATTERNS:
        if pattern.search(normalized):
            score += weight
            signals.append(label)
    return score, signals


def _name_score_adjustment(name: str | None, *, file_path: str) -> tuple[int, list[str]]:
    target = str(name or Path(file_path).stem or '').strip()
    if not target:
        return 0, []
    score = 0
    signals: list[str] = []
    for pattern, label, weight in _EMBEDDED_NAME_PATTERNS:
        if pattern.search(target):
            score += weight
            signals.append(label)
    return score, signals


def _shape_penalty(
    content: str,
    *,
    file_path: str,
    chunk_type: str,
    selected_paths: set[str] | None = None,
) -> tuple[int, list[str]]:
    if selected_paths and file_path in selected_paths:
        return 0, []

    nonempty_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not nonempty_lines:
        return 0, []

    comment_like = sum(
        1
        for line in nonempty_lines
        if line.startswith('//') or line.startswith('/*') or line.startswith('*') or line.startswith('*/')
    )
    macro_lines = sum(1 for line in nonempty_lines if line.startswith('#'))

    score = 0
    signals: list[str] = []
    if (comment_like / len(nonempty_lines)) >= 0.45:
        score -= 10
        signals.append('comment_heavy_chunk')
    if (
        Path(file_path).suffix.lower() in {'.h', '.hh', '.hpp', '.hxx'}
        and chunk_type in {'module', 'struct', 'class', 'enum'}
        and (macro_lines / len(nonempty_lines)) >= 0.35
    ):
        score -= 8
        signals.append('macro_heavy_header')
    if (
        Path(file_path).suffix.lower() in {'.h', '.hh', '.hpp', '.hxx'}
        and chunk_type == 'module'
    ):
        score -= 28
        signals.append('header_declaration_chunk')
    return score, signals


def _extract_include_targets(content: str) -> list[str]:
    return list(dict.fromkeys(match.strip() for match in _INCLUDE_PATTERN.findall(content) if match.strip()))


def _resolve_include_path(include_name: str, *, file_path: str, file_lookup: dict[str, dict[str, Any]]) -> str | None:
    normalized = include_name.replace('\\', '/').lstrip('./')
    if not normalized:
        return None

    candidates: list[str] = []
    current_dir = Path(file_path).parent
    relative_candidate = str((current_dir / normalized).as_posix()).lstrip('./')
    basename = Path(normalized).name

    for item in (
        normalized,
        relative_candidate,
        f'include/{basename}',
        f'inc/{basename}',
        basename,
    ):
        if item in file_lookup and item != file_path and item not in candidates:
            candidates.append(item)

    basename_matches = [
        path
        for path in file_lookup
        if Path(path).name == basename and path != file_path and path not in candidates
    ]
    basename_matches.sort(
        key=lambda item: (
            0 if item.startswith('include/') else 1,
            0 if item.startswith(str(current_dir).strip('./')) else 1,
            len(item),
            item,
        )
    )
    candidates.extend(basename_matches[:3])
    return candidates[0] if candidates else None


def _candidate_bucket(file_path: str) -> str:
    parts = [part for part in Path(file_path).parts if part not in {'.', ''}]
    return (parts[0].lower() if parts else 'root')


def _candidate_bucket_cap(bucket: str, *, max_units: int) -> int:
    if bucket == 'portable':
        return max(2, min(12, max_units // 6 if max_units else 2))
    if bucket in {'examples', 'example', 'docs', 'doc', 'tests', 'test'}:
        return max(2, min(8, max_units // 8 if max_units else 2))
    return max(4, max_units // 3 if max_units else 4)


def _collect_nearest_build_sections(workspace: Path, file_path: str) -> list[str]:
    relative_parent = Path(file_path).parent
    parent_chain = [relative_parent, *relative_parent.parents]
    sections: list[str] = []
    seen: set[str] = set()

    for parent in parent_chain:
        parent_rel = Path('') if str(parent) == '.' else parent
        disk_parent = workspace / parent_rel
        if not disk_parent.exists():
            continue
        for build_name in BUILD_FILE_CANDIDATES:
            build_path = disk_parent / build_name
            build_key = str(build_path)
            if not build_path.exists() or not build_path.is_file() or build_key in seen:
                continue
            try:
                label = build_path.relative_to(workspace)
            except ValueError:
                label = build_path
            try:
                sections.append(f'# {label}\n{build_path.read_text(encoding="utf-8", errors="ignore")[:800]}')
                seen.add(build_key)
            except OSError:
                continue
            if len(sections) >= 2:
                return sections
        for build_path in sorted(disk_parent.glob('*.mk')):
            build_key = str(build_path)
            if build_key in seen:
                continue
            try:
                label = build_path.relative_to(workspace)
            except ValueError:
                label = build_path
            try:
                sections.append(f'# {label}\n{build_path.read_text(encoding="utf-8", errors="ignore")[:800]}')
                seen.add(build_key)
            except OSError:
                continue
            if len(sections) >= 2:
                return sections
    return sections


def _select_diversified_candidates(
    candidates: list[CandidateUnit],
    *,
    max_units: int,
    selected_paths: set[str],
) -> list[CandidateUnit]:
    if max_units <= 0:
        return candidates

    basename_counts: defaultdict[str, int] = defaultdict(int)
    bucket_counts: defaultdict[str, int] = defaultdict(int)
    per_file_counts: defaultdict[str, int] = defaultdict(int)
    selected: list[CandidateUnit] = []
    default_basename_cap = max(3, min(6, max_units // 10 if max_units else 3))

    for candidate in candidates:
        if len(selected) >= max_units:
            break
        if candidate.file_path in selected_paths:
            selected.append(candidate)
            continue

        basename = Path(candidate.file_path).name
        bucket = _candidate_bucket(candidate.file_path)
        basename_cap = _NOISY_BASENAME_CAPS.get(basename, default_basename_cap)
        bucket_cap = _candidate_bucket_cap(bucket, max_units=max_units)
        per_file_cap = 2 if Path(candidate.file_path).suffix.lower() in {'.h', '.hh', '.hpp', '.hxx'} else 4

        if (
            basename_counts[basename] >= basename_cap
            or bucket_counts[bucket] >= bucket_cap
            or per_file_counts[candidate.file_path] >= per_file_cap
        ):
            continue

        selected.append(candidate)
        basename_counts[basename] += 1
        bucket_counts[bucket] += 1
        per_file_counts[candidate.file_path] += 1

    return selected[:max_units]


def _chunk_type_name(chunk: CodeChunk | CandidateUnit) -> str:
    chunk_type = getattr(chunk, 'chunk_type', '')
    return str(getattr(chunk_type, 'value', chunk_type) or '').strip().lower()


def _trim_context_snippet(
    content: str,
    *,
    anchors: Iterable[str] | None = None,
    max_chars: int,
) -> str:
    normalized = str(content or '').strip()
    if not normalized:
        return ''

    normalized = re.sub(r'^\s*/\*.*?\*/\s*', '', normalized, count=1, flags=re.DOTALL)
    normalized = re.sub(r'^(?:\s*//.*\n)+', '', normalized, count=1, flags=re.MULTILINE)

    for anchor in anchors or []:
        symbol = str(anchor or '').strip()
        if not symbol:
            continue
        index = normalized.find(symbol)
        if index < 0:
            continue
        start = max(0, index - min(320, index))
        end = min(len(normalized), start + max_chars)
        return normalized[start:end].strip()

    return normalized[:max_chars].strip()


def _extract_simple_calls(content: str) -> list[str]:
    matches = re.findall(r'\b([A-Za-z_]\w*)\s*\(', _strip_c_family_comments(content))
    return list(dict.fromkeys(match for match in matches if match not in _C_FAMILY_CALL_KEYWORDS))[:24]


def _extract_signature_name(signature_text: str) -> str | None:
    normalized = ' '.join(signature_text.split())
    if not normalized or normalized.startswith(('if ', 'for ', 'while ', 'switch ', 'typedef ')):
        return None
    match = re.search(
        r'([A-Za-z_~]\w*(?:::\w+)*)\s*\([^;{}]*\)\s*(?:const\s*)?(?:noexcept\s*)?\{',
        normalized,
    )
    if not match:
        return None
    name = match.group(1).split('::')[-1]
    return None if name in _C_FAMILY_CALL_KEYWORDS else name


def _find_signature_start(lines: list[str], index: int) -> int:
    start = index
    while start > 0 and (index - start) < 2:
        previous = lines[start - 1].strip()
        if (
            not previous
            or previous.startswith(('#', '//', '/*', '*', '*/'))
            or previous.endswith(';')
            or previous.endswith('}')
            or '{' in previous
        ):
            break
        start -= 1
    return start


def _find_block_end(lines: list[str], start_line: int) -> int | None:
    brace_depth = 0
    for index in range(start_line, len(lines)):
        line = lines[index]
        brace_depth += line.count('{')
        brace_depth -= line.count('}')
        if brace_depth == 0 and '{' in ''.join(lines[start_line:index + 1]):
            return index
    return None


def _extract_multiline_c_family_chunks(
    content: str,
    *,
    file_path: str,
    language: str,
) -> list[CandidateUnit]:
    lines = content.split('\n')
    candidates: list[CandidateUnit] = []
    seen_starts: set[int] = set()

    for index, line in enumerate(lines):
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(('#', '//', '/*', '*', '*/'))
            or '(' not in stripped
        ):
            continue

        signature_start = _find_signature_start(lines, index)
        signature_end = index
        while signature_end < len(lines) and (signature_end - signature_start) < 8:
            if ';' in lines[signature_end] and '{' not in lines[signature_end]:
                break
            if '{' in lines[signature_end]:
                break
            signature_end += 1
        if signature_end >= len(lines) or '{' not in lines[signature_end]:
            continue

        signature_text = ' '.join(
            item.strip()
            for item in lines[signature_start:signature_end + 1]
            if item.strip()
        )
        name = _extract_signature_name(signature_text)
        if not name or signature_start in seen_starts:
            continue

        end_line = _find_block_end(lines, signature_end)
        if end_line is None or end_line <= signature_end:
            continue

        chunk_content = '\n'.join(lines[signature_start:end_line + 1]).strip()
        if len(chunk_content) < 40:
            continue

        seen_starts.add(signature_start)
        candidates.append(
            CandidateUnit(
                file_path=file_path,
                language=language,
                content=chunk_content,
                line_start=signature_start + 1,
                line_end=end_line + 1,
                chunk_type='method' if '::' in signature_text else 'function',
                name=name,
                calls=_extract_simple_calls(chunk_content),
                definitions=[name],
            )
        )
    return candidates


def normalize_analysis_depth(value: str | None) -> str:
    return ANALYSIS_DEPTH_ALIASES.get(str(value or '').strip().lower(), 'standard')


def get_analysis_budget(analysis_depth: str | None) -> dict[str, int]:
    return dict(ANALYSIS_DEPTH_BUDGETS[normalize_analysis_depth(analysis_depth)])


def default_max_file_size_for_depth(analysis_depth: str | None) -> int:
    return int(get_analysis_budget(analysis_depth).get('max_file_size') or 0)


def is_c_family_path(path: str | None) -> bool:
    return Path(str(path or '')).suffix.lower() in C_FAMILY_EXTENSIONS


def is_c_family_language(language: str | None) -> bool:
    return str(language or '').strip().lower() in C_FAMILY_LANGUAGES


def parse_project_languages(raw_value: Any) -> list[str]:
    if isinstance(raw_value, (list, tuple)):
        return [
            str(item).strip().lower()
            for item in raw_value
            if str(item).strip()
        ]
    text = str(raw_value or '').strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = [text]
    return [
        str(item).strip().lower()
        for item in (parsed if isinstance(parsed, list) else [parsed])
        if str(item).strip()
    ]


def project_likely_c_family(project, file_paths: Iterable[str] | None = None) -> bool:
    explicit_paths = [item for item in (file_paths or []) if is_c_family_path(item)]
    if explicit_paths:
        return True
    languages = parse_project_languages(getattr(project, 'programming_languages', ''))
    return any(language in C_FAMILY_LANGUAGES for language in languages)


def build_language_profile(
    file_items: Iterable[dict[str, Any]] | None,
    *,
    selected_file_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    total_code_files = 0
    c_family_files = 0
    selected_paths = [
        str(item).strip()
        for item in (selected_file_paths or [])
        if str(item).strip()
    ]
    selected_c_family = 0

    for item in (file_items or []):
        file_path = str((item or {}).get('path') or '').strip()
        if not file_path:
            continue
        suffix = Path(file_path).suffix.lower()
        if suffix not in C_FAMILY_EXTENSIONS and suffix not in {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.php',
            '.rb', '.kt', '.swift', '.m', '.mm', '.sql', '.sh', '.vue',
        }:
            continue
        total_code_files += 1
        language = 'cpp' if suffix in {'.cc', '.cpp', '.cxx', '.hh', '.hpp', '.hxx'} else 'c' if suffix in {'.c', '.h'} else suffix.lstrip('.')
        counter[language] += 1
        if language in C_FAMILY_LANGUAGES:
            c_family_files += 1
        if selected_paths and file_path in selected_paths and language in C_FAMILY_LANGUAGES:
            selected_c_family += 1

    selected_count = len(selected_paths)
    c_family_ratio = (c_family_files / total_code_files) if total_code_files else 0.0
    selected_ratio = (selected_c_family / selected_count) if selected_count else 0.0
    dominant_language = counter.most_common(1)[0][0] if counter else 'text'
    is_c_family_dominant = (
        (selected_count > 0 and selected_ratio >= 0.6)
        or (selected_count == 0 and dominant_language in C_FAMILY_LANGUAGES and c_family_ratio >= 0.3)
    )
    return {
        'dominant_language': dominant_language,
        'dominant_family': 'c_family' if is_c_family_dominant else dominant_language,
        'is_c_family_dominant': is_c_family_dominant,
        'c_family_ratio': round(c_family_ratio, 4),
        'selected_c_family_ratio': round(selected_ratio, 4),
        'selected_files_count': selected_count,
        'total_code_files': total_code_files,
        'c_family_files': c_family_files,
        'language_distribution': dict(counter),
    }


def get_c_family_prompt_text() -> str:
    return (
        '请以汽车级 MCU 嵌入式 C/C++ 安全审计专家的视角分析当前代码单元。'
        '重点关注缓冲区越界、整数溢出/截断、空指针、UAF、double free、未初始化内存、'
        '资源泄漏、竞态、死锁、ISR/任务并发共享数据、返回值未检查、API 契约误用、'
        '格式化字符串和危险标准库调用。'
        '请基于当前代码与补充上下文给出根因、触发条件、影响场景、精确位置和可执行修复建议。'
    )


def _count_matches(content: str, patterns: Iterable[tuple[re.Pattern[str], str, int]]) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []
    for pattern, label, weight in patterns:
        matches = pattern.findall(content)
        if not matches:
            continue
        score += min(len(matches), 3) * weight
        signals.append(label)
    return score, signals


def _resource_pair_score(content: str) -> tuple[int, list[str]]:
    open_hits = {name for name, pattern in _RESOURCE_PAIR_OPENERS.items() if pattern.search(content)}
    close_hits = {name for name, pattern in _RESOURCE_PAIR_CLOSERS.items() if pattern.search(content)}
    score = 0
    signals: list[str] = []
    if ({'malloc', 'calloc', 'realloc', 'pvPortMalloc', 'new'} & open_hits) and not ({'free', 'vPortFree', 'delete'} & close_hits):
        score += 18
        signals.append('resource_release_asymmetry')
    if ({'lock', 'mutex_lock'} & open_hits) and not ({'unlock', 'mutex_unlock'} & close_hits):
        score += 18
        signals.append('lock_unlock_asymmetry')
    return score, signals


def score_candidate_chunk(
    chunk: CodeChunk | CandidateUnit,
    *,
    file_path: str,
    selected_paths: set[str] | None = None,
) -> tuple[float, list[str]]:
    content = chunk.content
    scoring_content = _strip_c_family_comments(content)
    if not scoring_content.strip():
        scoring_content = content
    score = 0.0
    signals: list[str] = []
    chunk_type = _chunk_type_name(chunk)
    for patterns in (_DANGEROUS_API_PATTERNS, _BOUNDARY_PATTERNS, _CONCURRENCY_PATTERNS, _QUALITY_PATTERNS):
        partial_score, partial_signals = _count_matches(scoring_content, patterns)
        score += partial_score
        signals.extend(partial_signals)
    pair_score, pair_signals = _resource_pair_score(scoring_content)
    score += pair_score
    signals.extend(pair_signals)
    if chunk_type in {'function', 'method', 'struct', 'class', 'enum'}:
        score += 8
    if getattr(chunk, 'name', None):
        score += 3
    path_score, path_signals = _path_score_adjustment(file_path, selected_paths=selected_paths)
    score += path_score
    signals.extend(path_signals)
    name_score, name_signals = _name_score_adjustment(getattr(chunk, 'name', None), file_path=file_path)
    score += name_score
    signals.extend(name_signals)
    shape_score, shape_signals = _shape_penalty(
        content,
        file_path=file_path,
        chunk_type=chunk_type,
        selected_paths=selected_paths,
    )
    score += shape_score
    signals.extend(shape_signals)
    if selected_paths and file_path in selected_paths:
        score += 32
        signals.append('selected_file')
    return score, list(dict.fromkeys(signals))


def collect_candidate_units(
    file_items: Iterable[dict[str, Any]],
    *,
    analysis_depth: str,
    selected_file_paths: Iterable[str] | None = None,
) -> list[CandidateUnit]:
    splitter = CodeSplitter(
        max_chunk_size=1800,
        min_chunk_size=80,
        overlap_size=80,
        preserve_structure=True,
        use_tree_sitter=True,
    )
    selected_paths = {
        str(item).strip()
        for item in (selected_file_paths or [])
        if str(item).strip()
    }
    budget = get_analysis_budget(analysis_depth)
    candidates: list[CandidateUnit] = []

    for item in file_items:
        file_path = str(item.get('path') or '').strip()
        if not is_c_family_path(file_path):
            continue
        content = str(item.get('content') or '')
        if not content.strip():
            continue
        language = 'cpp' if Path(file_path).suffix.lower() in {'.cc', '.cpp', '.cxx', '.hh', '.hpp', '.hxx'} else 'c'
        structured_candidates = _extract_multiline_c_family_chunks(
            content,
            file_path=file_path,
            language=language,
        )
        if structured_candidates:
            relevant_chunks: list[CodeChunk | CandidateUnit] = structured_candidates
        else:
            chunks = splitter.split_file(content, file_path, language=language)
            relevant_chunks = [
                chunk
                for chunk in chunks
                if chunk.content.strip()
                and chunk.chunk_type.value in {'function', 'method', 'struct', 'class', 'enum', 'module'}
            ]
            if not relevant_chunks:
                relevant_chunks = [
                    CodeChunk(
                        id='',
                        content=content,
                        file_path=file_path,
                        language=language,
                        chunk_type=chunks[0].chunk_type if chunks else ChunkType.MODULE,
                        line_start=1,
                        line_end=max(1, content.count('\n') + 1),
                    )
                ]
        for chunk in relevant_chunks:
            score, signals = score_candidate_chunk(
                chunk,
                file_path=file_path,
                selected_paths=selected_paths,
            )
            if score <= 0 and not (selected_paths and file_path in selected_paths):
                continue
            chunk_type = _chunk_type_name(chunk) or 'module'
            candidates.append(
                CandidateUnit(
                    file_path=file_path,
                    language=language,
                    content=chunk.content,
                    line_start=max(1, int(chunk.line_start or 1)),
                    line_end=max(int(chunk.line_end or 1), max(1, int(chunk.line_start or 1))),
                    chunk_type=chunk_type,
                    name=chunk.name,
                    calls=list(chunk.calls or []),
                    definitions=list(chunk.definitions or []),
                    score=score,
                    signals=signals,
                )
            )

    candidates.sort(
        key=lambda item: (
            1 if item.file_path in selected_paths else 0,
            item.score,
            item.line_end - item.line_start,
        ),
        reverse=True,
    )
    max_units = int(budget.get('max_units') or 0)
    if max_units <= 0:
        return candidates
    return _select_diversified_candidates(
        candidates,
        max_units=max_units,
        selected_paths=selected_paths,
    )


def _append_context_section(
    sections: list[str],
    *,
    title: str,
    content: str,
    context_sources: list[str],
    source_id: str,
    remaining_chars: int,
    section_limit: int = 1800,
) -> int:
    if remaining_chars <= 0:
        return remaining_chars
    normalized = str(content or '').strip()
    if not normalized:
        return remaining_chars
    snippet = normalized[: min(section_limit, remaining_chars)]
    sections.append(f'[{title}]\n{snippet}')
    context_sources.append(source_id)
    return remaining_chars - len(snippet)


def _find_header_source_pair(file_path: str, file_lookup: dict[str, dict[str, Any]]) -> str | None:
    path = Path(file_path)
    suffix = path.suffix.lower()
    for current_suffixes, candidate_suffixes in _HEADER_SOURCE_SUFFIX_GROUPS:
        if suffix not in current_suffixes:
            continue
        for candidate_suffix in candidate_suffixes:
            candidate_path = str(path.with_suffix(candidate_suffix)).replace('\\', '/')
            if candidate_path in file_lookup:
                return candidate_path
    return None


def build_candidate_context(
    workspace: Path,
    candidate: CandidateUnit,
    *,
    all_candidates: Iterable[CandidateUnit],
    file_lookup: dict[str, dict[str, Any]],
    analysis_depth: str,
) -> tuple[str, list[str]]:
    budget = get_analysis_budget(analysis_depth)
    remaining_chars = int((budget.get('context_token_budget') or 0) * 4)
    if remaining_chars <= 0:
        return '', []

    sections: list[str] = []
    context_sources: list[str] = []
    pair_path = _find_header_source_pair(candidate.file_path, file_lookup)
    if pair_path:
        pair_content = _trim_context_snippet(
            str(file_lookup[pair_path].get('content') or ''),
            anchors=[candidate.name, *(candidate.definitions or [])],
            max_chars=1500,
        )
        remaining_chars = _append_context_section(
            sections,
            title='头源文件配对上下文',
            content=pair_content,
            context_sources=context_sources,
            source_id=f'header_source:{pair_path}',
            remaining_chars=remaining_chars,
            section_limit=1500,
        )

    current_file_content = str(file_lookup.get(candidate.file_path, {}).get('content') or '')
    include_paths: list[str] = []
    for include_name in _extract_include_targets(current_file_content)[:6]:
        resolved = _resolve_include_path(include_name, file_path=candidate.file_path, file_lookup=file_lookup)
        if not resolved or resolved == pair_path or resolved in include_paths:
            continue
        include_paths.append(resolved)
        if len(include_paths) >= 2:
            break
    include_paths.sort(
        key=lambda path: (
            0 if candidate.name and candidate.name in str(file_lookup.get(path, {}).get('content') or '') else 1,
            0 if path.startswith('include/') else 1,
            len(path),
            path,
        )
    )
    for include_path in include_paths:
        include_content = _trim_context_snippet(
            str(file_lookup.get(include_path, {}).get('content') or ''),
            anchors=[candidate.name, *(candidate.definitions or [])],
            max_chars=1200,
        )
        remaining_chars = _append_context_section(
            sections,
            title='相关头文件与接口声明',
            content=include_content,
            context_sources=context_sources,
            source_id=f'include_dependency:{include_path}',
            remaining_chars=remaining_chars,
            section_limit=1200,
        )

    callers: list[CandidateUnit] = []
    callees: list[CandidateUnit] = []
    seen_context_keys = {candidate.file_path}
    for item in all_candidates:
        if item.file_path == candidate.file_path and item.line_start == candidate.line_start:
            continue
        if candidate.name and candidate.name in item.calls and len(callers) < 2:
            callers.append(item)
        if item.name and item.name in candidate.calls and len(callees) < 2:
            callees.append(item)
    for related in callers + callees:
        context_key = f'{related.file_path}:{related.line_start}:{related.line_end}'
        if context_key in seen_context_keys:
            continue
        seen_context_keys.add(context_key)
        remaining_chars = _append_context_section(
            sections,
            title='相关调用上下文',
            content=related.content,
            context_sources=context_sources,
            source_id=f'related_chunk:{context_key}',
            remaining_chars=remaining_chars,
            section_limit=1200,
        )

    macro_matches = _MACRO_PATTERN.findall(current_file_content)
    type_matches = _TYPE_PATTERN.findall(current_file_content)
    if macro_matches or type_matches:
        macro_text = '\n'.join(list(macro_matches)[:2] + list(type_matches)[:2])
        remaining_chars = _append_context_section(
            sections,
            title='关键宏与类型定义',
            content=macro_text,
            context_sources=context_sources,
            source_id=f'macros_types:{candidate.file_path}',
            remaining_chars=remaining_chars,
            section_limit=900,
        )

    build_sections = _collect_nearest_build_sections(workspace, candidate.file_path)
    if not build_sections:
        for build_path in sorted(workspace.rglob('*.mk')):
            if len(build_sections) >= 2:
                break
            try:
                build_sections.append(f'# {build_path.relative_to(workspace)}\n{build_path.read_text(encoding="utf-8", errors="ignore")[:800]}')
            except OSError:
                continue
    if build_sections:
        remaining_chars = _append_context_section(
            sections,
            title='构建线索',
            content='\n\n'.join(build_sections[:2]),
            context_sources=context_sources,
            source_id='build_hints',
            remaining_chars=remaining_chars,
            section_limit=1200,
        )

    return '\n\n'.join(sections).strip(), context_sources


def normalize_c_family_issue_type(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    aliases = {
        'memory_leak': 'resource_leak',
        'leak': 'resource_leak',
        'oob': 'out_of_bounds',
        'out_of_bounds_access': 'out_of_bounds',
        'uaf': 'use_after_free',
        'double delete': 'double_free',
        'nullptr_dereference': 'null_dereference',
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in C_FAMILY_TARGET_VULNERABILITIES:
        return normalized
    return normalized or 'api_contract_violation'


def enrich_issue_metadata(
    issue: dict[str, Any],
    *,
    candidate: CandidateUnit,
    language_profile: dict[str, Any],
    context_sources: Iterable[str],
    verification_status: str,
    verification_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(issue)
    issue_type = normalize_c_family_issue_type(
        payload.get('issue_type') or payload.get('type') or payload.get('vulnerability_type')
    )
    payload['issue_type'] = issue_type
    if 'type' in payload and not payload.get('type'):
        payload['type'] = issue_type
    try:
        local_line = int(payload.get('line') or payload.get('line_number') or 0)
    except (TypeError, ValueError):
        local_line = 0
    if local_line > 0:
        payload['line'] = candidate.line_start + local_line - 1
    else:
        payload['line'] = candidate.line_start
    payload['line_number'] = payload['line']
    payload['file_path'] = candidate.file_path
    payload['context_sources'] = list(dict.fromkeys(context_sources))
    payload['verification_status'] = verification_status
    payload['language_profile'] = dict(language_profile or {})
    metadata = dict(payload.get('ai_explanation') or {})
    metadata.update(
        {
            'chunk_name': candidate.name,
            'chunk_type': candidate.chunk_type,
            'chunk_line_start': candidate.line_start,
            'chunk_line_end': candidate.line_end,
            'context_sources': payload['context_sources'],
            'language_profile': payload['language_profile'],
            'verification_status': verification_status,
        }
    )
    cwe_id = str(payload.get('cwe_id') or '').strip()
    if cwe_id:
        metadata['cwe_id'] = cwe_id
    if verification_details:
        metadata['verification'] = verification_details
    payload['ai_explanation'] = metadata
    return payload


def dedupe_issue_key(issue: dict[str, Any]) -> tuple[str, int, str]:
    try:
        line_number = int(issue.get('line') or issue.get('line_number') or 0)
    except (TypeError, ValueError):
        line_number = 0
    return (
        str(issue.get('file_path') or '').strip(),
        line_number,
        normalize_c_family_issue_type(issue.get('issue_type') or issue.get('type')),
    )


def build_c_family_analysis_profile(
    *,
    analysis_depth: str,
    language_profile: dict[str, Any],
    context_sources: Iterable[str],
    prompt_template_id: str | None = None,
    rule_set_id: str | None = None,
    engine: str = 'llm_c_family',
) -> dict[str, Any]:
    return {
        'engine': engine,
        'analysis_depth': normalize_analysis_depth(analysis_depth),
        'profile_mode': 'c_family_deep' if language_profile.get('is_c_family_dominant') else 'default',
        'prompt_template_id': prompt_template_id,
        'rule_set_id': rule_set_id,
        'language_profile': dict(language_profile or {}),
        'context_sources': list(dict.fromkeys(context_sources)),
        'target_vulnerabilities': list(C_FAMILY_TARGET_VULNERABILITIES),
    }
