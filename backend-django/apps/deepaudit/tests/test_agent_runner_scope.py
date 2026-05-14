from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.tools.file_tool import (
    FileReadTool,
    FileSearchTool,
    ListFilesTool,
)
from apps.deepaudit.agent_task.agent_runner import (
    _effective_target_files_from_input,
    _normalize_finding_payload,
    _normalize_agent_input,
    _validate_runtime_target_files,
)


class AgentRunnerScopeTestCase(SimpleTestCase):
    databases = {"default"}

    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix='focusaudit-agent-runner-'))
        (self.workspace / 'src').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module' / 'main.c').write_text('int main(void) { return 0; }\n', encoding='utf-8')
        (self.workspace / 'src' / 'module' / 'helper.h').write_text('#pragma once\n', encoding='utf-8')

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_effective_target_files_prefers_selection_runtime_resolved_files(self) -> None:
        input_data = {
            'target_files': ['src/module'],
            'agent_config': {
                'selection_runtime': {
                    'resolved_target_files': ['src/module/main.c', 'src/module/helper.h'],
                },
            },
        }

        effective = _effective_target_files_from_input(input_data)

        self.assertEqual(effective, ['src/module/main.c', 'src/module/helper.h'])

    def test_validate_runtime_target_files_filters_directories_and_missing_paths(self) -> None:
        validation = _validate_runtime_target_files(
            str(self.workspace),
            ['src/module', 'src/module/main.c', 'src/missing.c'],
        )

        self.assertEqual(validation['valid_files'], ['src/module/main.c'])
        self.assertEqual(validation['directory_targets'], ['src/module'])
        self.assertEqual(validation['missing_files'], ['src/missing.c'])
        self.assertEqual(validation['outside_targets'], [])

    def test_normalize_agent_input_preserves_explicit_general_scenario(self) -> None:
        normalized = _normalize_agent_input(
            'task-1',
            {
                'target_files': ['src/module/main.c'],
                'audit_scope': {
                    'scenario_key': 'general',
                },
                'project_name': 'Demo Project',
            },
            str(self.workspace),
        )

        scenario_profile = normalized['config']['scenario_profile']
        self.assertEqual(scenario_profile['scenario_key'], 'general')
        self.assertFalse(scenario_profile['legacy_c_family'])
        self.assertEqual(normalized['config']['verification_level'], 'analysis_only')
        self.assertIn('buffer_overflow', normalized['config']['target_vulnerabilities'])

    def test_normalize_finding_payload_promotes_validation_evidence_and_fix_details(self) -> None:
        normalized = _normalize_finding_payload(
            {
                "title": "Unbounded copy in driver init",
                "vulnerability_type": "buffer_overflow",
                "severity": "high",
                "file_path": "src/module/main.c",
                "line_start": 18,
                "matched_line": "strcpy(device->name, user_name);",
                "context": "if (user_name) {\n    strcpy(device->name, user_name);\n}",
                "recommendation": "改用 snprintf，并校验输入长度。",
                "fix_code": "snprintf(device->name, sizeof(device->name), \"%s\", user_name);",
                "ai_explanation": "拷贝长度受外部输入影响，固定缓冲区可能被覆盖。",
                "evidence": "未看到任何长度检查或截断逻辑。",
                "validation": {
                    "is_vulnerable": True,
                    "verdict": "likely",
                    "detailed_analysis": "调用链允许外部名称进入固定数组，构成高可信越界写风险。",
                },
                "confidence": 0.91,
            }
        )

        assert normalized is not None
        self.assertEqual(normalized["code_snippet"], "if (user_name) {\n    strcpy(device->name, user_name);\n}")
        self.assertEqual(normalized["suggestion"], "改用 snprintf，并校验输入长度。")
        self.assertTrue(normalized["is_verified"])
        self.assertEqual(normalized["poc"]["fix_code"], "snprintf(device->name, sizeof(device->name), \"%s\", user_name);")
        self.assertEqual(normalized["poc"]["matched_line"], "strcpy(device->name, user_name);")
        self.assertEqual(normalized["poc"]["validation"]["verdict"], "likely")
        self.assertEqual(normalized["description"], "拷贝长度受外部输入影响，固定缓冲区可能被覆盖。")

    def test_normalize_finding_payload_honors_false_positive_verdict_from_nested_poc(self) -> None:
        normalized = _normalize_finding_payload(
            {
                "title": "Escaped output reported as XSS",
                "vulnerability_type": "xss",
                "severity": "medium",
                "file_path": "src/module/main.c",
                "poc": {
                    "verdict": "false_positive",
                    "validation": {
                        "is_vulnerable": False,
                        "details": "输出前已经过统一转义。",
                    },
                },
            }
        )

        assert normalized is not None
        self.assertEqual(normalized["status"], "false_positive")
        self.assertFalse(normalized["is_verified"])
        self.assertEqual(normalized["poc"]["verdict"], "false_positive")
        self.assertEqual(normalized["poc"]["validation"]["is_vulnerable"], False)


class AgentFileToolScopeTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix='focusaudit-file-tool-'))
        (self.workspace / 'src').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module' / 'main.c').write_text('int main(void) { return 0; }\n', encoding='utf-8')

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_file_tools_drop_directory_targets_from_whitelist(self) -> None:
        read_tool = FileReadTool(str(self.workspace), target_files=['src/module', 'src/module/main.c'])
        search_tool = FileSearchTool(str(self.workspace), target_files=['src/module', 'src/module/main.c'])
        list_tool = ListFilesTool(str(self.workspace), target_files=['src/module', 'src/module/main.c'])

        expected_scope = {'src/module/main.c'}
        self.assertEqual(read_tool.target_files, expected_scope)
        self.assertEqual(search_tool.target_files, expected_scope)
        self.assertEqual(list_tool.target_files, expected_scope)
