from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.deepaudit.agent_task.agent_task_model import AgentCheckpoint, AgentEvent, AgentFinding, AgentTask
from apps.deepaudit.agent_task.agent_task_services import (
    build_checkpoints,
    build_tree,
    create_task,
    execute_agent_task,
    export_agent_pdf_response,
    export_agent_report_response,
    export_agent_json_response,
    get_checkpoint_detail,
    list_checkpoints,
    persist_checkpoint,
    refresh_task_snapshot,
    resume_task_from_checkpoint,
)
from apps.deepaudit.constants import (
    AGENT_PHASE_ANALYSIS,
    AGENT_PHASE_PLANNING,
    AGENT_PHASE_RECONNAISSANCE,
    AGENT_PHASE_REPORTING,
    AGENT_PHASE_VERIFICATION,
)
from apps.deepaudit.project.project_model import AuditProject
from core.user.user_model import User


class AgentTaskServicesTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='agent-owner',
            password='not-used',
            name='Agent Owner',
        )
        self.project = AuditProject.objects.create(
            name='DeepAudit Demo',
            owner=self.user,
            source_type='repository',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            default_branch='main',
            manifest_xml='default.xml',
            group='platform',
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        self.task = self._create_task(name='Snapshot Task')

    def _create_task(self, *, name: str, status: str = 'running', current_phase: str = AGENT_PHASE_PLANNING) -> AgentTask:
        return AgentTask.objects.create(
            project=self.project,
            created_by=self.user,
            name=name,
            status=status,
            current_phase=current_phase,
            current_step=f'{current_phase} started',
            repository_url=self.project.repository_url,
            repository_type=self.project.repository_type,
            branch_name=self.project.default_branch,
            manifest_xml=self.project.manifest_xml,
            group=self.project.group,
            started_at=timezone.now(),
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def test_create_task_snapshots_repository_spec(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with patch('apps.deepaudit.agent_task.agent_task_services.require_project_role', return_value=access):
            task = create_task(
                self.user,
                {
                    'project_id': str(self.project.id),
                    'name': 'Snapshot Agent Task',
                },
            )

        self.assertEqual(task.repository_type, 'multi')
        self.assertEqual(task.repository_url, 'https://codehub.example.com/platform/manifest.git')
        self.assertEqual(task.branch_name, 'main')
        self.assertEqual(task.manifest_xml, 'default.xml')
        self.assertEqual(task.group, 'platform')

    def test_create_task_ignores_mismatched_requested_repository_type(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with (
            patch('apps.deepaudit.agent_task.agent_task_services.require_project_role', return_value=access),
            self.assertLogs('apps.deepaudit.agent_task.agent_task_services', level='WARNING') as captured,
        ):
            task = create_task(
                self.user,
                {
                    'project_id': str(self.project.id),
                    'name': 'Mismatch Agent Task',
                    'repository_type': 'single',
                },
            )

        self.assertEqual(task.repository_type, 'multi')
        self.assertEqual(task.repository_url, 'https://codehub.example.com/platform/manifest.git')
        self.assertIn('repository_type mismatch', '\n'.join(captured.output))
        warning_event = task.events.filter(is_deleted=False, event_type='warning').latest('sequence')
        self.assertEqual(warning_event.event_metadata.get('requested_repository_type'), 'single')
        self.assertEqual(warning_event.event_metadata.get('project_repository_type'), 'multi')

    def test_execute_agent_task_uses_snapshotted_repository_spec_after_project_changes(self) -> None:
        self.task.branch_name = 'release/main'
        self.task.save(update_fields=['branch_name', 'sys_update_datetime'])

        self.project.repository_url = 'https://codehub.example.com/platform/single.git'
        self.project.repository_type = 'single'
        self.project.default_branch = 'develop'
        self.project.manifest_xml = None
        self.project.group = None
        self.project.sys_modifier = self.user
        self.project.save(
            update_fields=[
                'repository_url',
                'repository_type',
                'default_branch',
                'manifest_xml',
                'group',
                'sys_modifier',
                'sys_update_datetime',
            ]
        )

        with (
            patch('apps.deepaudit.agent_task.agent_task_services.close_runtime_db_connections'),
            patch('apps.deepaudit.agent_task.agent_task_services.docker_available', return_value=True),
            patch(
                'apps.deepaudit.agent_task.agent_task_services.prepare_repository_workspace',
                return_value=(Path('/tmp/focusaudit-agent-workspace'), {'llm_config': {}, 'other_config': {}}),
            ) as mock_prepare,
            patch('apps.deepaudit.agent_task.agent_runner.run_orchestrator_agent_sync'),
            patch('apps.deepaudit.agent_task.agent_task_services.cleanup_runtime_workspace'),
        ):
            execute_agent_task(str(self.task.id))

        repository_spec = mock_prepare.call_args.kwargs['repository_spec']
        self.assertEqual(repository_spec['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_url'], 'https://codehub.example.com/platform/manifest.git')
        self.assertEqual(repository_spec['branch_name'], 'release/main')
        self.assertEqual(repository_spec['manifest_xml'], 'default.xml')
        self.assertEqual(repository_spec['group'], 'platform')
        event_messages = list(self.task.events.filter(is_deleted=False).values_list('message', flat=True))
        self.assertIn('开始按任务快照准备仓库工作区', event_messages)
        self.assertIn('任务执行将使用创建时快照的仓库规格，而不是项目当前配置', event_messages)

    def test_execute_agent_task_persists_repository_init_events(self) -> None:
        def fake_prepare_repository_workspace(*_args, **kwargs):
            callback = kwargs['event_callback']
            callback(
                'info',
                '多仓初始化命令开始执行',
                {'command': 'git mm init -u https://codehub.example.com/platform/manifest.git -b main -m default.xml'},
            )
            callback(
                'warning',
                '多仓同步命令返回非 0，已按 warning 继续执行',
                {
                    'command': 'git mm sync',
                    'exit_code': 23,
                    'stderr_tail': 'permission denied on child repo',
                    'soft_failed': True,
                },
            )
            return Path('/tmp/focusaudit-agent-workspace'), {'llm_config': {}, 'other_config': {}}

        with (
            patch('apps.deepaudit.agent_task.agent_task_services.close_runtime_db_connections'),
            patch('apps.deepaudit.agent_task.agent_task_services.docker_available', return_value=True),
            patch(
                'apps.deepaudit.agent_task.agent_task_services.prepare_repository_workspace',
                side_effect=fake_prepare_repository_workspace,
            ),
            patch('apps.deepaudit.agent_task.agent_runner.run_orchestrator_agent_sync'),
            patch('apps.deepaudit.agent_task.agent_task_services.cleanup_runtime_workspace'),
        ):
            execute_agent_task(str(self.task.id))

        event_messages = list(
            self.task.events.filter(is_deleted=False, event_type__in=['info', 'warning']).values_list('message', flat=True)
        )
        self.assertIn('多仓初始化命令开始执行', event_messages)
        self.assertIn('多仓同步命令返回非 0，已按 warning 继续执行', event_messages)
        warning_event = self.task.events.filter(is_deleted=False, event_type='warning').latest('sequence')
        self.assertEqual(warning_event.event_metadata.get('command'), 'git mm sync')
        self.assertEqual(warning_event.event_metadata.get('exit_code'), 23)
        self.assertTrue(warning_event.event_metadata.get('soft_failed'))

    def _create_event(
        self,
        task: AgentTask,
        sequence: int,
        event_type: str,
        *,
        phase: str | None = None,
        message: str | None = None,
        metadata: dict | None = None,
        tokens_used: int | None = None,
    ) -> AgentEvent:
        return AgentEvent.objects.create(
            task=task,
            sequence=sequence,
            event_type=event_type,
            phase=phase,
            message=message,
            event_metadata=metadata or {},
            tokens_used=tokens_used,
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def _seed_completed_runtime(self, task: AgentTask) -> AgentTask:
        self._create_event(task, 1, 'phase_start', phase=AGENT_PHASE_PLANNING, message='开始 planning 阶段')
        self._create_event(
            task,
            2,
            'info',
            phase=AGENT_PHASE_PLANNING,
            message='Orchestrator 正在规划',
            metadata={
                'agent_id': 'orch-1',
                'agent_name': 'Orchestrator',
                'agent_type': 'orchestrator',
                'iteration': 2,
                'tool_calls': 1,
                'tokens_used': 100,
                'status': 'running',
                'task': 'Review project and coordinate agents',
            },
            tokens_used=100,
        )
        self._create_event(task, 3, 'phase_complete', phase=AGENT_PHASE_PLANNING, message='planning 阶段完成')
        self._create_event(task, 4, 'phase_start', phase=AGENT_PHASE_RECONNAISSANCE, message='开始 reconnaissance 阶段')
        self._create_event(
            task,
            5,
            'info',
            phase=AGENT_PHASE_RECONNAISSANCE,
            message='Recon 完成项目侦察',
            metadata={
                'agent_id': 'recon-1',
                'agent_name': 'Recon Agent',
                'agent_type': 'recon',
                'parent_agent_id': 'orch-1',
                'iteration': 2,
                'tool_calls': 3,
                'tokens_used': 120,
                'findings_count': 1,
                'status': 'completed',
                'task': 'Inspect repository structure',
            },
            tokens_used=120,
        )
        self._create_event(task, 6, 'phase_complete', phase=AGENT_PHASE_RECONNAISSANCE, message='reconnaissance 阶段完成')
        self._create_event(task, 7, 'phase_start', phase=AGENT_PHASE_ANALYSIS, message='开始 analysis 阶段')
        self._create_event(
            task,
            8,
            'progress',
            phase=AGENT_PHASE_ANALYSIS,
            message='analysis 已分析 12/12 个文件',
            metadata={
                'agent_id': 'analysis-1',
                'agent_name': 'Analysis Agent',
                'agent_type': 'analysis',
                'parent_agent_id': 'orch-1',
                'iteration': 2,
                'tool_calls': 2,
                'tokens_used': 140,
                'current': 12,
                'total': 12,
                'status': 'running',
            },
            tokens_used=140,
        )
        self._create_event(
            task,
            9,
            'info',
            phase=AGENT_PHASE_ANALYSIS,
            message='Analysis 完成深度分析',
            metadata={
                'agent_id': 'analysis-1',
                'agent_name': 'Analysis Agent',
                'agent_type': 'analysis',
                'parent_agent_id': 'orch-1',
                'iteration': 3,
                'tool_calls': 4,
                'tokens_used': 240,
                'findings_count': 2,
                'status': 'completed',
                'task': 'Inspect high-risk code paths',
            },
            tokens_used=240,
        )
        self._create_event(task, 10, 'phase_complete', phase=AGENT_PHASE_ANALYSIS, message='analysis 阶段完成')
        self._create_event(task, 11, 'phase_start', phase=AGENT_PHASE_VERIFICATION, message='开始 verification 阶段')
        self._create_event(
            task,
            12,
            'info',
            phase=AGENT_PHASE_VERIFICATION,
            message='Verification 完成验证',
            metadata={
                'agent_id': 'verification-1',
                'agent_name': 'Verification Agent',
                'agent_type': 'verification',
                'parent_agent_id': 'orch-1',
                'iteration': 1,
                'tool_calls': 2,
                'tokens_used': 180,
                'findings_count': 2,
                'verified_count': 1,
                'false_positive_count': 1,
                'status': 'completed',
                'task': 'Validate candidate findings',
            },
            tokens_used=180,
        )
        self._create_event(task, 13, 'phase_complete', phase=AGENT_PHASE_VERIFICATION, message='verification 阶段完成')
        self._create_event(task, 14, 'phase_start', phase=AGENT_PHASE_REPORTING, message='开始 reporting 阶段')
        self._create_event(
            task,
            15,
            'task_complete',
            phase=AGENT_PHASE_REPORTING,
            message='报告生成完成',
            metadata={
                'agent_id': 'orch-1',
                'agent_name': 'Orchestrator',
                'agent_type': 'orchestrator',
                'iteration': 4,
                'tool_calls': 5,
                'tokens_used': 600,
                'findings_count': 2,
                'status': 'completed',
            },
            tokens_used=600,
        )

        AgentFinding.objects.create(
            task=task,
            vulnerability_type='command_injection',
            severity='critical',
            title='Unsafe command execution',
            description='Unsanitized input reaches shell execution.',
            file_path='apps/deepaudit/views.py',
            line_start=42,
            line_end=43,
            code_snippet="os.system(request.GET['cmd'])",
            is_verified=True,
            status='open',
            suggestion='Use subprocess with explicit argv.',
            poc={'verdict': 'confirmed'},
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        AgentFinding.objects.create(
            task=task,
            vulnerability_type='xss',
            severity='medium',
            title='Escaped value is already sanitized',
            description='This candidate turned out to be a false positive.',
            file_path='web/src/components/App.tsx',
            line_start=10,
            line_end=10,
            code_snippet='<div>{safeHtml}</div>',
            is_verified=False,
            status='false_positive',
            suggestion='Keep the sanitizer in place.',
            poc={'verdict': 'false_positive'},
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        return refresh_task_snapshot(
            task.id,
            status='completed',
            current_phase=AGENT_PHASE_REPORTING,
            current_step='报告生成完成',
            completed_at=timezone.now(),
            error_message='',
        )

    def _create_restorable_checkpoint(self, task: AgentTask, *, agent_type: str = 'orchestrator') -> AgentCheckpoint:
        now_text = timezone.now().isoformat()
        return AgentCheckpoint.objects.create(
            task=task,
            agent_id='orch-resume-1',
            agent_name='Orchestrator',
            agent_type=agent_type,
            iteration=2,
            status='running',
            total_tokens=128,
            tool_calls=3,
            findings_count=1,
            checkpoint_type='llm',
            checkpoint_name='可恢复状态',
            state_data={
                'version': '2.0',
                'state': {
                    'agent_id': 'orch-resume-1',
                    'agent_name': 'Orchestrator',
                    'agent_type': agent_type,
                    'parent_id': None,
                    'task': '继续编排审计',
                    'task_context': {'task_id': str(task.id), 'root_task_id': str(task.id)},
                    'inherited_context': {},
                    'knowledge_modules': [],
                    'status': 'running',
                    'iteration': 2,
                    'max_iterations': 20,
                    'messages': [],
                    'system_prompt': '',
                    'actions_taken': [],
                    'observations': [],
                    'errors': [],
                    'findings': [],
                    'created_at': now_text,
                    'started_at': now_text,
                    'last_updated': now_text,
                    'finished_at': None,
                    'waiting_for_input': False,
                    'waiting_start_time': None,
                    'waiting_reason': '',
                    'waiting_timeout_seconds': 600,
                    'final_result': None,
                    'total_tokens': 128,
                    'tool_calls': 3,
                    'stop_requested': False,
                    'max_iterations_warning_sent': False,
                },
                'runtime': {
                    'base': {
                        'iteration': 2,
                        'tool_calls': 3,
                        'total_tokens': 128,
                        'cancelled': False,
                        'incoming_handoff': None,
                        'insights': [],
                        'work_completed': ['planning completed'],
                        'last_input_data': {
                            'task': '继续编排审计',
                            'task_context': '恢复到上次状态继续执行',
                            'project_info': {'name': task.project.name, 'root': '/tmp/workspace'},
                            'config': {'target_files': []},
                            'project_root': '/tmp/workspace',
                            'task_id': str(task.id),
                        },
                    },
                    'agent': {
                        'conversation_history': [
                            {'role': 'system', 'content': 'sys'},
                            {'role': 'user', 'content': 'continue'},
                        ],
                        'steps': [],
                        'all_findings': [],
                        'runtime_context': {'task_id': str(task.id)},
                        'dispatched_tasks': {'recon': 1},
                        'agent_results': {},
                        'agent_handoffs': {},
                    },
                },
            },
            checkpoint_metadata={'phase': AGENT_PHASE_ANALYSIS, 'sequence': 9},
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def test_refresh_task_snapshot_recomputes_stats_and_reporting_phase(self) -> None:
        task = self._seed_completed_runtime(self.task)
        self.assertIsNotNone(task)
        assert task is not None

        task.refresh_from_db()

        self.assertEqual(task.status, 'completed')
        self.assertEqual(task.current_phase, AGENT_PHASE_REPORTING)
        self.assertEqual(task.current_step, '报告生成完成')
        self.assertEqual(task.total_files, 12)
        self.assertEqual(task.analyzed_files, 12)
        self.assertEqual(task.findings_count, 2)
        self.assertEqual(task.files_with_findings, 2)
        self.assertEqual(task.verified_count, 1)
        self.assertEqual(task.false_positive_count, 1)
        self.assertEqual(task.critical_count, 1)
        self.assertEqual(task.high_count, 0)
        self.assertEqual(task.medium_count, 1)
        self.assertEqual(task.low_count, 0)
        self.assertEqual(task.total_iterations, 10)
        self.assertEqual(task.tool_calls_count, 14)
        self.assertEqual(task.tokens_used, 1140)
        self.assertEqual(task.quality_score, 77.0)
        self.assertEqual(task.security_score, 72.4)

        checkpoints = build_checkpoints(task)
        checkpoint_by_phase = {item['phase']: item for item in checkpoints}
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_PLANNING]['status'], 'completed')
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_RECONNAISSANCE]['status'], 'completed')
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_ANALYSIS]['status'], 'completed')
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_VERIFICATION]['status'], 'completed')
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_REPORTING]['status'], 'completed')

    def test_persist_checkpoint_creates_history_and_detail(self) -> None:
        task = self._seed_completed_runtime(self.task)
        assert task is not None

        checkpoint = persist_checkpoint(
            task.id,
            checkpoint_type='final',
            checkpoint_name='报告生成完成',
            phase=AGENT_PHASE_REPORTING,
            sequence=15,
        )

        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertTrue(AgentCheckpoint.objects.filter(id=checkpoint.id, is_deleted=False).exists())

        checkpoints = build_checkpoints(task)
        checkpoint_by_phase = {item['phase']: item for item in checkpoints}
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_REPORTING]['id'], str(checkpoint.id))

        persisted_list = list_checkpoints(task)
        self.assertEqual(len(persisted_list), 1)
        self.assertEqual(persisted_list[0]['id'], str(checkpoint.id))
        self.assertEqual(persisted_list[0]['checkpoint_type'], 'final')

        detail = get_checkpoint_detail(task, checkpoint.id)
        self.assertEqual(detail['id'], str(checkpoint.id))
        self.assertEqual(detail['checkpoint_type'], 'final')
        self.assertEqual(detail['task_id'], task.id)
        self.assertTrue(detail['events'])
        self.assertIn('task', detail['state_data'])
        self.assertIn('phase', detail['metadata'])

    @patch("apps.deepaudit.agent_task.agent_task_services.dispatch_deepaudit_task", return_value=None)
    def test_resume_task_from_checkpoint_creates_new_task(self, mock_dispatch) -> None:
        task = self._seed_completed_runtime(self.task)
        assert task is not None
        restorable = self._create_restorable_checkpoint(task)
        checkpoint = persist_checkpoint(
            task.id,
            checkpoint_type='final',
            checkpoint_name='报告生成完成',
            phase=AGENT_PHASE_REPORTING,
            sequence=15,
        )
        assert checkpoint is not None

        resumed = resume_task_from_checkpoint(self.user, task.id, str(checkpoint.id))

        self.assertNotEqual(resumed.id, task.id)
        self.assertEqual(resumed.project_id, task.project_id)
        self.assertEqual(resumed.status, 'pending')
        self.assertEqual(resumed.audit_scope.get('resume_from_checkpoint_id'), str(restorable.id))
        self.assertEqual(resumed.audit_scope.get('resume_from_task_id'), task.id)
        self.assertEqual(resumed.agent_config.get('resume', {}).get('requested_checkpoint_id'), str(checkpoint.id))
        self.assertEqual(resumed.agent_config.get('resume', {}).get('resume_checkpoint_id'), str(restorable.id))
        self.assertEqual(resumed.repository_url, task.repository_url)
        self.assertEqual(resumed.repository_type, task.repository_type)
        self.assertEqual(resumed.branch_name, task.branch_name)
        self.assertEqual(resumed.manifest_xml, task.manifest_xml)
        self.assertEqual(resumed.group, task.group)
        mock_dispatch.assert_called_once()

    def test_refresh_task_snapshot_preserves_last_real_phase_on_failure(self) -> None:
        failed_task = self._create_task(name='Failed Task', current_phase=AGENT_PHASE_ANALYSIS)
        self._create_event(failed_task, 1, 'phase_start', phase=AGENT_PHASE_PLANNING, message='开始 planning 阶段')
        self._create_event(failed_task, 2, 'phase_complete', phase=AGENT_PHASE_PLANNING, message='planning 阶段完成')
        self._create_event(failed_task, 3, 'phase_start', phase=AGENT_PHASE_RECONNAISSANCE, message='开始 reconnaissance 阶段')
        self._create_event(failed_task, 4, 'phase_complete', phase=AGENT_PHASE_RECONNAISSANCE, message='reconnaissance 阶段完成')
        self._create_event(failed_task, 5, 'phase_start', phase=AGENT_PHASE_ANALYSIS, message='开始 analysis 阶段')
        self._create_event(failed_task, 6, 'task_error', phase=AGENT_PHASE_ANALYSIS, message='analysis crashed')

        refresh_task_snapshot(
            failed_task.id,
            status='failed',
            current_phase=AGENT_PHASE_ANALYSIS,
            current_step='analysis crashed',
            completed_at=timezone.now(),
            error_message='analysis crashed',
        )
        failed_task.refresh_from_db()

        self.assertEqual(failed_task.status, 'failed')
        self.assertEqual(failed_task.current_phase, AGENT_PHASE_ANALYSIS)
        self.assertEqual(failed_task.current_step, 'analysis crashed')

        checkpoints = build_checkpoints(failed_task)
        checkpoint_by_phase = {item['phase']: item for item in checkpoints}
        self.assertEqual(checkpoint_by_phase[AGENT_PHASE_ANALYSIS]['status'], 'failed')

    def test_refresh_task_snapshot_infers_file_counts_for_legacy_targeted_tasks(self) -> None:
        legacy_task = AgentTask.objects.create(
            project=self.project,
            created_by=self.user,
            name='Legacy File Count Task',
            status='completed',
            current_phase=AGENT_PHASE_PLANNING,
            current_step='报告生成完成',
            target_files=['a.py', 'b.py', 'c.py'],
            started_at=timezone.now(),
            completed_at=timezone.now(),
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        self._create_event(legacy_task, 1, 'phase_start', phase=AGENT_PHASE_PLANNING, message='开始 planning 阶段')
        self._create_event(
            legacy_task,
            2,
            'dispatch',
            phase=AGENT_PHASE_PLANNING,
            message='调度 analysis Agent: 深度审计指定的3个目标文件',
            metadata={'agent_name': 'Orchestrator'},
        )
        self._create_event(
            legacy_task,
            3,
            'info',
            phase=AGENT_PHASE_PLANNING,
            message='搜索结果: 搜索了 3 个文件',
            metadata={'agent_name': 'Analysis'},
        )
        self._create_event(legacy_task, 4, 'task_complete', phase=AGENT_PHASE_PLANNING, message='Orchestrator run completed.')

        refresh_task_snapshot(legacy_task.id, status='completed', completed_at=timezone.now())
        legacy_task.refresh_from_db()

        self.assertEqual(legacy_task.total_files, 3)
        self.assertEqual(legacy_task.analyzed_files, 3)
        self.assertEqual(legacy_task.indexed_files, 3)

    def test_build_tree_uses_agent_metadata_and_falls_back_for_legacy_tasks(self) -> None:
        completed_task = self._seed_completed_runtime(self.task)
        assert completed_task is not None

        nodes = build_tree(completed_task)
        node_by_id = {item['agent_id']: item for item in nodes}

        self.assertIn('orch-1', node_by_id)
        self.assertIn('recon-1', node_by_id)
        self.assertIn('analysis-1', node_by_id)
        self.assertIn('verification-1', node_by_id)
        self.assertEqual(node_by_id['orch-1']['agent_type'], 'orchestrator')
        self.assertEqual(node_by_id['recon-1']['parent_agent_id'], 'orch-1')
        self.assertEqual(node_by_id['analysis-1']['parent_agent_id'], 'orch-1')
        self.assertEqual(node_by_id['verification-1']['parent_agent_id'], 'orch-1')
        self.assertEqual(node_by_id['orch-1']['findings_count'], 2)

        legacy_task = self._create_task(name='Legacy Task')
        self._create_event(legacy_task, 1, 'phase_start', phase=AGENT_PHASE_PLANNING, message='开始 planning 阶段')
        self._create_event(legacy_task, 2, 'phase_complete', phase=AGENT_PHASE_PLANNING, message='planning 阶段完成')
        self._create_event(legacy_task, 3, 'phase_start', phase=AGENT_PHASE_RECONNAISSANCE, message='开始 reconnaissance 阶段')
        self._create_event(legacy_task, 4, 'phase_complete', phase=AGENT_PHASE_RECONNAISSANCE, message='reconnaissance 阶段完成')

        legacy_nodes = build_tree(legacy_task)
        self.assertEqual(legacy_nodes[0]['agent_type'], 'orchestrator')
        self.assertTrue(any(item['agent_type'] == 'recon' for item in legacy_nodes[1:]))

    def test_refresh_task_snapshot_truncates_oversized_current_step_and_checkpoint_name(self) -> None:
        task = self._create_task(name='Long Message Task')
        long_message = 'A' * 400
        self._create_event(
            task,
            1,
            'info',
            phase=AGENT_PHASE_ANALYSIS,
            message=long_message,
            metadata={
                'agent_id': 'orch-1',
                'agent_name': 'Orchestrator',
                'agent_type': 'orchestrator',
                'task': long_message,
            },
        )

        refreshed = refresh_task_snapshot(task.id)
        assert refreshed is not None
        refreshed.refresh_from_db()

        self.assertEqual(len(refreshed.current_step), 255)
        self.assertTrue(refreshed.current_step.endswith('…'))

        checkpoint = persist_checkpoint(
            task.id,
            checkpoint_name=long_message,
            phase=AGENT_PHASE_ANALYSIS,
        )
        assert checkpoint is not None
        self.assertEqual(len(checkpoint.checkpoint_name), 255)
        self.assertTrue(checkpoint.checkpoint_name.endswith('…'))

    def test_export_agent_report_response_supports_json_markdown_and_pdf(self) -> None:
        task = self._seed_completed_runtime(self.task)
        assert task is not None

        temp_dir = Path(tempfile.mkdtemp(prefix='deepaudit-report-test-'))
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        def fake_save_json_artifact(file_name: str, data: dict) -> Path:
            path = temp_dir / file_name
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            return path

        def fake_save_report_file(file_name: str, payload: bytes) -> Path:
            path = temp_dir / file_name
            path.write_bytes(payload)
            return path

        with (
            patch('apps.deepaudit.agent_task.agent_task_services.save_json_artifact', side_effect=fake_save_json_artifact),
            patch('apps.deepaudit.agent_task.agent_task_services.save_report_file', side_effect=fake_save_report_file),
            patch('apps.deepaudit.agent_task.agent_task_services.AuditArtifact.objects.update_or_create', return_value=(None, True)),
            patch('apps.deepaudit.agent_task.agent_task_services.ReportBuilder.build_agent_report', return_value=b'%PDF-test'),
        ):
            json_response = export_agent_report_response(self.user, task.id, format='json')
            markdown_response = export_agent_report_response(self.user, task.id, format='markdown')
            pdf_response = export_agent_report_response(self.user, task.id, format='pdf')
            compat_json_response = export_agent_json_response(self.user, task.id)
            compat_pdf_response = export_agent_pdf_response(self.user, task.id)

        self.assertEqual(json_response['Content-Type'], 'application/json')
        json_payload = json.loads(json_response.content.decode('utf-8'))
        self.assertIn('summary', json_payload)
        self.assertEqual(json_payload['task']['current_phase'], AGENT_PHASE_REPORTING)

        markdown_body = markdown_response.content.decode('utf-8')
        self.assertTrue(markdown_response['Content-Type'].startswith('text/markdown'))
        self.assertIn('# DeepAudit 代码审计报告', markdown_body)
        self.assertIn('## 审计概览', markdown_body)
        self.assertIn('Unsafe command execution', markdown_body)
        self.assertNotIn('{\n  "task"', markdown_body)

        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
        self.assertEqual(pdf_response.content, b'%PDF-test')
        self.assertEqual(compat_json_response['Content-Type'], 'application/json')
        self.assertEqual(compat_pdf_response['Content-Type'], 'application/pdf')
