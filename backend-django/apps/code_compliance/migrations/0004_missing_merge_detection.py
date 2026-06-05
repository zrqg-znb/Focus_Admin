# Generated manually for code compliance missing merge detection.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0003_compliance_foundation_models"),
        ("core", "0009_alter_permission_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceMissingMergeScanTask",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("trigger_type", models.CharField(choices=[("manual", "手动"), ("scheduled", "定时")], db_index=True, default="manual", help_text="手动/定时", max_length=32, verbose_name="触发方式")),
                ("status", models.CharField(choices=[("pending", "待执行"), ("running", "执行中"), ("success", "成功"), ("failed", "失败")], db_index=True, default="pending", help_text="待执行/执行中/成功/失败", max_length=32, verbose_name="任务状态")),
                ("merged_after", models.DateTimeField(db_index=True, help_text="数据湖 merged_after", verbose_name="合入开始时间")),
                ("merged_before", models.DateTimeField(db_index=True, help_text="数据湖 merged_before", verbose_name="合入结束时间")),
                ("filter_payload", models.JSONField(blank=True, default=dict, help_text="手动或定时任务的组织/代码库筛选条件", verbose_name="筛选条件")),
                ("started_at", models.DateTimeField(blank=True, help_text="开始时间", null=True, verbose_name="开始时间")),
                ("finished_at", models.DateTimeField(blank=True, help_text="结束时间", null=True, verbose_name="结束时间")),
                ("scanned_organization_count", models.IntegerField(default=0, help_text="扫描组织数", verbose_name="扫描组织数")),
                ("scanned_repository_count", models.IntegerField(default=0, help_text="扫描代码库数", verbose_name="扫描代码库数")),
                ("scanned_branch_pair_count", models.IntegerField(default=0, help_text="扫描分支对数", verbose_name="扫描分支对数")),
                ("detected_count", models.IntegerField(default=0, help_text="本次识别漏合风险数", verbose_name="识别风险数")),
                ("created_count", models.IntegerField(default=0, help_text="本次新增风险数", verbose_name="新增风险数")),
                ("updated_count", models.IntegerField(default=0, help_text="本次更新风险数", verbose_name="更新风险数")),
                ("fixed_count", models.IntegerField(default=0, help_text="本次自动标记已补合数量", verbose_name="自动补合数")),
                ("error_message", models.TextField(blank=True, default="", help_text="失败错误信息", verbose_name="错误信息")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规漏合检测任务",
                "verbose_name_plural": "代码合规漏合检测任务",
                "db_table": "compliance_missing_merge_scan_task",
                "ordering": ("-sys_create_datetime",),
                "indexes": [
                    models.Index(fields=["status", "trigger_type"], name="cc_mm_task_status_trigger_idx"),
                    models.Index(fields=["merged_after", "merged_before"], name="cc_mm_task_time_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ComplianceMissingMergeRecord",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("organization_group_id", models.CharField(db_index=True, help_text="公司代码库系统组织ID快照", max_length=128, verbose_name="组织ID快照")),
                ("organization_name", models.CharField(blank=True, default="", help_text="组织名快照", max_length=255, verbose_name="组织名快照")),
                ("repository_project_id", models.CharField(db_index=True, help_text="公司代码库系统代码库ID快照", max_length=128, verbose_name="代码库ID快照")),
                ("repository_name", models.CharField(blank=True, default="", help_text="代码库名快照", max_length=255, verbose_name="代码库名快照")),
                ("project_id", models.CharField(db_index=True, help_text="数据湖查询使用的 project_id", max_length=128, verbose_name="项目ID")),
                ("trunk_branch", models.CharField(db_index=True, help_text="主干分支名称", max_length=255, verbose_name="主干分支")),
                ("release_branch", models.CharField(db_index=True, help_text="发布分支名称", max_length=255, verbose_name="发布分支")),
                ("change_request_iid", models.CharField(blank=True, default="", help_text="CR内部ID", max_length=128, verbose_name="CR内部ID")),
                ("change_key", models.CharField(db_index=True, help_text="CR全局哈希标识", max_length=255, verbose_name="CR全局标识")),
                ("title", models.CharField(blank=True, default="", help_text="CR标题", max_length=500, verbose_name="CR标题")),
                ("description", models.TextField(blank=True, default="", help_text="CR描述", verbose_name="CR描述")),
                ("web_url", models.CharField(blank=True, default="", help_text="CR访问链接", max_length=1024, verbose_name="CR链接")),
                ("added_lines", models.IntegerField(default=0, help_text="新增代码行数", verbose_name="新增行数")),
                ("removed_lines", models.IntegerField(default=0, help_text="删除代码行数", verbose_name="删除行数")),
                ("merged_at", models.DateTimeField(blank=True, db_index=True, help_text="CR合入主干时间", null=True, verbose_name="主干合入时间")),
                ("target_branch", models.CharField(blank=True, default="", help_text="数据湖返回的目标合入分支", max_length=255, verbose_name="目标合入分支")),
                ("author_username", models.CharField(blank=True, db_index=True, default="", help_text="CR创建人Focus系统用户名", max_length=255, verbose_name="创建人用户名")),
                ("detected_at", models.DateTimeField(db_index=True, help_text="最近一次识别为漏合的时间", verbose_name="漏合识别时间")),
                ("status", models.CharField(choices=[("open", "未处理"), ("fixed", "已补合"), ("ignored", "已忽略")], db_index=True, default="open", help_text="未处理/已补合/已忽略", max_length=32, verbose_name="处理状态")),
                ("handled_at", models.DateTimeField(blank=True, help_text="最近一次处理时间", null=True, verbose_name="处理时间")),
                ("handle_remark", models.TextField(blank=True, default="", help_text="处理备注", verbose_name="处理备注")),
                ("handled_by", models.ForeignKey(blank=True, db_constraint=False, help_text="最近一次处理人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="handled_missing_merge_records", to="core.user", verbose_name="处理人")),
                ("organization", models.ForeignKey(blank=True, db_constraint=False, help_text="识别风险时对应的组织", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="missing_merge_records", to="code_compliance.complianceorganization", verbose_name="组织")),
                ("repository", models.ForeignKey(blank=True, db_constraint=False, help_text="识别风险时对应的代码库", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="missing_merge_records", to="code_compliance.compliancerepository", verbose_name="代码库")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规漏合风险",
                "verbose_name_plural": "代码合规漏合风险",
                "db_table": "compliance_missing_merge_record",
                "ordering": ("-detected_at", "-merged_at"),
                "indexes": [
                    models.Index(fields=["organization", "status"], name="cc_mm_org_status_idx"),
                    models.Index(fields=["repository", "status"], name="cc_mm_repo_status_idx"),
                    models.Index(fields=["trunk_branch", "release_branch"], name="cc_mm_branch_pair_idx"),
                    models.Index(fields=["detected_at", "status"], name="cc_mm_detect_status_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("repository", "trunk_branch", "release_branch", "change_key"), name="cc_missing_merge_record_uniq"),
                ],
            },
        ),
    ]
