from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.tools.file_tool import (
    FileReadTool,
    FileSearchTool,
    ListFilesTool,
)
from apps.deepaudit.agent_task.agent_runner import (
    _effective_target_files_from_input,
    _filter_tool_groups_for_scenario,
    _normalize_finding_payload,
    _normalize_agent_input,
    run_orchestrator_agent_async,
    _validate_runtime_target_files,
)


class AgentRunnerScopeTestCase(SimpleTestCase):
    databases = {"default"}

    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix='focusaudit-agent-runner-'))
        self.sibling_workspace = Path(f'{self.workspace}-sibling')
        (self.workspace / 'src').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'src' / 'module' / 'main.c').write_text('int main(void) { return 0; }\n', encoding='utf-8')
        (self.workspace / 'src' / 'module' / 'helper.h').write_text('#pragma once\n', encoding='utf-8')
        self.sibling_workspace.mkdir(parents=True, exist_ok=True)
        (self.sibling_workspace / 'outside.c').write_text('int outside(void) { return 1; }\n', encoding='utf-8')

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)
        shutil.rmtree(self.sibling_workspace, ignore_errors=True)

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

    def test_validate_runtime_target_files_rejects_sibling_prefix_paths(self) -> None:
        validation = _validate_runtime_target_files(
            str(self.workspace),
            [f'../{self.sibling_workspace.name}/outside.c'],
        )

        self.assertEqual(validation['valid_files'], [])
        self.assertEqual(validation['outside_targets'], [f'../{self.sibling_workspace.name}/outside.c'])

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

    def test_inventory_tool_policy_filters_vulnerability_and_poc_tools(self) -> None:
        tool_groups = {
            "recon": {
                "list_files": object(),
                "search_code": object(),
                "semgrep_scan": object(),
                "gitleaks_scan": object(),
            },
            "analysis": {
                "read_file": object(),
                "smart_scan": object(),
                "run_code": object(),
                "create_vulnerability_report": object(),
            },
            "verification": {
                "read_file": object(),
                "vulnerability_validation": object(),
                "run_code": object(),
            },
        }

        filtered = _filter_tool_groups_for_scenario(
            tool_groups,
            {
                "objective_type": "inventory",
                "tool_policy": {
                    "allowed_tools": [
                        "list_files",
                        "read_file",
                        "search_code",
                        "smart_scan",
                    ],
                    "blocked_tools": [
                        "semgrep_scan",
                        "gitleaks_scan",
                        "run_code",
                        "vulnerability_validation",
                        "create_vulnerability_report",
                    ],
                },
            },
        )

        self.assertEqual(set(filtered["recon"]), {"list_files", "search_code"})
        self.assertEqual(set(filtered["analysis"]), {"read_file", "smart_scan"})
        self.assertEqual(set(filtered["verification"]), {"read_file"})

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

    def test_run_orchestrator_agent_async_normalizes_input_in_worker_thread(self) -> None:
        result = SimpleNamespace(
            success=True,
            data={"findings": []},
            error=None,
            duration_ms=1,
        )
        orchestrator_run = AsyncMock(return_value=result)
        fake_orchestrator = SimpleNamespace(run=orchestrator_run)

        class FakeEventManager:
            def __init__(self, task_id: str) -> None:
                self.task_id = task_id
                self.current_phase = None
                self.events: list[dict[str, object]] = []

            async def init_sequence(self) -> None:
                return None

            async def emit(self, **kwargs) -> None:
                self.events.append(kwargs)
                self.current_phase = kwargs.get("phase", self.current_phase)

        class FakeEventEmitter:
            def __init__(self, task_id: str, event_manager: FakeEventManager) -> None:
                self.task_id = task_id
                self.event_manager = event_manager
                self.current_phase = None

            async def emit_phase_start(self, phase: str, message: str) -> None:
                self.current_phase = phase

            async def emit_phase_complete(self, phase: str, message: str) -> None:
                self.current_phase = phase

            async def emit_task_complete(self, **kwargs) -> None:
                return None

            async def emit_task_error(self, message: str) -> None:
                return None

        with (
            patch("apps.deepaudit.agent_task.agent_runner.EventManager", FakeEventManager),
            patch("apps.deepaudit.agent_task.agent_runner.AgentEventEmitter", FakeEventEmitter),
            patch("apps.deepaudit.agent_task.agent_runner._build_llm_service", return_value=object()),
            patch(
                "apps.deepaudit.agent_task.agent_runner._initialize_task_runtime_state",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "apps.deepaudit.agent_task.agent_runner._initialize_tools",
                new=AsyncMock(
                    return_value={
                        "orchestrator": {},
                        "recon": {},
                        "analysis": {},
                        "verification": {},
                    }
                ),
            ) as init_tools_mock,
            patch("apps.deepaudit.agent_task.agent_runner.OrchestratorAgent", return_value=fake_orchestrator),
            patch("apps.deepaudit.agent_task.agent_runner.ReconAgent", return_value=SimpleNamespace()),
            patch("apps.deepaudit.agent_task.agent_runner.AnalysisAgent", return_value=SimpleNamespace()),
            patch("apps.deepaudit.agent_task.agent_runner.VerificationAgent", return_value=SimpleNamespace()),
            patch("apps.deepaudit.agent_task.agent_task_services.refresh_task_snapshot", lambda task_id: None),
        ):
            asyncio.run(
                run_orchestrator_agent_async(
                    "task-async-normalize",
                    {
                        "project_name": "Demo Project",
                        "target_files": ["src/module/main.c"],
                        "audit_scope": {},
                        "agent_config": {},
                    },
                    str(self.workspace),
                )
            )

        self.assertEqual(orchestrator_run.await_count, 1)
        self.assertTrue(init_tools_mock.await_args.kwargs["enable_c_family_rag_fallback"])


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
