from types import SimpleNamespace
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from ninja.errors import HttpError

from apps.project_manager.project.project_model import Project
from apps.project_manager.requirement_workspace.requirement_workspace_model import (
    RequirementWorkspaceSnapshot,
)
from apps.project_manager.requirement_workspace import requirement_workspace_services


class RequirementWorkspaceServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    def _make_item(self, **overrides):
        data = {
            "project_id": "project-alpha",
            "project_name": "Alpha",
            "team_name": "Team-A",
            "requirement_id": "REQ-1",
            "title": "Requirement 1",
            "status_code": "P",
            "status_label": "开发中",
            "planned_test_time": None,
            "due_date": "2026-03-28 00:00:00",
            "completed_time": None,
            "accepted_time": None,
            "has_planned_test_time": False,
            "has_due_date": True,
            "has_develop_users": False,
            "has_test_users": True,
            "has_workload_man_day": False,
            "has_workload_kloc": False,
            "develop_user_display": "",
            "test_user_display": "tester",
            "is_dev_delayed": False,
            "is_test_delayed": False,
        }
        data.update(overrides)
        return data

    def test_build_snapshot_payload_uses_field_specific_denominators(self):
        projects = [
            SimpleNamespace(id="project-alpha", name="Alpha"),
            SimpleNamespace(id="project-beta", name="Beta"),
        ]
        items = [
            self._make_item(is_dev_delayed=True),
            self._make_item(
                project_id="project-alpha",
                project_name="Alpha",
                requirement_id="REQ-2",
                title="Requirement 2",
                status_code="C",
                status_label="已开发完成（转测）",
                planned_test_time="2026-03-18 00:00:00",
                due_date="2026-03-29 00:00:00",
                completed_time="2026-03-18 10:00:00",
                has_planned_test_time=True,
                has_due_date=True,
                has_develop_users=True,
                has_test_users=False,
                has_workload_man_day=True,
                has_workload_kloc=False,
                develop_user_display="dev-a",
                is_test_delayed=True,
            ),
            self._make_item(
                project_id="project-beta",
                project_name="Beta",
                team_name="Team-B",
                requirement_id="REQ-3",
                title="Requirement 3",
                status_code="A",
                status_label="测试完成（已置A）",
                planned_test_time="2026-03-20 00:00:00",
                due_date=None,
                completed_time="2026-03-20 08:00:00",
                accepted_time="2026-03-21 08:00:00",
                has_planned_test_time=True,
                has_due_date=False,
                has_develop_users=True,
                has_test_users=True,
                has_workload_man_day=True,
                has_workload_kloc=True,
                develop_user_display="dev-b",
                test_user_display="tester-b",
                is_dev_delayed=False,
                is_test_delayed=False,
            ),
        ]

        payload = requirement_workspace_services.build_requirement_workspace_snapshot_payload(
            projects,
            items,
            scope=requirement_workspace_services.DEFAULT_SCOPE,
            generated_at=timezone.now(),
        )

        field_map = {
            item["field_key"]: item
            for item in payload["field_overview"]
        }
        self.assertEqual(field_map["planned_test_time"]["applicable_count"], 3)
        self.assertEqual(field_map["planned_test_time"]["filled_count"], 2)
        self.assertEqual(field_map["develop_users"]["missing_count"], 1)
        self.assertEqual(field_map["workload_man_day"]["applicable_count"], 2)
        self.assertEqual(field_map["workload_man_day"]["filled_count"], 2)
        self.assertEqual(field_map["workload_kloc"]["missing_count"], 1)

        project_rows = payload["project_rows"]
        self.assertEqual(project_rows[0]["project_name"], "Beta")
        self.assertEqual(project_rows[0]["completion_score"], 0.8333)
        self.assertEqual(project_rows[1]["project_name"], "Alpha")
        self.assertEqual(project_rows[1]["delay"]["development_count"], 1)
        self.assertEqual(project_rows[1]["delay"]["acceptance_count"], 1)
        self.assertEqual(
            len(payload["missing_previews"]["planned_test_time"]),
            1,
        )
        self.assertEqual(len(payload["delay_previews"]["development"]), 1)

    def test_get_latest_returns_empty_payload_before_first_snapshot(self):
        Project.objects.create(
            name="Alpha",
            domain="车控",
            type="量产",
            code="alpha-empty",
            design_id="design-alpha",
            sub_teams=["Team-A"],
        )

        payload = requirement_workspace_services.get_latest_requirement_workspace_snapshot()
        self.assertIsNone(payload["generated_at"])
        self.assertEqual(payload["project_count"], 1)
        self.assertEqual(payload["project_rows"], [])

    @mock.patch(
        "apps.project_manager.requirement_workspace.requirement_workspace_services.requirement_board_services.scan_standardized_requirement_items"
    )
    def test_refresh_snapshot_upserts_same_day_record(self, mocked_scan):
        project = Project.objects.create(
            name="Alpha",
            domain="车控",
            type="量产",
            code="alpha-refresh",
            design_id="design-alpha",
            sub_teams=["Team-A"],
        )
        mocked_scan.return_value = [
            self._make_item(
                project_id=str(project.id),
                project_name=project.name,
                requirement_id="REQ-1",
                title="Requirement 1",
            )
        ]

        first = requirement_workspace_services.refresh_requirement_workspace_snapshot()
        self.assertEqual(first["project_count"], 1)
        self.assertEqual(RequirementWorkspaceSnapshot.objects.count(), 1)

        mocked_scan.return_value = [
            self._make_item(
                project_id=str(project.id),
                project_name=project.name,
                requirement_id="REQ-2",
                title="Requirement 2",
                has_planned_test_time=True,
                planned_test_time="2026-03-20 00:00:00",
            )
        ]
        second = requirement_workspace_services.refresh_requirement_workspace_snapshot()

        self.assertEqual(RequirementWorkspaceSnapshot.objects.count(), 1)
        snapshot = RequirementWorkspaceSnapshot.objects.get()
        self.assertEqual(snapshot.requirement_count, 1)
        self.assertEqual(second["project_rows"][0]["total_count"], 1)
        self.assertEqual(
            second["missing_previews"]["planned_test_time"],
            [],
        )

    def test_refresh_snapshot_raises_when_generation_lock_exists(self):
        today = timezone.now().date().isoformat()
        lock_key = (
            f"pm:requirement-workspace:snapshot:{requirement_workspace_services.DEFAULT_SCOPE}:{today}:lock"
        )
        cache.add(lock_key, "1", 60)

        with self.assertRaises(HttpError):
            requirement_workspace_services.refresh_requirement_workspace_snapshot()
