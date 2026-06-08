import io
from datetime import datetime, timedelta
from unittest.mock import patch

import openpyxl
from django.test import override_settings
from django.utils import timezone
from django.test import TestCase
from ninja.errors import HttpError

from apps.code_compliance import base_services as services
from apps.code_compliance import missing_merge_services
from apps.code_compliance.base_schemas import (
    BatchBindBranchesIn,
    BatchBindRepositoriesIn,
    BranchIn,
    OrganizationIn,
    OrganizationPatch,
    RepositoryIn,
)
from apps.code_compliance.missing_merge_client import (
    DEFAULT_CR_API_URL_TEMPLATE,
    build_cr_encoded_query,
    build_cr_request_params,
    build_cr_request_url,
)
from apps.code_compliance.missing_merge_schemas import MissingMergeRecordStatusIn, MissingMergeScanRunIn
from apps.code_compliance.models import (
    MISSING_MERGE_SCAN_STATUS_FAILED,
    MISSING_MERGE_SCAN_STATUS_PENDING,
    MISSING_MERGE_SCAN_STATUS_RUNNING,
    MISSING_MERGE_SCAN_STATUS_SUCCESS,
    MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
    MISSING_MERGE_OPERATION_AUTO_CLOSED,
    MISSING_MERGE_OPERATION_DETECTED,
    MISSING_MERGE_OPERATION_MANUAL_HANDLE,
    MISSING_MERGE_OPERATION_REOPENED,
    MISSING_MERGE_STATUS_FIXED,
    MISSING_MERGE_STATUS_IGNORED,
    MISSING_MERGE_STATUS_OPEN,
    ComplianceManagedBranch,
    ComplianceMissingMergeOperationLog,
    ComplianceMissingMergeRecord,
    ComplianceMissingMergeScanTask,
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

    def create_branch(self, branch_name: str = "master", branch_type: str = "trunk"):
        return services.create_branch(
            self.user,
            BranchIn(
                branch_name=branch_name,
                branch_type=branch_type,
                domain="cockpit",
            ),
        )

    def create_missing_record(
        self,
        repository: ComplianceRepository,
        organization: ComplianceOrganization,
        *,
        change_key: str = "mock-20001-001",
        status: str = MISSING_MERGE_STATUS_OPEN,
    ):
        return ComplianceMissingMergeRecord.objects.create(
            organization=organization,
            repository=repository,
            organization_group_id=organization.group_id,
            organization_name=organization.name,
            repository_project_id=repository.project_id,
            repository_name=repository.project_name,
            project_id=repository.project_id,
            trunk_branch="master",
            release_branch="release/1.0",
            change_request_iid="10001",
            change_key=change_key,
            title=f"record {change_key}",
            merged_at=timezone.now(),
            target_branch="master",
            author_username="user01",
            detected_at=timezone.now(),
            status=status,
        )

    def run_missing_scan_now(self, payload: MissingMergeScanRunIn):
        """测试中同步执行已创建任务，避免后台线程带来竞态。"""
        task = missing_merge_services.create_scan_task(self.user, payload)
        return missing_merge_services.execute_scan_task(str(task.id), str(self.user.id))

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

    def test_missing_merge_repository_options_support_pagination_and_filters(self):
        """漏合风险手动同步代码库选项支持分页、组织和关键词过滤。"""
        org = self.create_org()
        repo_a = self.create_repo(org["id"], "20001")
        repo_b = self.create_repo(org["id"], "20002")
        other_org = self.create_org("10003", "车控组织")
        self.create_repo(other_org["id"], "30001")

        page = missing_merge_services.list_repository_options(
            page=1,
            page_size=1,
            organization_id=org["id"],
        )

        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)

        keyword_page = missing_merge_services.list_repository_options(
            keyword=repo_b["project_id"],
            organization_id=org["id"],
        )
        self.assertEqual(keyword_page["total"], 1)
        self.assertEqual(keyword_page["items"][0]["id"], repo_b["id"])
        self.assertNotEqual(keyword_page["items"][0]["id"], repo_a["id"])

    def test_missing_merge_records_support_scope_union_filters(self):
        """漏合风险级联筛选支持组织子树、多个代码库和混选并集。"""
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
        other = self.create_org("10003", "车控组织")
        root_repo = self.create_repo(root["id"], "20001")
        child_repo = self.create_repo(child["id"], "20002")
        other_repo = self.create_repo(other["id"], "30001")
        root_record = self.create_missing_record(
            ComplianceRepository.objects.get(id=root_repo["id"]),
            ComplianceOrganization.objects.get(id=root["id"]),
            change_key="root-risk",
        )
        child_record = self.create_missing_record(
            ComplianceRepository.objects.get(id=child_repo["id"]),
            ComplianceOrganization.objects.get(id=child["id"]),
            change_key="child-risk",
        )
        other_record = self.create_missing_record(
            ComplianceRepository.objects.get(id=other_repo["id"]),
            ComplianceOrganization.objects.get(id=other["id"]),
            change_key="other-risk",
        )

        old_org_page = missing_merge_services.list_missing_merge_records(
            organization_id=root["id"],
            page_size=10,
        )
        old_repo_page = missing_merge_services.list_missing_merge_records(
            repository_id=child_repo["id"],
            page_size=10,
        )
        parent_scope_page = missing_merge_services.list_missing_merge_records(
            organization_ids=root["id"],
            page_size=10,
        )
        multi_repo_page = missing_merge_services.list_missing_merge_records(
            repository_ids=f"{child_repo['id']},{other_repo['id']}",
            page_size=10,
        )
        union_page = missing_merge_services.list_missing_merge_records(
            organization_ids=[root["id"]],
            repository_ids=[other_repo["id"]],
            page_size=10,
        )

        self.assertEqual({item["id"] for item in old_org_page["items"]}, {str(root_record.id)})
        self.assertEqual({item["id"] for item in old_repo_page["items"]}, {str(child_record.id)})
        self.assertEqual(
            {item["id"] for item in parent_scope_page["items"]},
            {str(root_record.id), str(child_record.id)},
        )
        self.assertEqual(
            {item["id"] for item in multi_repo_page["items"]},
            {str(child_record.id), str(other_record.id)},
        )
        self.assertEqual(
            {item["id"] for item in union_page["items"]},
            {str(root_record.id), str(child_record.id), str(other_record.id)},
        )

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

    def test_cr_client_builds_encoded_get_query(self):
        """数据湖 GET 参数必须包含固定 state、only_count 和 URL 编码时间。"""
        merged_after = datetime(2026, 6, 11, 16, 20, 20, tzinfo=timezone.get_fixed_timezone(480))
        merged_before = merged_after + timedelta(hours=1)

        params = build_cr_request_params(
            page=1,
            per_page=50,
            target_branch="master",
            projects=["20001", "20002"],
            merged_after=merged_after,
            merged_before=merged_before,
            only_count=True,
        )
        encoded = build_cr_encoded_query(params)

        self.assertEqual(params["state"], "merged")
        self.assertEqual(params["only_count"], "True")
        self.assertEqual(params["projects"], ["20001", "20002"])
        self.assertIn("projects=20001&projects=20002", encoded)
        self.assertIn("merged_after=2026-06-11T16%3A20%3A20.000%2B08%3A00", encoded)

    def test_cr_client_builds_group_path_url(self):
        """数据湖 URL 固定为组织路径模板，group_id 需要动态注入并编码。"""
        merged_after = datetime(2026, 6, 11, 16, 20, 20, tzinfo=timezone.get_fixed_timezone(480))
        params = build_cr_request_params(
            page=1,
            per_page=50,
            target_branch="master",
            projects=["20001"],
            merged_after=merged_after,
            merged_before=merged_after + timedelta(hours=1),
            only_count=False,
        )

        url = build_cr_request_url(DEFAULT_CR_API_URL_TEMPLATE, "A 组/10001", params)

        self.assertTrue(url.startswith("http://apig.yinwang.com/api/v4/groups/A%20%E7%BB%84%2F10001/change_requests?"))
        self.assertIn("projects=20001", url)

    def test_missing_merge_status_requires_valid_remark_and_logs_manual_history(self):
        """人工处理必须填写合规备注，并写入操作历史。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        record = self.create_missing_record(repository, organization)

        for remark in ("", "1234", "包含<script>"):
            with self.assertRaises(HttpError):
                missing_merge_services.update_missing_merge_status(
                    self.user,
                    str(record.id),
                    MissingMergeRecordStatusIn(
                        status=MISSING_MERGE_STATUS_IGNORED,
                        handle_remark=remark,
                    ),
                )

        result = missing_merge_services.update_missing_merge_status(
            self.user,
            str(record.id),
            MissingMergeRecordStatusIn(
                status=MISSING_MERGE_STATUS_IGNORED,
                handle_remark="确认无需补合处理",
            ),
        )

        self.assertEqual(result["status"], MISSING_MERGE_STATUS_IGNORED)
        self.assertEqual(result["operation_logs"][0]["operation_type"], MISSING_MERGE_OPERATION_MANUAL_HANDLE)
        self.assertEqual(result["operation_logs"][0]["remark"], "确认无需补合处理")

    def test_missing_merge_manual_run_submits_async_task_and_blocks_active(self):
        """手动同步只提交后台任务，已有未完成任务时不再重复创建。"""
        now = timezone.now()
        payload = MissingMergeScanRunIn(
            merged_after=now - timedelta(days=1),
            merged_before=now,
        )

        with patch.object(missing_merge_services, "_start_scan_task_thread") as start_thread:
            result = missing_merge_services.run_missing_merge_scan(self.user, payload)
            blocked = missing_merge_services.run_missing_merge_scan(self.user, payload)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["task"]["status"], MISSING_MERGE_SCAN_STATUS_PENDING)
        start_thread.assert_called_once()
        self.assertFalse(blocked["accepted"])
        self.assertEqual(blocked["task"]["id"], result["task"]["id"])
        self.assertEqual(ComplianceMissingMergeScanTask.objects.count(), 1)

    def test_execute_scan_task_records_failure(self):
        """后台执行异常必须回写 failed 状态和错误信息，供历史页排障。"""
        now = timezone.now()
        task = missing_merge_services.create_scan_task(
            self.user,
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now,
            ),
        )

        with patch.object(missing_merge_services, "_execute_scan", side_effect=RuntimeError("mock failure")):
            result = missing_merge_services.execute_scan_task(str(task.id), str(self.user.id))

        task.refresh_from_db()
        self.assertEqual(result["status"], MISSING_MERGE_SCAN_STATUS_FAILED)
        self.assertEqual(task.status, MISSING_MERGE_SCAN_STATUS_FAILED)
        self.assertIn("mock failure", task.error_message)
        self.assertIsNotNone(task.finished_at)

    def test_scan_task_detail_and_filters(self):
        """任务历史支持详情读取和触发方式、状态、时间范围筛选。"""
        now = timezone.now()
        old_task = missing_merge_services.create_scan_task(
            self.user,
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=3),
                merged_before=now - timedelta(days=2),
            ),
        )
        new_task = missing_merge_services.create_scan_task(
            self.user,
            MissingMergeScanRunIn(
                merged_after=now - timedelta(hours=2),
                merged_before=now,
            ),
            trigger_type=MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
        )
        ComplianceMissingMergeScanTask.objects.filter(id=old_task.id).update(
            status=MISSING_MERGE_SCAN_STATUS_FAILED,
            started_at=now - timedelta(days=3),
        )
        ComplianceMissingMergeScanTask.objects.filter(id=new_task.id).update(
            status=MISSING_MERGE_SCAN_STATUS_SUCCESS,
            started_at=now - timedelta(hours=1),
        )

        detail = missing_merge_services.get_scan_task(str(new_task.id))
        page = missing_merge_services.list_scan_tasks(
            status=MISSING_MERGE_SCAN_STATUS_SUCCESS,
            trigger_type=MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
            merged_after=now - timedelta(days=1),
            started_after=now - timedelta(hours=2),
        )

        self.assertEqual(detail["id"], str(new_task.id))
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["id"], str(new_task.id))

    @override_settings(CODE_COMPLIANCE_CR_FORCE_MOCK=True)
    def test_missing_merge_scan_detects_fixed_and_preserves_ignored(self):
        """扫描应识别主干差集，自动关闭已补合项，并不覆盖已忽略项。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        trunk = self.create_branch("master", "trunk")
        release = self.create_branch("release/1.0", "release")
        services.bind_branches_to_repositories(
            [repo["id"]],
            [trunk["id"], release["id"]],
            "append",
        )
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        now = timezone.now()
        self.create_missing_record(
            repository,
            organization,
            change_key="mock-20001-001",
            status=MISSING_MERGE_STATUS_OPEN,
        )
        ignored = self.create_missing_record(
            repository,
            organization,
            change_key="mock-20001-003",
            status=MISSING_MERGE_STATUS_IGNORED,
        )
        ignored.handle_remark = "人工忽略"
        ignored.save()

        task = self.run_missing_scan_now(
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now + timedelta(days=1),
            ),
        )

        self.assertEqual(task["status"], "success")
        self.assertGreater(task["detected_count"], 0)
        self.assertGreater(task["created_count"], 0)
        self.assertGreater(task["fixed_count"], 0)
        fixed_record = ComplianceMissingMergeRecord.objects.get(change_key="mock-20001-001")
        ignored.refresh_from_db()
        self.assertEqual(fixed_record.status, MISSING_MERGE_STATUS_FIXED)
        self.assertEqual(ignored.status, MISSING_MERGE_STATUS_IGNORED)
        self.assertTrue(
            ComplianceMissingMergeOperationLog.objects.filter(
                record=fixed_record,
                operation_type=MISSING_MERGE_OPERATION_AUTO_CLOSED,
                remark=missing_merge_services.AUTO_CLOSED_REMARK,
            ).exists()
        )
        self.assertTrue(
            ComplianceMissingMergeRecord.objects.filter(
                change_key="mock-20001-006",
                status=MISSING_MERGE_STATUS_OPEN,
            ).exists()
        )
        created_record = ComplianceMissingMergeRecord.objects.get(change_key="mock-20001-006")
        self.assertTrue(
            ComplianceMissingMergeOperationLog.objects.filter(
                record=created_record,
                operation_type=MISSING_MERGE_OPERATION_DETECTED,
            ).exists()
        )

        self.run_missing_scan_now(
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now + timedelta(days=1),
            ),
        )
        self.assertEqual(
            ComplianceMissingMergeOperationLog.objects.filter(
                record=fixed_record,
                operation_type=MISSING_MERGE_OPERATION_AUTO_CLOSED,
            ).count(),
            1,
        )

    @override_settings(CODE_COMPLIANCE_CR_FORCE_MOCK=True)
    def test_missing_merge_scan_accepts_multiple_repository_ids(self):
        """手动同步支持多选代码库，并把多个 project_id 作为 projects 数组传给数据湖。"""
        org = self.create_org()
        repo_a = self.create_repo(org["id"], "20001")
        repo_b = self.create_repo(org["id"], "20002")
        repo_c = self.create_repo(org["id"], "20003")
        trunk = self.create_branch("master", "trunk")
        release = self.create_branch("release/1.0", "release")
        services.bind_branches_to_repositories(
            [repo_a["id"], repo_b["id"], repo_c["id"]],
            [trunk["id"], release["id"]],
            "append",
        )
        now = timezone.now()

        task = self.run_missing_scan_now(
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now + timedelta(days=1),
                repository_ids=[repo_a["id"], repo_b["id"]],
            ),
        )

        self.assertEqual(task["status"], "success")
        self.assertEqual(task["scanned_repository_count"], 2)
        self.assertEqual(set(task["filter_payload"]["repository_ids"]), {repo_a["id"], repo_b["id"]})
        self.assertTrue(ComplianceMissingMergeRecord.objects.filter(project_id="20001").exists())
        self.assertTrue(ComplianceMissingMergeRecord.objects.filter(project_id="20002").exists())
        self.assertFalse(ComplianceMissingMergeRecord.objects.filter(project_id="20003").exists())

    @override_settings(CODE_COMPLIANCE_CR_FORCE_MOCK=True)
    def test_scheduled_missing_merge_scan_writes_task_history(self):
        """定时扫描复用任务历史表，并标记为 scheduled 触发。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        trunk = self.create_branch("master", "trunk")
        release = self.create_branch("release/1.0", "release")
        services.bind_branches_to_repositories(
            [repo["id"]],
            [trunk["id"], release["id"]],
            "append",
        )

        result = missing_merge_services.run_scheduled_missing_merge_scan.__wrapped__()

        self.assertEqual(result["status"], MISSING_MERGE_SCAN_STATUS_SUCCESS)
        self.assertEqual(result["trigger_type"], MISSING_MERGE_SCAN_TRIGGER_SCHEDULED)
        self.assertTrue(
            ComplianceMissingMergeScanTask.objects.filter(
                id=result["id"],
                trigger_type=MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
            ).exists()
        )

    @override_settings(CODE_COMPLIANCE_CR_FORCE_MOCK=True)
    def test_missing_merge_scan_reopens_previously_fixed_record(self):
        """已补合记录再次出现在主干差集时，应重新变为未处理并写历史。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        trunk = self.create_branch("master", "trunk")
        release = self.create_branch("release/1.0", "release")
        services.bind_branches_to_repositories(
            [repo["id"]],
            [trunk["id"], release["id"]],
            "append",
        )
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        record = self.create_missing_record(
            repository,
            organization,
            change_key="mock-20001-006",
            status=MISSING_MERGE_STATUS_FIXED,
        )
        now = timezone.now()

        task = self.run_missing_scan_now(
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now + timedelta(days=1),
            ),
        )

        record.refresh_from_db()
        self.assertEqual(task["status"], "success")
        self.assertEqual(record.status, MISSING_MERGE_STATUS_OPEN)
        self.assertTrue(
            ComplianceMissingMergeOperationLog.objects.filter(
                record=record,
                operation_type=MISSING_MERGE_OPERATION_REOPENED,
            ).exists()
        )
