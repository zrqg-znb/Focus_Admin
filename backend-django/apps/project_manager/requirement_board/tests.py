from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase
from unittest import mock

from apps.project_manager.project.project_model import Project
from apps.project_manager.requirement_board import requirement_board_services
from apps.project_manager.requirement_board.requirement_board_model import (
    CATEGORY_ORDER,
    DEFAULT_TIME_FIELD,
    RequirementBoardFilterPreference,
    RequirementBoardQueryTask,
)
from apps.project_manager.requirement_board.requirement_board_schemas import (
    RequirementBoardFilterPayloadSchema,
)


class RequirementBoardPreferenceTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create(
            username="tester",
            password="secret",
        )

    def _create_project(
        self,
        *,
        name: str,
        code: str,
        design_id: str | None = None,
        sub_teams: list[str] | None = None,
    ) -> Project:
        return Project.objects.create(
            name=name,
            domain="车控",
            type="量产",
            code=code,
            design_id=design_id if design_id is not None else f"design-{code}",
            sub_teams=sub_teams if sub_teams is not None else ["Team-A"],
        )

    def test_get_filter_options_returns_favorite_flags_and_clean_saved_filter(self):
        favorite_project = self._create_project(name="Alpha", code="alpha")
        normal_project = self._create_project(name="Beta", code="beta")
        invalid_project = self._create_project(
            name="Gamma",
            code="gamma",
            design_id="",
            sub_teams=[],
        )
        favorite_project.favorited_by.add(self.user)
        invalid_project.favorited_by.add(self.user)

        RequirementBoardFilterPreference.objects.create(
            user=self.user,
            payload={
                "project_ids": [str(favorite_project.id), str(invalid_project.id), "missing"],
                "sub_teams": ["Team-A", "Team-X"],
                "categories": [],
                "schedule_state": ["P", "INVALID"],
                "verification_policies": ["10000001", "unknown"],
                "develop_user": ["dev-a"],
                "test_user": ["test-a"],
                "time_field": "invalid_field",
                "time_start": "bad-date",
                "time_end": "2026-03-20",
            },
            last_applied_at=requirement_board_services.timezone.now(),
        )

        result = requirement_board_services.get_filter_options(self.user)

        projects = {item["id"]: item for item in result["projects"]}
        self.assertTrue(projects[str(favorite_project.id)]["is_favorited"])
        self.assertFalse(projects[str(normal_project.id)]["is_favorited"])
        self.assertTrue(projects[str(invalid_project.id)]["is_favorited"])

        saved_filter = result["saved_filter"]
        self.assertEqual(saved_filter["project_ids"], [str(favorite_project.id)])
        self.assertEqual(saved_filter["sub_teams"], ["Team-A"])
        self.assertEqual(saved_filter["categories"], list(CATEGORY_ORDER))
        self.assertEqual(saved_filter["schedule_state"], ["P"])
        self.assertEqual(saved_filter["verification_policies"], ["10000001"])
        self.assertEqual(saved_filter["time_field"], DEFAULT_TIME_FIELD)
        self.assertEqual(saved_filter["time_start"], "")
        self.assertEqual(saved_filter["time_end"], "2026-03-20")

    def test_save_filter_preference_upserts_normalized_payload(self):
        project = self._create_project(name="Alpha", code="alpha")

        result = requirement_board_services.save_filter_preference(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(project.id), str(project.id)],
                sub_teams=["Team-A"],
                categories=[],
                schedule_state=["P"],
                verification_policies=["10000001"],
                develop_user=[" dev-a ", "dev-a"],
                test_user=["tester"],
                time_field="",
                time_start="",
                time_end="",
            ),
        )

        self.assertTrue(result)
        self.assertEqual(RequirementBoardFilterPreference.objects.count(), 1)
        preference = RequirementBoardFilterPreference.objects.get(user=self.user)
        self.assertEqual(preference.payload["project_ids"], [str(project.id)])
        self.assertEqual(preference.payload["categories"], list(CATEGORY_ORDER))
        self.assertEqual(preference.payload["develop_user"], ["dev-a"])
        self.assertEqual(preference.payload["time_field"], DEFAULT_TIME_FIELD)

        requirement_board_services.save_filter_preference(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(project.id)],
                sub_teams=[],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                time_field="accepted_time",
                time_start="2026-03-01",
                time_end="2026-03-31",
            ),
        )

        self.assertEqual(RequirementBoardFilterPreference.objects.count(), 1)
        preference.refresh_from_db()
        self.assertEqual(preference.payload["categories"], ["AR"])
        self.assertEqual(preference.payload["sub_teams"], [])
        self.assertEqual(preference.payload["time_start"], "2026-03-01")

    def test_delete_filter_preference_clears_saved_filter(self):
        project = self._create_project(name="Alpha", code="alpha")
        requirement_board_services.save_filter_preference(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(project.id)],
                sub_teams=[],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
        )

        deleted = requirement_board_services.delete_filter_preference(self.user)

        self.assertTrue(deleted)
        preference = RequirementBoardFilterPreference.objects.get(user=self.user)
        self.assertTrue(preference.is_deleted)
        result = requirement_board_services.get_filter_options(self.user)
        self.assertIsNone(result["saved_filter"])

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._start_requirement_board_query_task_thread"
    )
    def test_prepare_query_returns_ready_for_small_remote_query(self, mocked_start):
        project = self._create_project(name="Alpha", code="alpha")

        result = requirement_board_services.prepare_requirement_board_query(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
        )

        self.assertEqual(result["mode"], "ready")
        self.assertIsNone(result["task"])
        mocked_start.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._get_setting"
    )
    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._start_requirement_board_query_task_thread"
    )
    def test_prepare_query_creates_async_task_for_large_or_local_filter(
        self,
        mocked_start,
        mocked_get_setting,
    ):
        projects = [
            self._create_project(name=f"Project-{index}", code=f"code-{index}")
            for index in range(1, 4)
        ]

        def _fake_get_setting(name, default=None):
            if name == "REQUIREMENT_BOARD_ASYNC_PROJECT_THRESHOLD":
                return 2
            return getattr(requirement_board_services.settings, name, default)

        mocked_get_setting.side_effect = _fake_get_setting
        result = requirement_board_services.prepare_requirement_board_query(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(project.id) for project in projects],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
        )

        self.assertEqual(result["mode"], "async")
        self.assertEqual(RequirementBoardQueryTask.objects.count(), 1)
        task = RequirementBoardQueryTask.objects.get(user=self.user)
        self.assertEqual(task.status, RequirementBoardQueryTask.STATUS_PENDING)
        mocked_start.assert_called_once()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._get_setting"
    )
    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._collect_prepared_items_for_task"
    )
    def test_query_task_runner_caches_prepared_items(self, mocked_collect, mocked_get_setting):
        project = self._create_project(name="Alpha", code="alpha")
        payload = RequirementBoardFilterPayloadSchema(
            project_ids=[str(project.id)],
            sub_teams=["Team-A"],
            categories=["AR"],
            schedule_state=[],
            verification_policies=[],
            develop_user=["dev-a"],
            test_user=[],
            time_field="accepted_time",
            time_start="",
            time_end="",
        )

        def _fake_get_setting(name, default=None):
            if name == "REQUIREMENT_BOARD_ASYNC_PROJECT_THRESHOLD":
                return 20
            return getattr(requirement_board_services.settings, name, default)

        mocked_get_setting.side_effect = _fake_get_setting
        normalized_payload = requirement_board_services._normalize_filter_payload_for_storage(payload)
        task = RequirementBoardQueryTask.objects.create(
            user=self.user,
            sys_creator=self.user,
            fingerprint="fingerprint-1",
            payload=normalized_payload,
            status=RequirementBoardQueryTask.STATUS_PENDING,
            message="submitted",
        )
        mocked_collect.return_value = [
            {
                "requirement_id": "REQ-1",
                "project_id": str(project.id),
                "project_name": project.name,
                "team_name": "Team-A",
                "title": "Requirement 1",
                "category": "AR",
                "verification_policy": "",
                "verification_policy_label": "",
                "status_code": "P",
                "status_label": "开发中",
                "raw_status": "",
                "planned_test_time": None,
                "due_date": None,
                "completed_time": None,
                "accepted_time": None,
                "is_dev_delayed": False,
                "is_test_delayed": False,
                "workload_kloc": 0.0,
                "workload_man_day": 0.0,
                "develop_users": ["dev-a"],
                "test_users": [],
                "develop_user_display": "dev-a",
                "test_user_display": "",
                "develop_user": "dev-a",
                "test_user": "",
            }
        ]

        requirement_board_services._run_requirement_board_query_task(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, RequirementBoardQueryTask.STATUS_SUCCESS)
        self.assertTrue(task.result_cache_key)
        cached = requirement_board_services.cache.get(task.result_cache_key)
        self.assertEqual(len(cached["items"]), 1)
