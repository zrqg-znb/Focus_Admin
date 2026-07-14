import io
from datetime import date, datetime, timedelta
from unittest.mock import patch

import openpyxl
from django.test import override_settings
from django.utils import timezone
from django.test import TestCase
from ninja.errors import HttpError

from apps.code_compliance import base_services as services
from apps.code_compliance import contribution_services
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
    DEFAULT_MR_API_URL_TEMPLATE,
    build_cr_encoded_query,
    build_cr_request_params,
    build_cr_request_url,
    build_mr_request_params,
    build_mr_request_url,
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
    ComplianceContributionDailyAggregate,
    ComplianceContributionCollectTask,
    ComplianceContributionRecord,
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

    def create_org(self, group_id: str = "10001", name: str = "座舱组织", mode: str = "CR"):
        return services.create_organization(
            self.user,
            OrganizationIn(
                group_id=group_id,
                name=name,
                mode=mode,
                domain="cockpit",
            ),
        )

    def create_repo(self, org_id: str, project_id: str = "20001", mode: str = "CR"):
        return services.create_repository(
            self.user,
            RepositoryIn(
                project_id=project_id,
                project_name=f"repo-{project_id}",
                project_url=f"https://git.example.com/{project_id}",
                organization_id=org_id,
                repo_type="business",
                responsibility_group_ids=[str(self.pl_group.id)],
                mode=mode,
                domain="cockpit",
            ),
        )

    def create_branch(
        self,
        branch_name: str = "master",
        branch_type: str = "trunk",
        *,
        is_active: bool = True,
        created_date=None,
    ):
        return services.create_branch(
            self.user,
            BranchIn(
                branch_name=branch_name,
                branch_type=branch_type,
                created_date=created_date,
                domain="cockpit",
                is_active=is_active,
            ),
        )

    def create_missing_record(
        self,
        repository: ComplianceRepository,
        organization: ComplianceOrganization,
        *,
        author_pl_group: PlGroup | None = None,
        author_user: User | None = None,
        author_username: str = "user01",
        change_key: str = "mock-20001-001",
        detected_at=None,
        merged_at=None,
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
            merged_at=merged_at or timezone.now(),
            target_branch="master",
            author_username=author_username,
            author_user=author_user,
            author_user_name=(author_user.name or author_user.username) if author_user else "",
            author_pl_group=author_pl_group,
            author_pl_group_name=(
                author_pl_group.name
                if author_pl_group
                else missing_merge_services.UNKNOWN_PL_GROUP_NAME
            ),
            detected_at=detected_at or timezone.now(),
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

    def test_branch_active_state_filters_and_imports(self):
        """分支活跃状态支持创建、列表筛选和 Excel 导入更新。"""
        active = self.create_branch("master", is_active=True)
        archived = self.create_branch("release/old", "release", is_active=False)

        active_page = services.list_branches(is_active=True)
        archived_page = services.list_branches(is_active=False)

        self.assertEqual({item["id"] for item in active_page["items"]}, {active["id"]})
        self.assertEqual({item["id"] for item in archived_page["items"]}, {archived["id"]})

        file_obj = build_workbook_file(
            ["分支名称", "创建日期", "分支类型", "分支别名", "分支用途", "领域", "是否活跃", "备注"],
            [["release/old", "2026-01-02", "发布", "旧发布", "归档发布线", "cockpit", "活跃", ""]],
            "branches.xlsx",
        )
        result = services.import_branches(self.user, file_obj)
        updated = ComplianceManagedBranch.objects.get(id=archived["id"])

        self.assertEqual(result.updated_count, 1)
        self.assertTrue(updated.is_active)

    def test_relation_details_return_branch_repository_tree_and_sorted_branches(self):
        """关系详情接口返回弹窗所需组织树和按创建时间排序的分支。"""
        parent = services.create_organization(
            self.user,
            OrganizationIn(group_id="10000", name="根组织", mode="CR", domain="cockpit"),
        )
        child = services.create_organization(
            self.user,
            OrganizationIn(
                group_id="10001",
                name="子组织",
                parent_id=parent["id"],
                mode="CR",
                domain="cockpit",
            ),
        )
        repo = self.create_repo(child["id"], "20001")
        old_release = self.create_branch(
            "release/old",
            "release",
            is_active=False,
            created_date=date(2026, 1, 10),
        )
        trunk = self.create_branch("master", "trunk", created_date=date(2026, 1, 1))
        unknown_date = self.create_branch("feature/no-date", "development")
        services.bind_branches_to_repositories(
            [repo["id"]],
            [old_release["id"], trunk["id"], unknown_date["id"]],
            "append",
        )

        branch_relation = services.get_branch_repositories(trunk["id"])
        repo_relation = services.get_repository_branches(repo["id"])

        self.assertEqual(branch_relation["branch"]["id"], trunk["id"])
        self.assertEqual(branch_relation["organizations"][0]["children"][0]["repositories"][0]["id"], repo["id"])
        self.assertEqual(
            [item["branch_name"] for item in repo_relation["branches"]],
            ["master", "release/old", "feature/no-date"],
        )
        self.assertFalse(repo_relation["branches"][1]["is_active"])

    def test_missing_merge_scan_pairs_ignore_inactive_branches(self):
        """漏合扫描配对前排除非活跃主干和发布分支。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        active_trunk = self.create_branch("master", "trunk")
        inactive_trunk = self.create_branch("legacy-master", "trunk", is_active=False)
        active_release = self.create_branch("release/1.0", "release")
        inactive_release = self.create_branch("release/old", "release", is_active=False)
        services.bind_branches_to_repositories(
            [repo["id"]],
            [
                active_trunk["id"],
                inactive_trunk["id"],
                active_release["id"],
                inactive_release["id"],
            ],
            "append",
        )

        pairs = missing_merge_services._load_scan_pairs(repository_ids=[repo["id"]])

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].trunk_branch, "master")
        self.assertEqual(pairs[0].release_branch, "release/1.0")

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

    def test_missing_merge_scan_closes_same_pair_old_record_and_creates_new_one(self):
        """当前窗口发布分支出现旧 key 时，只闭环同配对历史风险，并新增当前窗口新风险。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        pair_a = missing_merge_services.ScanPair(
            repository=repository,
            trunk_branch="trunk-A",
            release_branch="release-A",
        )
        pair_b = missing_merge_services.ScanPair(
            repository=repository,
            trunk_branch="trunk-B",
            release_branch="release-B",
        )
        now = timezone.now()

        def row(change_key: str, branch: str):
            return {
                "added_lines": 1,
                "author_username": "user01",
                "change_key": change_key,
                "change_request_iid": change_key,
                "merged_at": now,
                "project_id": "20001",
                "removed_lines": 0,
                "target_branch": branch,
                "title": f"CR {change_key}",
            }

        def branch_rows(day: int):
            if day == 1:
                data = {
                    "trunk-A": {"20001": {"X": row("X", "trunk-A")}},
                    "release-A": {"20001": {}},
                    "trunk-B": {"20001": {"X": row("X", "trunk-B")}},
                    "release-B": {"20001": {}},
                }
            else:
                data = {
                    "trunk-A": {"20001": {"Y": row("Y", "trunk-A")}},
                    "release-A": {"20001": {"X": row("X", "release-A")}},
                    "trunk-B": {"20001": {}},
                    "release-B": {"20001": {}},
                }
            diagnostics = [
                {
                    "target_branch": branch,
                    "project_count": 1,
                    "project_ids": ["20001"],
                    "only_count": sum(len(project_rows) for project_rows in projects.values()),
                    "detail_count": sum(len(project_rows) for project_rows in projects.values()),
                }
                for branch, projects in data.items()
            ]
            return data, diagnostics

        with patch.object(missing_merge_services, "_load_scan_pairs", return_value=[pair_a, pair_b]):
            with patch.object(missing_merge_services, "_fetch_branch_rows", return_value=branch_rows(1)):
                day1_task = missing_merge_services.create_scan_task(
                    self.user,
                    MissingMergeScanRunIn(
                        merged_after=now - timedelta(days=2),
                        merged_before=now - timedelta(days=1),
                    ),
                )
                day1 = missing_merge_services.execute_scan_task(str(day1_task.id), str(self.user.id))

            with patch.object(missing_merge_services, "_fetch_branch_rows", return_value=branch_rows(2)):
                day2_task = missing_merge_services.create_scan_task(
                    self.user,
                    MissingMergeScanRunIn(
                        merged_after=now - timedelta(days=1),
                        merged_before=now,
                    ),
                )
                day2 = missing_merge_services.execute_scan_task(str(day2_task.id), str(self.user.id))

        record_a_x = ComplianceMissingMergeRecord.objects.get(
            repository=repository,
            trunk_branch="trunk-A",
            release_branch="release-A",
            change_key="X",
        )
        record_b_x = ComplianceMissingMergeRecord.objects.get(
            repository=repository,
            trunk_branch="trunk-B",
            release_branch="release-B",
            change_key="X",
        )
        record_a_y = ComplianceMissingMergeRecord.objects.get(
            repository=repository,
            trunk_branch="trunk-A",
            release_branch="release-A",
            change_key="Y",
        )

        self.assertEqual(day1["created_count"], 2)
        self.assertEqual(day2["fixed_count"], 1)
        self.assertEqual(day2["created_count"], 1)
        self.assertEqual(record_a_x.status, MISSING_MERGE_STATUS_FIXED)
        self.assertEqual(record_b_x.status, MISSING_MERGE_STATUS_OPEN)
        self.assertEqual(record_a_y.status, MISSING_MERGE_STATUS_OPEN)
        self.assertEqual(
            ComplianceMissingMergeRecord.objects.filter(
                repository=repository,
                trunk_branch="trunk-A",
                release_branch="release-A",
                change_key="X",
            ).count(),
            1,
        )
        self.assertTrue(day2["scan_diagnostics"]["pairs"])
        pair_diag = {
            (item["trunk_branch"], item["release_branch"]): item
            for item in day2["scan_diagnostics"]["pairs"]
        }
        self.assertEqual(pair_diag[("trunk-A", "release-A")]["fixed_count"], 1)
        self.assertEqual(pair_diag[("trunk-A", "release-A")]["missing_key_count"], 1)
        self.assertEqual(pair_diag[("trunk-B", "release-B")]["fixed_count"], 0)

    def test_contribution_record_upsert_and_daily_aggregate(self):
        """贡献明细按仓库、分支、change_key 幂等写入，并按受影响日期重算日聚合。"""
        org = self.create_org()
        repo_data = self.create_repo(org["id"], "20001")
        branch_data = self.create_branch("master", "trunk")
        services.bind_branches_to_repositories([repo_data["id"]], [branch_data["id"]], "append")
        repository = ComplianceRepository.objects.get(id=repo_data["id"])
        branch = ComplianceManagedBranch.objects.get(id=branch_data["id"])
        author = User.objects.create(username="dev01", password="secret", name="开发一")
        self.pl_group.members.add(author)
        merged_at = timezone.now()
        row = {
            "added_lines": 12,
            "author_username": "dev01",
            "change_key": "change-001",
            "change_request_iid": "1",
            "merged_at": merged_at,
            "project_id": repository.project_id,
            "removed_lines": 5,
            "target_branch": branch.branch_name,
            "title": "Feature A",
            "web_url": "https://git.example.com/cr/1",
        }
        assignments = contribution_services._load_author_assignments(["dev01"])

        first_created = contribution_services._upsert_contribution_record(
            repository,
            branch,
            row,
            assignments,
        )
        row["added_lines"] = 20
        second_created = contribution_services._upsert_contribution_record(
            repository,
            branch,
            row,
            assignments,
        )
        contribution_date = contribution_services._date_from_datetime(merged_at)
        aggregate_count = contribution_services._rebuild_daily_aggregates(
            {contribution_date},
            {},
        )

        record = ComplianceContributionRecord.objects.get(
            repository=repository,
            branch_name=branch.branch_name,
            change_key="change-001",
        )
        aggregate = ComplianceContributionDailyAggregate.objects.get(
            repository=repository,
            branch_name=branch.branch_name,
            author_username="dev01",
        )
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(ComplianceContributionRecord.objects.count(), 1)
        self.assertEqual(record.added_lines, 20)
        self.assertEqual(record.removed_lines, 5)
        self.assertEqual(record.net_lines, 15)
        self.assertEqual(record.changed_lines, 25)
        self.assertEqual(record.author_user.username, author.username)
        self.assertEqual(record.author_pl_group.code, self.pl_group.code)
        self.assertEqual(aggregate_count, 1)
        self.assertEqual(aggregate.cr_count, 1)
        self.assertEqual(aggregate.changed_lines, 25)
        trend = contribution_services.get_dashboard_trend()
        self.assertEqual(trend[0]["date"], contribution_date)
        self.assertNotIn("contribution_date", trend[0])

    def test_contribution_unknown_author_keeps_username(self):
        """未匹配 Focus 用户时保留数据湖工号，并归属到非底软领域。"""
        org = self.create_org()
        repo_data = self.create_repo(org["id"], "20002")
        branch_data = self.create_branch("release/1.0", "release")
        repository = ComplianceRepository.objects.get(id=repo_data["id"])
        branch = ComplianceManagedBranch.objects.get(id=branch_data["id"])
        row = {
            "added_lines": 1,
            "author_username": "external01",
            "change_key": "change-unknown",
            "merged_at": timezone.now(),
            "project_id": repository.project_id,
            "removed_lines": 0,
            "target_branch": branch.branch_name,
        }

        contribution_services._upsert_contribution_record(
            repository,
            branch,
            row,
            contribution_services._load_author_assignments(["external01"]),
        )

        record = ComplianceContributionRecord.objects.get(change_key="change-unknown")
        self.assertIsNone(record.author_user)
        self.assertEqual(record.author_username, "external01")
        self.assertEqual(record.author_pl_group_name, contribution_services.UNKNOWN_PL_GROUP_NAME)

    def test_mr_contribution_collect_uses_project_endpoint_and_source_id(self):
        """MR 贡献采集按项目请求，并使用上游 id 而非 CR change_key 幂等。"""
        org = self.create_org("mr-group", "MR组织", mode="MR")
        repo_data = self.create_repo(org["id"], "mr-project", mode="MR")
        branch_data = self.create_branch("main", "trunk")
        services.bind_branches_to_repositories([repo_data["id"]], [branch_data["id"]], "append")
        now = timezone.now()
        task = ComplianceContributionCollectTask.objects.create(
            trigger_type="manual",
            status="pending",
            merged_after=now - timedelta(days=1),
            merged_before=now,
            filter_payload={"source_mode": "MR"},
        )
        with override_settings(CODE_COMPLIANCE_MR_FORCE_MOCK=True):
            counters, diagnostics, _ = contribution_services._collect_contribution_records(task)

        record = ComplianceContributionRecord.objects.filter(repository_id=repo_data["id"]).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.source_mode, "MR")
        self.assertTrue(record.source_change_id.startswith("mr-mr-project-"))
        self.assertEqual(record.change_key, "")
        self.assertGreater(counters["fetched_count"], 0)
        self.assertEqual(len(diagnostics["mr_projects"]), 1)

    def test_mr_request_url_uses_project_id_not_group(self):
        """MR 数据湖 URL 只注入项目 ID，并复用目标分支和时间参数。"""
        now = timezone.now()
        params = build_mr_request_params(
            page=1,
            per_page=100,
            target_branch="main",
            merged_after=now - timedelta(days=1),
            merged_before=now,
            only_count=True,
        )
        url = build_mr_request_url(DEFAULT_MR_API_URL_TEMPLATE, "project/A", params)
        self.assertTrue(url.startswith("http://apig.yinwang.com/api/v4/projects/project%2FA/merge_requests?"))
        self.assertNotIn("groups/", url)

    def test_organization_and_repository_modes_must_match(self):
        """组织树与直属代码库禁止混用 CR/MR，避免进入错误的数据湖采集路径。"""
        parent = self.create_org("mr-parent", "MR父组织", mode="MR")
        with self.assertRaises(HttpError):
            services.create_organization(
                self.user,
                OrganizationIn(group_id="cr-child", name="CR子组织", parent_id=parent["id"], mode="CR", domain="cockpit"),
            )
        with self.assertRaises(HttpError):
            self.create_repo(parent["id"], "wrong-mode-project", mode="CR")

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
    def test_missing_merge_scan_resolves_author_pl_group(self):
        """扫描落库时按 CR 作者 username 匹配 Focus 用户和启用 PL 组。"""
        author = User.objects.create(username="user06", password="secret", name="Mock Author")
        self.pl_group.members.add(author)
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        trunk = self.create_branch("master", "trunk")
        release = self.create_branch("release/1.0", "release")
        services.bind_branches_to_repositories(
            [repo["id"]],
            [trunk["id"], release["id"]],
            "append",
        )
        now = timezone.now()

        self.run_missing_scan_now(
            MissingMergeScanRunIn(
                merged_after=now - timedelta(days=1),
                merged_before=now + timedelta(days=1),
            ),
        )

        record = ComplianceMissingMergeRecord.objects.get(change_key="mock-20001-006")
        self.assertEqual(record.author_username, "user06")
        self.assertEqual(record.author_user_id, author.id)
        self.assertEqual(record.author_pl_group_id, self.pl_group.id)
        self.assertEqual(record.author_pl_group_name, self.pl_group.name)

    def test_missing_merge_unknown_author_falls_back_to_non_base_soft(self):
        """作者不存在或无启用 PL 组时，风险统一归属为非底软领域。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        pair = missing_merge_services.ScanPair(
            repository=repository,
            trunk_branch="master",
            release_branch="release/1.0",
        )

        missing_merge_services._upsert_missing_record(
            user=self.user,
            pair=pair,
            row={
                "added_lines": 1,
                "author_username": "ghost-user",
                "change_key": "unknown-author-risk",
                "change_request_iid": "90001",
                "merged_at": timezone.now(),
                "removed_lines": 0,
                "target_branch": "master",
                "title": "unknown author",
            },
        )

        record = ComplianceMissingMergeRecord.objects.get(change_key="unknown-author-risk")
        self.assertIsNone(record.author_user_id)
        self.assertIsNone(record.author_pl_group_id)
        self.assertEqual(
            record.author_pl_group_name,
            missing_merge_services.UNKNOWN_PL_GROUP_NAME,
        )

    def test_missing_merge_multiple_pl_groups_uses_sorted_first(self):
        """同一作者命中多个启用 PL 组时，按现有排序口径只取第一个。"""
        author = User.objects.create(username="multi-pl", password="secret", name="Multi PL")
        low_group = PlGroup.objects.create(
            name="低优先级PL组",
            code="low-pl",
            status=True,
            pl_user=self.pl_user,
            sort=1,
        )
        high_group = PlGroup.objects.create(
            name="高优先级PL组",
            code="high-pl",
            status=True,
            pl_user=self.pl_user,
            sort=20,
        )
        low_group.members.add(author)
        high_group.members.add(author)
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        pair = missing_merge_services.ScanPair(
            repository=repository,
            trunk_branch="master",
            release_branch="release/1.0",
        )

        missing_merge_services._upsert_missing_record(
            user=self.user,
            pair=pair,
            row={
                "added_lines": 1,
                "author_username": "multi-pl",
                "change_key": "multi-pl-risk",
                "change_request_iid": "90002",
                "merged_at": timezone.now(),
                "removed_lines": 0,
                "target_branch": "master",
                "title": "multi pl",
            },
        )

        record = ComplianceMissingMergeRecord.objects.get(change_key="multi-pl-risk")
        self.assertEqual(record.author_pl_group_id, high_group.id)
        self.assertEqual(record.author_pl_group_name, high_group.name)

    def test_missing_merge_records_filter_by_pl_group_and_unknown(self):
        """漏合风险列表支持真实 PL 组和 unknown 特殊值筛选。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        known = self.create_missing_record(
            repository,
            organization,
            author_pl_group=self.pl_group,
            author_user=self.pl_user,
            change_key="known-pl-risk",
        )
        unknown = self.create_missing_record(
            repository,
            organization,
            author_username="ghost-user",
            change_key="unknown-pl-risk",
        )

        known_page = missing_merge_services.list_missing_merge_records(
            page_size=10,
            pl_group_ids=[str(self.pl_group.id)],
        )
        unknown_page = missing_merge_services.list_missing_merge_records(
            page_size=10,
            pl_group_ids=missing_merge_services.UNKNOWN_PL_GROUP_ID,
        )

        self.assertEqual({item["id"] for item in known_page["items"]}, {str(known.id)})
        self.assertEqual({item["id"] for item in unknown_page["items"]}, {str(unknown.id)})

    def test_missing_merge_records_filter_author_by_username_or_name(self):
        """创建人筛选参数保持兼容，但支持按工号或 Focus 姓名查询。"""
        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        known = self.create_missing_record(
            repository,
            organization,
            author_user=self.pl_user,
            author_username=self.pl_user.username,
            change_key="known-author-risk",
        )
        unknown = self.create_missing_record(
            repository,
            organization,
            author_username="external-user",
            change_key="unknown-author-risk",
        )

        username_page = missing_merge_services.list_missing_merge_records(
            author_username=self.pl_user.username,
            page_size=10,
        )
        name_page = missing_merge_services.list_missing_merge_records(
            author_username=self.pl_user.name,
            page_size=10,
        )
        external_page = missing_merge_services.list_missing_merge_records(
            author_username="external-user",
            page_size=10,
        )

        self.assertEqual({item["id"] for item in username_page["items"]}, {str(known.id)})
        self.assertEqual({item["id"] for item in name_page["items"]}, {str(known.id)})
        self.assertEqual({item["id"] for item in external_page["items"]}, {str(unknown.id)})

    def test_missing_merge_pl_dashboard_uses_merged_week_and_counts_unknown(self):
        """PL 看板按主干合入周聚合，空 merged_at 只进入汇总和明细。"""
        def model_dt(year: int, month: int, day: int):
            value = timezone.make_aware(
                datetime(year, month, day, 10, 0, 0),
                timezone.get_current_timezone(),
            )
            return missing_merge_services._to_model_datetime(value)

        org = self.create_org()
        repo = self.create_repo(org["id"], "20001")
        repository = ComplianceRepository.objects.get(id=repo["id"])
        organization = ComplianceOrganization.objects.get(id=org["id"])
        self.create_missing_record(
            repository,
            organization,
            author_pl_group=self.pl_group,
            author_user=self.pl_user,
            change_key="pl-jan-open",
            detected_at=model_dt(2026, 1, 12),
            merged_at=model_dt(2026, 1, 10),
            status=MISSING_MERGE_STATUS_OPEN,
        )
        self.create_missing_record(
            repository,
            organization,
            author_pl_group=self.pl_group,
            author_user=self.pl_user,
            change_key="pl-feb-fixed",
            detected_at=model_dt(2026, 2, 12),
            merged_at=model_dt(2026, 2, 10),
            status=MISSING_MERGE_STATUS_FIXED,
        )
        self.create_missing_record(
            repository,
            organization,
            author_username="ghost-user",
            change_key="unknown-jan-ignored",
            detected_at=model_dt(2026, 1, 13),
            merged_at=model_dt(2026, 1, 11),
            status=MISSING_MERGE_STATUS_IGNORED,
        )
        missing_merged_at = self.create_missing_record(
            repository,
            organization,
            author_username="ghost-user",
            change_key="unknown-no-merged-at",
            detected_at=model_dt(2026, 2, 13),
            status=MISSING_MERGE_STATUS_OPEN,
        )
        missing_merged_at.merged_at = None
        missing_merged_at.save(update_fields=["merged_at"])

        dashboard = missing_merge_services.get_pl_dashboard(
            merged_after=model_dt(2026, 1, 1),
            merged_before=model_dt(2026, 2, 28),
        )

        self.assertIn("2026-W02", dashboard["weeks"])
        self.assertIn("2026-W07", dashboard["weeks"])
        self.assertEqual(dashboard["summary"]["total_count"], 4)
        self.assertEqual(dashboard["summary"]["open_count"], 2)
        self.assertEqual(dashboard["summary"]["fixed_count"], 1)
        self.assertEqual(dashboard["summary"]["ignored_count"], 1)
        self.assertEqual(dashboard["summary"]["missing_merged_at_count"], 1)
        trend_by_name = {item["pl_group_name"]: item["data"] for item in dashboard["trend_series"]}
        week_02_index = dashboard["weeks"].index("2026-W02")
        week_07_index = dashboard["weeks"].index("2026-W07")
        self.assertEqual(trend_by_name[self.pl_group.name][week_02_index], 1)
        self.assertEqual(trend_by_name[self.pl_group.name][week_07_index], 1)
        self.assertEqual(trend_by_name[missing_merge_services.UNKNOWN_PL_GROUP_NAME][week_02_index], 1)
        self.assertEqual(trend_by_name[missing_merge_services.UNKNOWN_PL_GROUP_NAME][week_07_index], 0)
        groups_by_name = {item["pl_group_name"]: item for item in dashboard["pl_groups"]}
        self.assertEqual(groups_by_name[self.pl_group.name]["total_count"], 2)
        self.assertEqual(
            groups_by_name[missing_merge_services.UNKNOWN_PL_GROUP_NAME]["total_count"],
            2,
        )

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
