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
    _validate_runtime_target_files,
)


class AgentRunnerScopeTestCase(SimpleTestCase):
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
