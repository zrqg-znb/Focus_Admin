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
    RequirementBoardDataQuerySchema,
    RequirementBoardFilterPayloadSchema,
    RequirementBoardSummaryQuerySchema,
)
from core.pl.pl_model import PlGroup


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
                "title_keyword": " 登录 ",
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
        self.assertEqual(saved_filter["title_keyword"], "登录")
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
                requirement_id_keyword=" REQ- ",
                title_keyword=" 首帧 ",
                develop_user=[" dev-a ", "dev-a"],
                test_user=["tester"],
                time_field="",
                time_start="",
                time_end="",
                planned_test_time_start="2026-03-01",
                planned_test_time_end="2026-03-31",
                due_date_start="",
                due_date_end="",
                completed_time_start="",
                completed_time_end="",
                accepted_time_start="",
                accepted_time_end="",
                dev_delay_status="invalid",
                test_delay_status="delayed",
            ),
        )

        self.assertTrue(result)
        self.assertEqual(RequirementBoardFilterPreference.objects.count(), 1)
        preference = RequirementBoardFilterPreference.objects.get(user=self.user)
        self.assertEqual(preference.payload["project_ids"], [str(project.id)])
        self.assertEqual(preference.payload["categories"], list(CATEGORY_ORDER))
        self.assertEqual(preference.payload["title_keyword"], "首帧")
        self.assertEqual(preference.payload["requirement_id_keyword"], "REQ-")
        self.assertEqual(preference.payload["develop_user"], ["dev-a"])
        self.assertEqual(preference.payload["time_field"], DEFAULT_TIME_FIELD)
        self.assertEqual(preference.payload["planned_test_time_start"], "2026-03-01")
        self.assertEqual(preference.payload["planned_test_time_end"], "2026-03-31")
        self.assertEqual(preference.payload["dev_delay_status"], "all")
        self.assertEqual(preference.payload["test_delay_status"], "delayed")

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
        "apps.project_manager.requirement_board.requirement_board_services._start_requirement_board_query_task_thread"
    )
    def test_prepare_query_returns_ready_when_full_cache_covers_projects(
        self,
        mocked_start,
        mocked_get_setting,
    ):
        projects = [
            self._create_project(name=f"Project-{index}", code=f"cached-{index}")
            for index in range(1, 4)
        ]

        def _fake_get_setting(name, default=None):
            if name == "REQUIREMENT_BOARD_ASYNC_PROJECT_THRESHOLD":
                return 2
            return getattr(requirement_board_services.settings, name, default)

        mocked_get_setting.side_effect = _fake_get_setting
        cache.set(
            requirement_board_services._FULL_CACHE_KEY,
            {
                "project_ids": [str(project.id) for project in projects],
                "item_count": 0,
                "generated_at": "2026-03-01T00:00:00+08:00",
            },
            300,
        )

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
                responsible_pl_group_ids=["unknown"],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
        )

        self.assertEqual(result["mode"], "ready")
        self.assertIsNone(result["task"])
        self.assertEqual(RequirementBoardQueryTask.objects.count(), 0)
        mocked_start.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._get_setting"
    )
    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._start_requirement_board_query_task_thread"
    )
    def test_prepare_query_falls_back_async_when_full_cache_misses_project_scope(
        self,
        mocked_start,
        mocked_get_setting,
    ):
        cached_project = self._create_project(name="Cached", code="cached")
        missing_project = self._create_project(name="Missing", code="missing")

        def _fake_get_setting(name, default=None):
            if name == "REQUIREMENT_BOARD_ASYNC_PROJECT_THRESHOLD":
                return 1
            return getattr(requirement_board_services.settings, name, default)

        mocked_get_setting.side_effect = _fake_get_setting
        cache.set(
            requirement_board_services._FULL_CACHE_KEY,
            {
                "project_ids": [str(cached_project.id)],
                "item_count": 0,
                "generated_at": "2026-03-01T00:00:00+08:00",
            },
            300,
        )

        result = requirement_board_services.prepare_requirement_board_query(
            self.user,
            RequirementBoardFilterPayloadSchema(
                project_ids=[str(cached_project.id), str(missing_project.id)],
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
                "responsible_pl_group_id": None,
                "responsible_pl_group_name": "未识别PL领域",
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

    def _build_raw_requirement(
        self,
        *,
        design_id: str,
        requirement_id: str,
        team: str,
        category: str = "AR",
        status: str = "In-Progress",
        policy: str = "10000001",
        title: str = "Requirement",
        develop_owner: str = "dev-a",
        test_owner: str = "test-a",
        planned_test_time: str = "2026-03-05 10:00:00",
        due_date: str = "2026-03-10 18:00:00",
        completed_time: str | None = None,
        accepted_time: str | None = None,
    ) -> dict:
        return {
            "id": requirement_id,
            "title": title,
            "category": category,
            "schedule_state": status,
            "verification_policy": policy,
            "requirement2domain": design_id,
            "service_name": team,
            "planned_test_time": planned_test_time,
            "due_date": due_date,
            "completed_time": completed_time,
            "accepted_time": accepted_time,
            "workload_kloc": 1.2,
            "workload_man_day": 3.4,
            "develop_owner": develop_owner,
            "test_owner": test_owner,
        }

    def _build_raw_page(self, items: list[dict]) -> dict:
        return {
            "code": 200,
            "message": "success",
            "data": {
                "result": items,
                "page": {
                    "page_no": 1,
                    "page_size": 500,
                    "page_sum": len(items),
                    "total": len(items),
                },
            },
        }

    def _create_focus_user(self, username: str, name: str | None = None):
        return get_user_model().objects.create(
            username=username,
            name=name or username,
            password="secret",
        )

    def _create_pl_group(
        self,
        *,
        name: str,
        code: str,
        pl_user,
        members: list,
        sort: int = 0,
        status: bool = True,
    ) -> PlGroup:
        group = PlGroup.objects.create(
            name=name,
            code=code,
            pl_user=pl_user,
            sort=sort,
            status=status,
        )
        group.members.add(pl_user, *members)
        return group

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_refresh_full_cache_writes_configured_projects_only(self, mocked_fetch):
        project_a = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        project_b = self._create_project(
            name="Beta",
            code="beta",
            design_id="design-b",
            sub_teams=["Team-B"],
        )
        self._create_project(name="NoDesign", code="no-design", design_id="", sub_teams=["Team-C"])
        self._create_project(name="NoTeam", code="no-team", design_id="design-c", sub_teams=[])
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-A",
                    team="Team-A",
                ),
                self._build_raw_requirement(
                    design_id="design-b",
                    requirement_id="REQ-B",
                    team="Team-B",
                ),
            ]
        )

        result = requirement_board_services.refresh_requirement_board_full_cache()

        self.assertEqual(result["project_count"], 2)
        self.assertEqual(result["team_count"], 2)
        self.assertEqual(result["item_count"], 2)
        cached = cache.get(requirement_board_services._FULL_CACHE_KEY)
        self.assertEqual(
            set(cached["project_ids"]),
            {str(project_a.id), str(project_b.id)},
        )
        self.assertEqual(cached["item_count"], 2)
        project_a_cache = cache.get(
            requirement_board_services._full_cache_project_key(str(project_a.id))
        )
        project_b_cache = cache.get(
            requirement_board_services._full_cache_project_key(str(project_b.id))
        )
        self.assertEqual(len(project_a_cache["items"]), 1)
        self.assertEqual(len(project_b_cache["items"]), 1)

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_page_query_uses_full_cache_and_keeps_local_filters(self, mocked_fetch):
        project_a = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A", "Team-B"],
        )
        project_b = self._create_project(
            name="Beta",
            code="beta",
            design_id="design-b",
            sub_teams=["Team-C"],
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-1",
                    team="Team-A",
                    status="In-Progress",
                    title="缓存命中需求",
                    develop_owner="dev-a",
                    planned_test_time="2026-03-05 10:00:00",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-2",
                    team="Team-B",
                    status="Accepted",
                    title="团队不匹配",
                    develop_owner="dev-a",
                    planned_test_time="2026-03-05 10:00:00",
                    accepted_time="2026-03-09 18:00:00",
                ),
                self._build_raw_requirement(
                    design_id="design-b",
                    requirement_id="REQ-3",
                    team="Team-C",
                    status="In-Progress",
                    title="项目不匹配",
                    develop_owner="dev-b",
                    planned_test_time="2026-03-05 10:00:00",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()

        result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project_a.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=["P"],
                verification_policies=[],
                title_keyword="缓存",
                develop_user=["dev-a"],
                test_user=[],
                time_field="planned_test_time",
                time_start="2026-03-01",
                time_end="2026-03-31",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["requirement_id"], "REQ-1")
        mocked_fetch.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_full_cache_filters_requirement_id_time_ranges_and_delay(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-KEEP",
                    team="Team-A",
                    title="目标需求",
                    planned_test_time="2026-03-05 10:00:00",
                    due_date="2026-03-10 18:00:00",
                    completed_time="2026-03-08 18:00:00",
                    accepted_time="2026-03-12 18:00:00",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-DROP-ID",
                    team="Team-A",
                    title="目标需求",
                    planned_test_time="2026-03-05 10:00:00",
                    due_date="2026-03-10 18:00:00",
                    completed_time="2026-03-08 18:00:00",
                    accepted_time="2026-03-12 18:00:00",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-KEEP-LATE",
                    team="Team-A",
                    title="目标需求",
                    planned_test_time="2026-04-05 10:00:00",
                    due_date="2026-04-10 18:00:00",
                    completed_time="2026-04-08 18:00:00",
                    accepted_time="2026-04-12 18:00:00",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()

        result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                requirement_id_keyword="KEEP",
                title_keyword="目标",
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
                planned_test_time_start="2026-03-01",
                planned_test_time_end="2026-03-31",
                due_date_start="2026-03-01",
                due_date_end="2026-03-31",
                completed_time_start="2026-03-07",
                completed_time_end="2026-03-09",
                accepted_time_start="2026-03-11",
                accepted_time_end="2026-03-13",
                dev_delay_status="delayed",
                test_delay_status="delayed",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["requirement_id"], "REQ-KEEP")
        mocked_fetch.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_full_cache_filtered_result_is_reused_by_page_and_summary(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-1",
                    team="Team-A",
                    status="In-Progress",
                    develop_owner="dev-a",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-2",
                    team="Team-A",
                    status="Accepted",
                    develop_owner="dev-b",
                    accepted_time="2026-03-09 18:00:00",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()
        query = RequirementBoardDataQuerySchema(
            project_ids=[str(project.id)],
            sub_teams=["Team-A"],
            categories=["AR"],
            schedule_state=["P"],
            verification_policies=[],
            develop_user=[],
            test_user=[],
            time_field="accepted_time",
            time_start="",
            time_end="",
            page_no=1,
            page_size=1,
        )

        first_result = requirement_board_services.get_requirement_board_page(
            query,
            user=self.user,
        )

        self.assertEqual(first_result["total"], 1)
        with mock.patch(
            "apps.project_manager.requirement_board.requirement_board_services._load_full_cache_candidate_items",
            wraps=requirement_board_services._load_full_cache_candidate_items,
        ) as mocked_load_candidates:
            second_result = requirement_board_services.get_requirement_board_page(
                query,
                user=self.user,
            )
            summary = requirement_board_services.get_requirement_board_summary(
                RequirementBoardSummaryQuerySchema(
                    project_ids=[str(project.id)],
                    sub_teams=["Team-A"],
                    categories=["AR"],
                    schedule_state=["P"],
                    verification_policies=[],
                    develop_user=[],
                    test_user=[],
                    time_field="accepted_time",
                    time_start="",
                    time_end="",
                ),
                user=self.user,
            )

        self.assertEqual(second_result["total"], 1)
        self.assertEqual(summary["total_count"], 1)
        mocked_load_candidates.assert_not_called()
        mocked_fetch.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_summary_query_uses_full_cache(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-1",
                    team="Team-A",
                    status="In-Progress",
                    develop_owner="dev-a",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-2",
                    team="Team-A",
                    status="Accepted",
                    develop_owner="dev-b",
                    accepted_time="2026-03-09 18:00:00",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()

        result = requirement_board_services.get_requirement_board_summary(
            RequirementBoardSummaryQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=["P"],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
            user=self.user,
        )

        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["team_summary"][0]["team_name"], "Team-A")
        self.assertEqual(result["team_summary"][0]["p_count"], 1)
        self.assertEqual(result["pl_group_summary"][0]["pl_group_name"], "未识别PL领域")
        self.assertEqual(result["pl_group_summary"][0]["p_count"], 1)
        mocked_fetch.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_summary_full_cache_returns_team_and_pl_group_dimensions(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A", "Team-B"],
        )
        dev_known = self._create_focus_user("dev-known")
        group = self._create_pl_group(
            name="平台PL",
            code="pl-platform",
            pl_user=dev_known,
            members=[dev_known],
            sort=1,
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-KNOWN",
                    team="Team-A",
                    status="Completed",
                    develop_owner="dev-known",
                    completed_time="2026-03-08 18:00:00",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-UNKNOWN",
                    team="Team-B",
                    status="Accepted",
                    develop_owner="dev-missing",
                    accepted_time="2026-03-09 18:00:00",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()

        result = requirement_board_services.get_requirement_board_summary(
            RequirementBoardSummaryQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A", "Team-B"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
            ),
            user=self.user,
        )

        self.assertEqual(result["total_count"], 2)
        self.assertEqual(
            {item["team_name"]: item["total_count"] for item in result["team_summary"]},
            {"Team-A": 1, "Team-B": 1},
        )
        pl_rows = {
            item["pl_group_name"]: item for item in result["pl_group_summary"]
        }
        self.assertEqual(pl_rows["平台PL"]["pl_group_id"], str(group.id))
        self.assertEqual(pl_rows["平台PL"]["c_count"], 1)
        self.assertIsNone(pl_rows["未识别PL领域"]["pl_group_id"])
        self.assertEqual(pl_rows["未识别PL领域"]["a_count"], 1)
        mocked_fetch.assert_not_called()

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_responsible_pl_group_maps_first_develop_owner_only(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        dev_first = self._create_focus_user("dev-first")
        dev_second = self._create_focus_user("dev-second")
        first_low = self._create_pl_group(
            name="低优先PL",
            code="pl-low",
            pl_user=dev_first,
            members=[dev_first],
            sort=1,
        )
        first_high = self._create_pl_group(
            name="高优先PL",
            code="pl-high",
            pl_user=dev_first,
            members=[dev_first],
            sort=9,
        )
        self._create_pl_group(
            name="第二责任人PL",
            code="pl-second",
            pl_user=dev_second,
            members=[dev_second],
            sort=99,
        )
        self._create_pl_group(
            name="禁用PL",
            code="pl-disabled",
            pl_user=dev_first,
            members=[dev_first],
            sort=100,
            status=False,
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-PL",
                    team="Team-A",
                    develop_owner="dev-first,dev-second",
                ),
            ]
        )

        result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=[],
                time_field="accepted_time",
                time_start="",
                time_end="",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )

        row = result["items"][0]
        self.assertEqual(row["responsible_pl_group_id"], str(first_high.id))
        self.assertEqual(row["responsible_pl_group_name"], "高优先PL")
        self.assertNotEqual(row["responsible_pl_group_id"], str(first_low.id))

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_responsible_pl_group_filter_supports_real_and_unknown(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        dev_known = self._create_focus_user("dev-known")
        group = self._create_pl_group(
            name="已识别PL",
            code="pl-known",
            pl_user=dev_known,
            members=[dev_known],
            sort=1,
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-KNOWN",
                    team="Team-A",
                    develop_owner="dev-known",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-UNKNOWN",
                    team="Team-A",
                    develop_owner="dev-missing",
                ),
            ]
        )

        known_result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=[str(group.id)],
                time_field="accepted_time",
                time_start="",
                time_end="",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )
        self.assertEqual(known_result["total"], 1)
        self.assertEqual(known_result["items"][0]["requirement_id"], "REQ-KNOWN")

        unknown_result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=["unknown"],
                time_field="accepted_time",
                time_start="",
                time_end="",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )
        self.assertEqual(unknown_result["total"], 1)
        self.assertEqual(unknown_result["items"][0]["requirement_id"], "REQ-UNKNOWN")
        self.assertEqual(
            unknown_result["items"][0]["responsible_pl_group_name"],
            "未识别PL领域",
        )

    @mock.patch(
        "apps.project_manager.requirement_board.requirement_board_services._fetch_raw_page"
    )
    def test_full_cache_can_filter_responsible_pl_group(self, mocked_fetch):
        project = self._create_project(
            name="Alpha",
            code="alpha",
            design_id="design-a",
            sub_teams=["Team-A"],
        )
        dev_known = self._create_focus_user("dev-known")
        group = self._create_pl_group(
            name="缓存PL",
            code="pl-cache",
            pl_user=dev_known,
            members=[dev_known],
            sort=1,
        )
        mocked_fetch.return_value = self._build_raw_page(
            [
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-CACHE-KNOWN",
                    team="Team-A",
                    develop_owner="dev-known",
                ),
                self._build_raw_requirement(
                    design_id="design-a",
                    requirement_id="REQ-CACHE-UNKNOWN",
                    team="Team-A",
                    develop_owner="dev-missing",
                ),
            ]
        )
        requirement_board_services.refresh_requirement_board_full_cache()
        mocked_fetch.reset_mock()

        result = requirement_board_services.get_requirement_board_page(
            RequirementBoardDataQuerySchema(
                project_ids=[str(project.id)],
                sub_teams=["Team-A"],
                categories=["AR"],
                schedule_state=[],
                verification_policies=[],
                develop_user=[],
                test_user=[],
                responsible_pl_group_ids=[str(group.id)],
                time_field="accepted_time",
                time_start="",
                time_end="",
                page_no=1,
                page_size=20,
            ),
            user=self.user,
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["requirement_id"], "REQ-CACHE-KNOWN")
        mocked_fetch.assert_not_called()
