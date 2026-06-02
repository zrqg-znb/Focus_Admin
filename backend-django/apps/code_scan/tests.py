from datetime import timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.code_scan.api import list_latest_results, list_project_overview
from apps.code_scan.models import (
    ScanFinding,
    ScanProject,
    ScanResult,
    ScanResultDetail,
    ScanResultOccurrence,
    ScanTask,
    ShieldApplication,
)
from apps.code_scan.services import ScanService
from core.user.user_model import User


class CodeScanApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = User.objects.create(
            username='code-scan-tester',
            password='secret',
            name='Code Scan Tester',
        )
        self.project = self._create_project(name='Focus Admin')

    def _create_project(self, *, name: str) -> ScanProject:
        return ScanProject.objects.create(
            name=name,
            repo_url=f'https://example.com/{name.lower().replace(" ", "-")}.git',
            branch='main',
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def _create_task(
        self,
        *,
        project: ScanProject | None = None,
        tool_name: str = 'tscan',
        status: str = 'success',
        sub_module: str = '',
        created_at=None,
    ) -> ScanTask:
        task = ScanTask.objects.create(
            project=project or self.project,
            tool_name=tool_name,
            status=status,
            source='manual',
            sub_module=sub_module,
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        if created_at is not None:
            ScanTask.objects.filter(id=task.id).update(
                sys_create_datetime=created_at,
                sys_update_datetime=created_at,
            )
            task.refresh_from_db()
        return task

    def _create_result(
        self,
        task: ScanTask,
        *,
        shield_status: str = 'Normal',
        index: int = 0,
        file_path: str | None = None,
        defect_type: str = 'NullPointer',
        severity: str = 'High',
        description: str | None = None,
    ) -> ScanResult:
        return ScanResult.objects.create(
            task=task,
            file_path=file_path or f'src/module_{index}.cpp',
            line_number=index + 1,
            defect_type=defect_type,
            severity=severity,
            description=description or f'defect-{shield_status}-{index}',
            fingerprint=f'fingerprint-{task.id}-{shield_status}-{index}',
            shield_status=shield_status,
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def _create_occurrence(
        self,
        task: ScanTask,
        *,
        shield_status: str = 'Normal',
        index: int = 0,
        file_path: str | None = None,
        defect_type: str = 'NullPointer',
        severity: str = 'High',
        description: str | None = None,
    ) -> ScanResultOccurrence:
        detail_payload = {
            'file_path': file_path or f'src/module_{index}.cpp',
            'defect_type': defect_type,
            'severity': severity,
            'description': description or f'defect-{shield_status}-{index}',
            'help_info': '',
            'code_snippet': '',
        }
        fingerprint = ScanService.build_fingerprint(
            {**detail_payload, 'line_number': index + 1}
        )
        finding, _ = ScanFinding.objects.get_or_create(
            project=task.project,
            fingerprint=fingerprint,
            defaults={
                'shield_status': shield_status,
                'first_seen_task': task,
                'last_seen_task': task,
                'first_seen_at': timezone.now(),
                'last_seen_at': timezone.now(),
            },
        )
        if finding.shield_status != shield_status:
            finding.shield_status = shield_status
            finding.save(update_fields=['shield_status', 'updated_at'])

        detail_hash = ScanService.build_detail_hash(detail_payload)
        detail, _ = ScanResultDetail.objects.get_or_create(
            content_hash=detail_hash,
            defaults=detail_payload,
        )
        return ScanResultOccurrence.objects.create(
            task=task,
            finding=finding,
            detail=detail,
            line_number=index + 1,
            shield_status=shield_status,
        )

    def test_latest_results_include_all_statuses_by_default(self):
        task = self._create_task(tool_name='tscan')
        statuses = ['Normal', 'Pending', 'Shielded', 'Rejected']
        for index, status in enumerate(statuses):
            self._create_result(task, shield_status=status, index=index)

        request = self.factory.get(f'/api/code-scan/projects/{self.project.id}/latest-results')

        payload = list_latest_results(request, self.project.id, tool_name='tscan')

        self.assertEqual(payload['total'], 4)
        self.assertEqual(
            {item['shield_status'] for item in payload['items']},
            set(statuses),
        )

    def test_latest_results_filter_by_shield_status(self):
        task = self._create_task(tool_name='valgrind', sub_module='engine')
        self._create_result(task, shield_status='Pending', index=1)
        self._create_result(task, shield_status='Shielded', index=2)

        request = self.factory.get(f'/api/code-scan/projects/{self.project.id}/latest-results')

        payload = list_latest_results(
            request,
            self.project.id,
            tool_name='valgrind',
            sub_modules='engine',
            shield_status='pending',
        )

        self.assertEqual(payload['total'], 1)
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(payload['items'][0]['shield_status'], 'Pending')

    def test_latest_results_filter_by_keywords(self):
        task = self._create_task(tool_name='tscan')
        target = self._create_result(
            task,
            index=1,
            severity='Medium',
            defect_type='MemoryLeak',
            file_path='src/network/connector.cpp',
            description='unsafe copy in parser',
        )
        self._create_result(
            task,
            index=2,
            severity='High',
            defect_type='NullPointer',
            file_path='src/core/service.cpp',
            description='null dereference in service',
        )
        self._create_result(
            task,
            index=3,
            severity='Low',
            defect_type='RaceCondition',
            file_path='src/thread/worker.cpp',
            description='race detected in worker',
        )

        request = self.factory.get(
            f'/api/code-scan/projects/{self.project.id}/latest-results'
        )

        severity_payload = list_latest_results(
            request,
            self.project.id,
            tool_name='tscan',
            severity_keyword='edi',
        )
        defect_type_payload = list_latest_results(
            request,
            self.project.id,
            tool_name='tscan',
            defect_type_keyword='leak',
        )
        file_path_payload = list_latest_results(
            request,
            self.project.id,
            tool_name='tscan',
            file_path_keyword='network/connector',
        )
        description_payload = list_latest_results(
            request,
            self.project.id,
            tool_name='tscan',
            description_keyword='unsafe copy',
        )

        for payload in (
            severity_payload,
            defect_type_payload,
            file_path_payload,
            description_payload,
        ):
            self.assertEqual(payload['total'], 1)
            self.assertEqual(len(payload['items']), 1)
            self.assertEqual(payload['items'][0]['id'], str(target.id))

    def test_latest_results_support_combined_filters(self):
        engine_task = self._create_task(tool_name='valgrind', sub_module='engine')
        braking_task = self._create_task(tool_name='valgrind', sub_module='braking')
        target = self._create_result(
            engine_task,
            shield_status='Pending',
            index=10,
            severity='High',
            defect_type='MemoryLeak',
            file_path='src/engine/network.cpp',
            description='network leak in parser',
        )
        self._create_result(
            engine_task,
            shield_status='Rejected',
            index=11,
            severity='High',
            defect_type='MemoryLeak',
            file_path='src/engine/network.cpp',
            description='network leak in parser',
        )
        self._create_result(
            braking_task,
            shield_status='Pending',
            index=12,
            severity='High',
            defect_type='MemoryLeak',
            file_path='src/brake/network.cpp',
            description='network leak in parser',
        )

        request = self.factory.get(
            f'/api/code-scan/projects/{self.project.id}/latest-results'
        )

        payload = list_latest_results(
            request,
            self.project.id,
            tool_name='valgrind',
            sub_modules='engine',
            shield_status='pending',
            severity_keyword='High',
            defect_type_keyword='Leak',
            file_path_keyword='src/engine',
            description_keyword='network',
        )

        self.assertEqual(payload['total'], 1)
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(payload['items'][0]['id'], str(target.id))

    def test_project_overview_counts_include_shielded_results(self):
        task = self._create_task(tool_name='tscan')
        self._create_result(task, shield_status='Normal', index=1)
        self._create_result(task, shield_status='Shielded', index=2)

        request = self.factory.get('/api/code-scan/projects/overview')

        payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            project_id=self.project.id,
        )

        self.assertEqual(payload['total'], 1)
        self.assertEqual(len(payload['items']), 1)
        overview = payload['items'][0]
        self.assertEqual(overview['project_id'], str(self.project.id))
        self.assertEqual(overview['total'], 2)
        self.assertEqual(overview['tool_counts']['tscan'], 2)

    def test_project_overview_supports_total_and_tool_sorting_with_missing_last(self):
        beta = self._create_project(name='Beta')
        gamma = self._create_project(name='Gamma')
        base_time = timezone.now().replace(microsecond=0)

        focus_task = self._create_task(
            project=self.project,
            tool_name='tscan',
            created_at=base_time + timedelta(hours=1),
        )
        beta_task = self._create_task(
            project=beta,
            tool_name='tscan',
            created_at=base_time + timedelta(hours=2),
        )

        for index in range(2):
            self._create_result(focus_task, index=index)
        for index in range(5):
            self._create_result(beta_task, index=index)

        request = self.factory.get('/api/code-scan/projects/overview')

        total_desc_payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            sort_field='total',
            sort_order='desc',
        )
        tscan_asc_payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            sort_field='tscan',
            sort_order='asc',
        )

        self.assertEqual(
            [item['project_name'] for item in total_desc_payload['items']],
            ['Beta', 'Focus Admin', 'Gamma'],
        )
        self.assertEqual(
            [item['project_name'] for item in tscan_asc_payload['items']],
            ['Focus Admin', 'Beta', 'Gamma'],
        )
        self.assertEqual(total_desc_payload['items'][-1]['project_name'], gamma.name)
        self.assertEqual(tscan_asc_payload['items'][-1]['project_name'], gamma.name)

    def test_project_overview_supports_latest_time_sorting_with_missing_last(self):
        beta = self._create_project(name='Beta')
        gamma = self._create_project(name='Gamma')
        base_time = timezone.now().replace(microsecond=0)

        focus_task = self._create_task(
            project=self.project,
            tool_name='tscan',
            created_at=base_time + timedelta(hours=1),
        )
        beta_task = self._create_task(
            project=beta,
            tool_name='tscan',
            created_at=base_time + timedelta(hours=3),
        )
        self._create_result(focus_task, index=1)
        self._create_result(beta_task, index=2)

        request = self.factory.get('/api/code-scan/projects/overview')

        latest_time_desc_payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            sort_field='latest_time',
            sort_order='desc',
        )
        latest_time_asc_payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            sort_field='latest_time',
            sort_order='asc',
        )

        self.assertEqual(
            [item['project_name'] for item in latest_time_desc_payload['items']],
            ['Beta', 'Focus Admin', 'Gamma'],
        )
        self.assertEqual(
            [item['project_name'] for item in latest_time_asc_payload['items']],
            ['Focus Admin', 'Beta', 'Gamma'],
        )
        self.assertEqual(
            latest_time_desc_payload['items'][-1]['project_name'],
            gamma.name,
        )
        self.assertEqual(
            latest_time_asc_payload['items'][-1]['project_name'],
            gamma.name,
        )

    def test_latest_results_reads_normalized_occurrences(self):
        task = self._create_task(tool_name='tscan')
        occurrence = self._create_occurrence(
            task,
            index=7,
            severity='Medium',
            defect_type='MemoryLeak',
            file_path='src/normalized.cpp',
            description='normalized leak',
        )

        request = self.factory.get(
            f'/api/code-scan/projects/{self.project.id}/latest-results'
        )

        payload = list_latest_results(request, self.project.id, tool_name='tscan')

        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['items'][0]['id'], str(occurrence.id))
        self.assertEqual(payload['items'][0]['file_path'], 'src/normalized.cpp')
        self.assertEqual(payload['items'][0]['description'], 'normalized leak')

    def test_project_overview_counts_normalized_occurrences(self):
        task = self._create_task(tool_name='tscan')
        self._create_occurrence(task, index=1)
        self._create_occurrence(task, index=2, shield_status='Shielded')

        request = self.factory.get('/api/code-scan/projects/overview')

        payload = list_project_overview(
            request,
            page=1,
            pageSize=20,
            project_id=self.project.id,
        )

        self.assertEqual(payload['items'][0]['total'], 2)
        self.assertEqual(payload['items'][0]['tool_counts']['tscan'], 2)

    def test_process_report_deduplicates_detail_and_finding(self):
        defect = {
            'file_path': 'src/shared.cpp',
            'line_number': 12,
            'defect_type': 'MemoryLeak',
            'severity': 'High',
            'description': 'same leak',
            'help_info': 'free it',
            'code_snippet': 'malloc();',
        }
        parser = type('Parser', (), {'parse': lambda self, path: [defect]})()
        first_task = self._create_task(tool_name='tscan', status='processing')
        second_task = self._create_task(tool_name='tscan', status='processing')

        with patch('apps.code_scan.services.ParserFactory.get_parser', return_value=parser):
            ScanService.process_report(first_task.id)
            ScanService.process_report(second_task.id)

        self.assertEqual(ScanResult.objects.count(), 0)
        self.assertEqual(ScanResultDetail.objects.count(), 1)
        self.assertEqual(ScanFinding.objects.count(), 1)
        self.assertEqual(ScanResultOccurrence.objects.count(), 2)

    def test_process_report_inherits_shielded_finding(self):
        defect = {
            'file_path': 'src/inherit.cpp',
            'line_number': 8,
            'defect_type': 'NullPointer',
            'severity': 'High',
            'description': 'same null',
        }
        parser = type('Parser', (), {'parse': lambda self, path: [defect]})()
        first_task = self._create_task(tool_name='tscan', status='processing')
        second_task = self._create_task(tool_name='tscan', status='processing')

        with patch('apps.code_scan.services.ParserFactory.get_parser', return_value=parser):
            ScanService.process_report(first_task.id)

        first_occurrence = ScanResultOccurrence.objects.get(task=first_task)
        first_occurrence.shield_status = 'Shielded'
        first_occurrence.save(update_fields=['shield_status', 'updated_at'])
        first_occurrence.finding.shield_status = 'Shielded'
        first_occurrence.finding.save(update_fields=['shield_status', 'updated_at'])

        with patch('apps.code_scan.services.ParserFactory.get_parser', return_value=parser):
            ScanService.process_report(second_task.id)

        second_occurrence = ScanResultOccurrence.objects.get(task=second_task)
        self.assertEqual(second_occurrence.shield_status, 'Shielded')

    def test_process_report_applies_path_prefix_shielding(self):
        self.project.path_shield_prefixes = ['third_party/']
        self.project.save(update_fields=['path_shield_prefixes', 'sys_update_datetime'])
        defect = {
            'file_path': 'third_party/vendor.cpp',
            'line_number': 8,
            'defect_type': 'Style',
            'severity': 'Low',
            'description': 'vendor issue',
        }
        parser = type('Parser', (), {'parse': lambda self, path: [defect]})()
        task = self._create_task(tool_name='tscan', status='processing')

        with patch('apps.code_scan.services.ParserFactory.get_parser', return_value=parser):
            ScanService.process_report(task.id)

        occurrence = ScanResultOccurrence.objects.get(task=task)
        self.assertEqual(occurrence.shield_status, 'Shielded')

    def test_apply_and_audit_shield_for_normalized_occurrence(self):
        task = self._create_task(tool_name='tscan')
        occurrence = self._create_occurrence(task)

        ScanService.apply_shield(
            self.user,
            [str(occurrence.id)],
            self.user.id,
            'false positive',
        )

        occurrence.refresh_from_db()
        app = ShieldApplication.objects.get(occurrence=occurrence)
        self.assertEqual(occurrence.shield_status, 'Pending')
        self.assertIsNone(app.result_id)

        processed = ScanService.audit_shield_batch(
            self.user,
            [app.id],
            'Approved',
            'ok',
        )

        occurrence.refresh_from_db()
        occurrence.finding.refresh_from_db()
        self.assertEqual(processed, 1)
        self.assertEqual(occurrence.shield_status, 'Shielded')
        self.assertEqual(occurrence.finding.shield_status, 'Shielded')
