from django.test import RequestFactory, TestCase

from apps.code_scan.api import list_latest_results, list_project_overview
from apps.code_scan.models import ScanProject, ScanResult, ScanTask
from core.user.user_model import User


class CodeScanApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = User.objects.create(
            username='code-scan-tester',
            password='secret',
            name='Code Scan Tester',
        )
        self.project = ScanProject.objects.create(
            name='Focus Admin',
            repo_url='https://example.com/focus-admin.git',
            branch='main',
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def _create_task(
        self,
        *,
        tool_name: str = 'tscan',
        status: str = 'success',
        sub_module: str = '',
    ) -> ScanTask:
        return ScanTask.objects.create(
            project=self.project,
            tool_name=tool_name,
            status=status,
            source='manual',
            sub_module=sub_module,
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def _create_result(
        self,
        task: ScanTask,
        *,
        shield_status: str,
        index: int,
    ) -> ScanResult:
        return ScanResult.objects.create(
            task=task,
            file_path=f'src/module_{index}.cpp',
            line_number=index + 1,
            defect_type='NullPointer',
            severity='High',
            description=f'defect-{shield_status}-{index}',
            fingerprint=f'fingerprint-{task.id}-{shield_status}-{index}',
            shield_status=shield_status,
            sys_creator=self.user,
            sys_modifier=self.user,
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
