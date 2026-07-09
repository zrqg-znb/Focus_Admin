from types import SimpleNamespace
import importlib

from django.test import RequestFactory, TestCase
from ninja.errors import HttpError

from core.user.user_model import User

from apps.project_manager.project import project_service
from apps.project_manager.hardware.hardware_model import CdcPlatform, IdvpPlatform
from apps.project_manager.project.project_model import Project, ProjectReleasePlan
from apps.project_manager.project.project_schema import (
    ProjectCreateSchema,
    ProjectOut,
    ProjectUpdateSchema,
)
from apps.project_manager.release_plan.release_plan_schema import ReleasePlanFilterSchema
from apps.project_manager.release_plan import release_plan_service


class ProjectVehicleOptionalFieldsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(
            username="project-tester",
            password="secret",
            name="Project Tester",
        )
        self.request = SimpleNamespace(auth=self.user)

    def test_create_vehicle_project_persists_optional_link_rows(self):
        payload = ProjectCreateSchema(
            name="Vehicle Project",
            domain="车控域",
            type="量产",
            code="vehicle-project",
            manager_ids=[str(self.user.id)],
            enable_milestone=False,
            enable_iteration=False,
            enable_quality=False,
            enable_dts=False,
            power_info_link=[
                {"chip_name": "VIU-1", "url": "https://example.com/power-1"},
                {"chip_name": "VIU-2", "url": "https://example.com/power-2"},
            ],
            hardware_software_interface_doc=[
                {
                    "chip_name": "VIU-1",
                    "url": "https://example.com/interface-1",
                },
            ],
        )

        project = project_service.create_project(self.request, payload)
        detail_request = self.factory.get(f"/api/project-manager/projects/{project.id}")
        detail_request.auth = self.user
        detail = project_service.get_project(detail_request, project.id)

        self.assertEqual(
            detail.power_info_link,
            [
                {"chip_name": "VIU-1", "url": "https://example.com/power-1"},
                {"chip_name": "VIU-2", "url": "https://example.com/power-2"},
            ],
        )
        self.assertEqual(
            detail.hardware_software_interface_doc,
            [{"chip_name": "VIU-1", "url": "https://example.com/interface-1"}],
        )
        self.assertEqual(
            list(detail.managers.values_list("id", flat=True)),
            [str(self.user.id)],
        )

    def test_create_and_update_allow_omitting_optional_fields(self):
        project = project_service.create_project(
            self.request,
            ProjectCreateSchema(
                name="General Project",
                domain="通用平台",
                type="预研",
                code="general-project",
                manager_ids=[str(self.user.id)],
                enable_milestone=False,
                enable_iteration=False,
                enable_quality=False,
                enable_dts=False,
            ),
        )

        updated = project_service.update_project(
            self.request,
            project.id,
            ProjectUpdateSchema(name="General Project Updated"),
        )

        self.assertEqual(updated.power_info_link, [])
        self.assertEqual(updated.hardware_software_interface_doc, [])
        self.assertEqual(updated.name, "General Project Updated")

    def test_empty_vehicle_link_rows_are_dropped(self):
        project = project_service.create_project(
            self.request,
            ProjectCreateSchema(
                name="Vehicle Project Empty Links",
                domain="车控域",
                type="量产",
                code="vehicle-project-empty-links",
                manager_ids=[str(self.user.id)],
                enable_milestone=False,
                enable_iteration=False,
                enable_quality=False,
                enable_dts=False,
                power_info_link=[
                    {"chip_name": "", "url": ""},
                    {"chip_name": "VIU-1", "url": " https://example.com/power "},
                ],
                hardware_software_interface_doc=[],
            ),
        )

        self.assertEqual(
            project.power_info_link,
            [{"chip_name": "VIU-1", "url": "https://example.com/power"}],
        )
        self.assertEqual(project.hardware_software_interface_doc, [])

    def test_partial_vehicle_link_row_raises_validation_error(self):
        project = Project.objects.create(
            name="Vehicle Project Partial Link",
            domain="车控项目",
            type="量产",
            code="vehicle-project-partial-link",
            sys_creator=self.user,
        )

        with self.assertRaises(HttpError):
            project_service.update_project(
                self.request,
                project.id,
                ProjectUpdateSchema(
                    power_info_link=[
                        {"chip_name": "VIU-1", "url": ""},
                    ],
                ),
            )

    def test_non_vehicle_update_preserves_existing_optional_fields_when_omitted(self):
        project = Project.objects.create(
            name="Vehicle Project",
            domain="车控项目",
            type="量产",
            code="vehicle-project-preserve",
            power_info_link=[
                {"chip_name": "VIU-1", "url": "https://example.com/existing-power"}
            ],
            hardware_software_interface_doc=[
                {
                    "chip_name": "VIU-1",
                    "url": "https://example.com/existing-interface",
                }
            ],
            sys_creator=self.user,
        )
        project.managers.add(self.user)

        updated = project_service.update_project(
            self.request,
            project.id,
            ProjectUpdateSchema(domain="通用项目"),
        )

        self.assertEqual(updated.domain, "通用项目")
        self.assertEqual(
            updated.power_info_link,
            [{"chip_name": "VIU-1", "url": "https://example.com/existing-power"}],
        )
        self.assertEqual(
            updated.hardware_software_interface_doc,
            [
                {
                    "chip_name": "VIU-1",
                    "url": "https://example.com/existing-interface",
                }
            ],
        )

    def test_project_schema_exposes_optional_fields(self):
        schema_fields = getattr(ProjectOut, "model_fields", None)
        if schema_fields is None:
            schema_fields = ProjectOut.__fields__

        self.assertIn("power_info_link", schema_fields)
        self.assertIn("hardware_software_interface_doc", schema_fields)
        self.assertIn("release_plans", schema_fields)

    def test_migration_normalizes_legacy_string_values(self):
        migration = importlib.import_module(
            "apps.project_manager.migrations.0050_project_vehicle_links_json"
        )

        self.assertEqual(
            migration.normalize_vehicle_link_value(" https://example.com/power "),
            [{"chip_name": "", "url": "https://example.com/power"}],
        )
        self.assertEqual(migration.normalize_vehicle_link_value(""), [])
        self.assertEqual(
            migration.normalize_vehicle_link_value(
                [{"chip_name": " VIU ", "url": " https://example.com/doc "}],
            ),
            [{"chip_name": "VIU", "url": "https://example.com/doc"}],
        )


class ProjectReleasePlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="release-plan-tester",
            password="secret",
            name="Release Plan Tester",
        )
        self.request = SimpleNamespace(auth=self.user)
        self.idvp = IdvpPlatform.objects.create(name="IDVP-R1", sys_creator=self.user)
        self.cdc = CdcPlatform.objects.create(name="CDC-R1", sys_creator=self.user)

    def test_create_project_persists_multi_branch_release_plans(self):
        project = project_service.create_project(
            self.request,
            ProjectCreateSchema(
                name="Release Vehicle Project",
                domain="车控项目",
                type="量产",
                code="release-vehicle-project",
                manager_ids=[str(self.user.id)],
                enable_milestone=False,
                enable_iteration=False,
                enable_quality=False,
                enable_dts=False,
                release_plans=[
                    {
                        "branch_name": "main",
                        "release_date": "2026-08-01",
                        "version_type": "Release",
                        "idvp_platform_id": str(self.idvp.id),
                        "release_vehicles": ["车型A", "车型B"],
                    },
                    {
                        "branch_name": "dev",
                        "release_date": "2026-08-08",
                        "version_type": "Beta",
                        "idvp_platform_id": str(self.idvp.id),
                        "release_vehicles": ["车型C"],
                    },
                ],
            ),
        )

        plans = list(project.release_plans.order_by("branch_name"))
        self.assertEqual(len(plans), 2)
        self.assertEqual({plan.branch_name for plan in plans}, {"dev", "main"})
        self.assertEqual(plans[0].scenario, "vehicle")

    def test_update_project_replaces_release_plans(self):
        project = project_service.create_project(
            self.request,
            ProjectCreateSchema(
                name="Release Replace Project",
                domain="车控项目",
                type="量产",
                code="release-replace-project",
                manager_ids=[str(self.user.id)],
                enable_milestone=False,
                enable_iteration=False,
                enable_quality=False,
                enable_dts=False,
                release_plans=[
                    {
                        "branch_name": "old",
                        "release_date": "2026-08-01",
                        "version_type": "RC",
                        "idvp_platform_id": str(self.idvp.id),
                        "release_vehicles": ["车型A"],
                    }
                ],
            ),
        )

        project_service.update_project(
            self.request,
            project.id,
            ProjectUpdateSchema(
                release_plans=[
                    {
                        "branch_name": "new",
                        "release_date": "2026-09-01",
                        "version_type": "灰度",
                        "idvp_platform_id": str(self.idvp.id),
                        "release_vehicles": ["车型B"],
                    }
                ],
            ),
        )

        plans = list(ProjectReleasePlan.objects.filter(project=project))
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].branch_name, "new")
        self.assertEqual(plans[0].version_type, "灰度")

    def test_release_plan_validates_required_fields_and_scenario_platform(self):
        with self.assertRaises(HttpError):
            project_service.create_project(
                self.request,
                ProjectCreateSchema(
                    name="Invalid Vehicle Release",
                    domain="车控项目",
                    type="量产",
                    code="invalid-vehicle-release",
                    manager_ids=[str(self.user.id)],
                    enable_milestone=False,
                    enable_iteration=False,
                    enable_quality=False,
                    enable_dts=False,
                    release_plans=[
                        {
                            "branch_name": "main",
                            "release_date": "2026-08-01",
                            "version_type": "Release",
                            "cdc_platform_id": str(self.cdc.id),
                            "release_vehicles": ["车型A"],
                        }
                    ],
                ),
            )

        with self.assertRaises(HttpError):
            project_service.create_project(
                self.request,
                ProjectCreateSchema(
                    name="Invalid Cockpit Release",
                    domain="座舱项目",
                    type="量产",
                    code="invalid-cockpit-release",
                    manager_ids=[str(self.user.id)],
                    enable_milestone=False,
                    enable_iteration=False,
                    enable_quality=False,
                    enable_dts=False,
                    release_plans=[
                        {
                            "branch_name": "main",
                            "release_date": "2026-08-01",
                            "version_type": "Release",
                            "idvp_platform_id": str(self.idvp.id),
                            "release_vehicles": ["车型A"],
                        }
                    ],
                ),
            )

        with self.assertRaises(HttpError):
            project_service.create_project(
                self.request,
                ProjectCreateSchema(
                    name="Invalid Version Release",
                    domain="车控项目",
                    type="量产",
                    code="invalid-version-release",
                    manager_ids=[str(self.user.id)],
                    enable_milestone=False,
                    enable_iteration=False,
                    enable_quality=False,
                    enable_dts=False,
                    release_plans=[
                        {
                            "branch_name": "main",
                            "release_date": "2026-08-01",
                            "version_type": "",
                            "idvp_platform_id": str(self.idvp.id),
                            "release_vehicles": ["车型A"],
                        }
                    ],
                ),
            )

    def test_release_plan_list_and_calendar_filters(self):
        project_service.create_project(
            self.request,
            ProjectCreateSchema(
                name="Calendar Release Project",
                domain="座舱项目",
                type="量产",
                code="calendar-release-project",
                manager_ids=[str(self.user.id)],
                enable_milestone=False,
                enable_iteration=False,
                enable_quality=False,
                enable_dts=False,
                release_plans=[
                    {
                        "branch_name": "cockpit-main",
                        "release_date": "2026-08-10",
                        "version_type": "Hotfix",
                        "cdc_platform_id": str(self.cdc.id),
                        "release_vehicles": ["车型Z"],
                    }
                ],
            ),
        )

        filters = ReleasePlanFilterSchema(
            keyword="Calendar",
            platform_keyword="CDC-R1",
            vehicle_keyword="车型Z",
            release_date_start="2026-08-01",
            release_date_end="2026-08-31",
        )
        rows = release_plan_service.list_release_plans(filters)
        calendar = release_plan_service.get_release_plan_calendar(filters)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["platform_name"], "CDC-R1")
        self.assertEqual(calendar["total"], 1)
        self.assertEqual(calendar["days"][0]["date"].isoformat(), "2026-08-10")
