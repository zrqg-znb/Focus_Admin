import io

import openpyxl
from django.test import TestCase
from ninja.errors import HttpError

from apps.code_compliance import base_services as services
from apps.code_compliance.base_schemas import (
    BatchBindBranchesIn,
    BatchBindRepositoriesIn,
    BranchIn,
    OrganizationIn,
    OrganizationPatch,
    RepositoryIn,
)
from apps.code_compliance.models import (
    ComplianceManagedBranch,
    ComplianceOrganization,
    ComplianceRepository,
    ComplianceRepositoryBranch,
)
from core.dict.dict_model import Dict
from core.dict_item.dict_item_model import DictItem
from core.pl.pl_model import PlGroup
from core.user.user_model import User


class NamedBytesIO(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.name = name


def build_workbook_file(header: list[str], rows: list[list[object]], name: str) -> NamedBytesIO:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return NamedBytesIO(stream.read(), name)


class CodeComplianceFoundationTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username="compliance-admin",
            password="secret",
            name="Compliance Admin",
        )
        self.pl_user = User.objects.create(
            username="pl-owner",
            password="secret",
            name="PL Owner",
        )
        self.repo_type_dict = Dict.objects.create(
            name="代码仓类型",
            code=services.REPO_TYPE_DICT_CODE,
            status=True,
        )
        DictItem.objects.create(
            dict=self.repo_type_dict,
            label="业务仓",
            value="business",
            status=True,
        )
        self.pl_group = PlGroup.objects.create(
            name="座舱PL组",
            code="cockpit-pl",
            status=True,
            pl_user=self.pl_user,
        )
        self.pl_group.members.add(self.pl_user)

    def create_org(self, group_id: str = "10001", name: str = "座舱组织"):
        return services.create_organization(
            self.user,
            OrganizationIn(
                group_id=group_id,
                name=name,
                mode="CR",
                domain="cockpit",
            ),
        )

    def create_repo(self, org_id: str, project_id: str = "20001"):
        return services.create_repository(
            self.user,
            RepositoryIn(
                project_id=project_id,
                project_name=f"repo-{project_id}",
                project_url=f"https://git.example.com/{project_id}",
                organization_id=org_id,
                repo_type="business",
                responsibility_group_ids=[str(self.pl_group.id)],
                mode="MR",
                domain="cockpit",
            ),
        )

    def create_branch(self, branch_name: str = "master"):
        return services.create_branch(
            self.user,
            BranchIn(
                branch_name=branch_name,
                branch_type="trunk",
                domain="cockpit",
            ),
        )

    def test_organization_tree_counts_direct_repositories(self):
        root = self.create_org()
        child = services.create_organization(
            self.user,
            OrganizationIn(
                group_id="10002",
                name="座舱子组织",
                parent_id=root["id"],
                mode="CR",
                domain="cockpit",
            ),
        )
        self.create_repo(root["id"], "20001")
        self.create_repo(child["id"], "20002")

        tree = services.list_organization_tree()

        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["repository_count"], 1)
        self.assertEqual(tree[0]["children"][0]["repository_count"], 1)

    def test_organization_prevents_cycles_and_delete_with_repositories(self):
        root = self.create_org()
        child = services.create_organization(
            self.user,
            OrganizationIn(
                group_id="10002",
                name="座舱子组织",
                parent_id=root["id"],
            ),
        )

        with self.assertRaises(HttpError):
            services.update_organization(
                self.user,
                root["id"],
                OrganizationPatch(parent_id=child["id"]),
            )

        self.create_repo(root["id"], "20001")
        with self.assertRaises(HttpError):
            services.delete_organization(root["id"])

    def test_repository_filters_and_serializes_pl_group_and_repo_type(self):
        org = self.create_org()
        self.create_repo(org["id"], "20001")
        other_org = self.create_org("10003", "车控组织")
        self.create_repo(other_org["id"], "20002")

        page = services.list_repositories(organization_id=org["id"])

        self.assertEqual(page["total"], 1)
        item = page["items"][0]
        self.assertEqual(item["repo_type_label"], "业务仓")
        self.assertEqual(item["responsibility_group_names"], ["座舱PL组"])

    def test_batch_bind_supports_append_and_replace_from_both_sides(self):
        org = self.create_org()
        repo_a = self.create_repo(org["id"], "20001")
        repo_b = self.create_repo(org["id"], "20002")
        branch_a = self.create_branch("master")
        branch_b = self.create_branch("release")

        result = services.bind_branches_to_repositories(
            BatchBindBranchesIn(
                repository_ids=[repo_a["id"]],
                branch_ids=[branch_a["id"], branch_b["id"]],
                mode="append",
            ).repository_ids,
            [branch_a["id"], branch_b["id"]],
            "append",
        )
        self.assertEqual(result["created_count"], 2)

        result = services.bind_repositories_to_branches(
            BatchBindRepositoriesIn(
                branch_ids=[branch_a["id"]],
                repository_ids=[repo_b["id"]],
                mode="replace",
            ).branch_ids,
            [repo_b["id"]],
            "replace",
        )
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["removed_count"], 1)
        self.assertTrue(
            ComplianceRepositoryBranch.objects.filter(
                repository_id=repo_b["id"],
                branch_id=branch_a["id"],
                is_deleted=False,
            ).exists()
        )
        self.assertFalse(
            ComplianceRepositoryBranch.objects.filter(
                repository_id=repo_a["id"],
                branch_id=branch_a["id"],
                is_deleted=False,
            ).exists()
        )

    def test_import_repositories_returns_row_errors(self):
        org = self.create_org()
        file_obj = build_workbook_file(
            ["代码库ID", "代码库名", "代码库URL", "组织ID", "模式", "领域", "代码仓类型", "责任PL组", "备注"],
            [
                ["20001", "repo-ok", "https://git.example.com/ok", "10001", "CR", "座舱", "business", "cockpit-pl", ""],
                ["20002", "repo-bad", "https://git.example.com/bad", "missing-org", "CR", "座舱", "business", "", ""],
            ],
            "repositories.xlsx",
        )

        result = services.import_repositories(self.user, file_obj)

        self.assertEqual(result.created_count, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].row_no, 3)
        self.assertTrue(
            ComplianceRepository.objects.filter(
                organization_id=org["id"],
                project_id="20001",
                is_deleted=False,
            ).exists()
        )

    def test_import_branches_updates_existing_row(self):
        branch = self.create_branch("master")
        self.assertTrue(
            ComplianceManagedBranch.objects.filter(id=branch["id"], alias="").exists()
        )
        file_obj = build_workbook_file(
            ["分支名称", "创建日期", "分支类型", "分支别名", "分支用途", "领域", "备注"],
            [["master", "2026-01-01", "主干", "主线", "主干开发", "cockpit", ""]],
            "branches.xlsx",
        )

        result = services.import_branches(self.user, file_obj)

        self.assertEqual(result.updated_count, 1)
        updated = ComplianceManagedBranch.objects.get(id=branch["id"])
        self.assertEqual(updated.alias, "主线")

    def test_organization_template_route_is_not_captured_by_dynamic_org_route(self):
        """组织模板静态路由必须先于 /organizations/{org_id} 匹配。"""
        response = self.client.get("/api/code-compliance/base/organizations/template")

        self.assertNotEqual(response.status_code, 405)
