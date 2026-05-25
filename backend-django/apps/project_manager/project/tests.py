from types import SimpleNamespace

from django.test import RequestFactory, TestCase

from core.user.user_model import User

from apps.project_manager.project import project_service
from apps.project_manager.project.project_model import Project
from apps.project_manager.project.project_schema import (
    ProjectCreateSchema,
    ProjectOut,
    ProjectUpdateSchema,
)


class ProjectVehicleOptionalFieldsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(
            username="project-tester",
            password="secret",
            name="Project Tester",
        )
        self.request = SimpleNamespace(auth=self.user)

    def test_create_vehicle_project_persists_optional_fields(self):
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
            power_info_link="https://example.com/power",
            hardware_software_interface_doc="https://example.com/interface",
        )

        project = project_service.create_project(self.request, payload)
        detail_request = self.factory.get(f"/api/project-manager/projects/{project.id}")
        detail_request.auth = self.user
        detail = project_service.get_project(detail_request, project.id)

        self.assertEqual(detail.power_info_link, "https://example.com/power")
        self.assertEqual(
            detail.hardware_software_interface_doc,
            "https://example.com/interface",
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

        self.assertIsNone(updated.power_info_link)
        self.assertIsNone(updated.hardware_software_interface_doc)
        self.assertEqual(updated.name, "General Project Updated")

    def test_non_vehicle_update_preserves_existing_optional_fields_when_omitted(self):
        project = Project.objects.create(
            name="Vehicle Project",
            domain="车控项目",
            type="量产",
            code="vehicle-project-preserve",
            power_info_link="https://example.com/existing-power",
            hardware_software_interface_doc="https://example.com/existing-interface",
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
            "https://example.com/existing-power",
        )
        self.assertEqual(
            updated.hardware_software_interface_doc,
            "https://example.com/existing-interface",
        )

    def test_project_schema_exposes_optional_fields(self):
        schema_fields = getattr(ProjectOut, "model_fields", None)
        if schema_fields is None:
            schema_fields = ProjectOut.__fields__

        self.assertIn("power_info_link", schema_fields)
        self.assertIn("hardware_software_interface_doc", schema_fields)
