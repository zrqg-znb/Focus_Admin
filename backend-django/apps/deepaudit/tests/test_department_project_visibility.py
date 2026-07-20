from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from ninja.errors import HttpError

from apps.deepaudit.permissions import get_project_access, require_project_role
from apps.deepaudit.project.project_model import AuditProject


class DepartmentProjectVisibilityTestCase(SimpleTestCase):
    def _project(self):
        members = Mock()
        members.filter.return_value.order_by.return_value.first.return_value = None
        project = Mock(spec=AuditProject)
        project.id = 'project-1'
        project.owner_id = 'owner-1'
        project.is_deleted = False
        project.members = members
        return project

    def test_non_member_receives_platform_viewer_access_for_active_project(self) -> None:
        access = get_project_access(SimpleNamespace(id='reader-1'), self._project())

        self.assertEqual(access.role, 'viewer')
        self.assertFalse(access.can_manage_project)

    def test_platform_viewer_cannot_run_or_modify_project_resources(self) -> None:
        with self.assertRaises(HttpError) as raised:
            require_project_role(
                SimpleNamespace(id='reader-1'),
                self._project(),
                min_role='member',
            )

        self.assertEqual(raised.exception.status_code, 403)
