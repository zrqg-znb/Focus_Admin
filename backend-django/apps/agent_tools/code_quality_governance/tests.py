from django.test import TestCase

from core.user.user_model import User

from .models import GovernanceFinding, GovernanceFindingOccurrence, GovernanceProject, GovernanceProjectResponsibility, GovernanceResponsibility, GovernanceShieldAuditLog
from .parsers import parse_report
from .schemas import ShieldApplicationIn
from .services import audit_application, create_application, ingest_report


class CodeQualityGovernanceTests(TestCase):
    """验证独立代码问题治理的解析、归并和审核流程。"""

    def setUp(self):
        self.user = User.objects.create(username='governance-user', password='secret', name='治理用户')
        self.approver = User.objects.create(username='governance-approver', password='secret', name='审批用户')
        project = GovernanceProject.objects.create(name='演示项目', code='demo', sys_creator=self.user, sys_modifier=self.user)
        responsibility = GovernanceResponsibility.objects.create(name='底层驱动', code='driver', sys_creator=self.user, sys_modifier=self.user)
        responsibility.approvers.add(self.approver)
        self.scope = GovernanceProjectResponsibility.objects.create(project=project, responsibility=responsibility, sys_creator=self.user, sys_modifier=self.user)

    def payload(self, issue_key='sha256:issue-1', complete='false'):
        """构造含 identity、证据和五级严重度的第三方报告。"""
        return {'repository': '/usr/example/project', 'complete': complete, 'summary': {'file_scanned': 1, 'critical': 1}, 'created_at': '2026-08-28T09:27:45Z', 'findings': [{'fingerprint': 'sha256:legacy', 'rule_id': 'mcu,nvm.NUM-001', 'rule_version': '1.0.0', 'severity': 'critical', 'confidence': 0.72, 'location': {'path': 'bad_driver.c', 'start_line': 3, 'end_line': 3}, 'message': '敏感数值计算缺少可见的溢出或范围检查', 'evidence': [{'path': 'bad_driver.c', 'start_line': 3}], 'identity': {'version': 2, 'category': 'numeric_overflow', 'issue_key': issue_key, 'anchor_hash': 'sha256:anchor'}, 'legacy_fingerprints': ['sha256:legacy']}]}

    def test_parser_preserves_incomplete_flag_and_severity(self):
        """complete=false 仍被解析，严重度按五级保留。"""
        parsed = parse_report(self.payload())
        self.assertFalse(parsed.complete)
        self.assertEqual(parsed.findings[0].severity, 'critical')

    def test_ingest_merges_same_issue_across_reports(self):
        """相同 issue_key 在多次扫描中只产生一条稳定问题。"""
        ingest_report(self.user, str(self.scope.project_id), str(self.scope.responsibility_id), 'third-party', self.payload())
        ingest_report(self.user, str(self.scope.project_id), str(self.scope.responsibility_id), 'third-party', self.payload())
        self.assertEqual(GovernanceFinding.objects.count(), 1)
        self.assertEqual(GovernanceFindingOccurrence.objects.count(), 2)

    def test_shield_application_and_approval(self):
        """申请、审批和审计日志状态保持一致。"""
        ingest_report(self.user, str(self.scope.project_id), str(self.scope.responsibility_id), 'third-party', self.payload())
        finding = GovernanceFinding.objects.get()
        request = ShieldApplicationIn(finding_ids=[str(finding.id)], approver_id=str(self.approver.id), reason='误报')
        application = create_application(self.user, request)[0]
        self.assertEqual(application['status'], 'Pending')
        result = audit_application(self.approver, application['id'], 'Approved', '确认屏蔽')
        self.assertEqual(result['status'], 'Approved')
        finding.refresh_from_db()
        self.assertEqual(finding.shield_status, 'Shielded')
        self.assertEqual(GovernanceShieldAuditLog.objects.count(), 2)
