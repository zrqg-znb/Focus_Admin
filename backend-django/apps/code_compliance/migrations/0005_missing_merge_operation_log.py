# Generated manually for code compliance missing merge operation history.

import uuid

import django.db.models.deletion
from django.db import migrations, models


def backfill_operation_logs(apps, schema_editor):
    """为迁移前已有漏合风险补齐基础操作历史。"""
    Record = apps.get_model("code_compliance", "ComplianceMissingMergeRecord")
    OperationLog = apps.get_model("code_compliance", "ComplianceMissingMergeOperationLog")
    User = apps.get_model("core", "User")

    users = {
        str(user.id): user
        for user in User.objects.filter(
            id__in=Record.objects.exclude(handled_by_id__isnull=True).values_list("handled_by_id", flat=True)
        )
    }

    logs = []
    for record in Record.objects.filter(is_deleted=False).iterator():
        detected_at = record.detected_at or record.sys_create_datetime
        logs.append(
            OperationLog(
                record_id=record.id,
                operation_type="detected",
                source="system",
                from_status="",
                to_status="open",
                operator_name="系统",
                remark="系统首次自动检测到漏合风险",
                operated_at=detected_at,
                sys_create_datetime=detected_at,
                sys_update_datetime=detected_at,
            )
        )

        remark = (record.handle_remark or "").strip()
        if not remark and not record.handled_at:
            continue

        is_auto_closed = record.status == "fixed" and ("系统" in remark or "自动" in remark)
        operation_type = "auto_closed" if is_auto_closed else "manual_handle"
        source = "system" if is_auto_closed else "manual"
        operator = None if is_auto_closed else users.get(str(record.handled_by_id or ""))
        operator_name = "系统"
        if operator is not None:
            operator_name = getattr(operator, "name", "") or getattr(operator, "username", "") or "人工处理"
        elif not is_auto_closed and record.handled_by_id:
            operator_name = "人工处理"

        operated_at = record.handled_at or record.sys_update_datetime or detected_at
        logs.append(
            OperationLog(
                record_id=record.id,
                operation_type=operation_type,
                source=source,
                from_status="open",
                to_status=record.status,
                operator_id=getattr(operator, "id", None),
                operator_name=operator_name,
                remark=remark or "迁移补齐最近一次处理记录",
                operated_at=operated_at,
                sys_create_datetime=operated_at,
                sys_update_datetime=operated_at,
            )
        )

    OperationLog.objects.bulk_create(logs, batch_size=500)


def noop_reverse(apps, schema_editor):
    """反向迁移删除模型时不需要额外处理历史数据。"""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0004_missing_merge_detection"),
        ("core", "0009_alter_permission_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceMissingMergeOperationLog",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("operation_type", models.CharField(choices=[("detected", "首次自动检测"), ("manual_handle", "人工处理"), ("auto_closed", "自动闭环"), ("reopened", "重新检测为待处理")], db_index=True, help_text="首次自动检测/人工处理/自动闭环/重新检测", max_length=32, verbose_name="操作类型")),
                ("source", models.CharField(choices=[("system", "系统"), ("manual", "人工")], db_index=True, default="system", help_text="系统/人工", max_length=16, verbose_name="操作来源")),
                ("from_status", models.CharField(blank=True, default="", help_text="操作前处理状态", max_length=32, verbose_name="变更前状态")),
                ("to_status", models.CharField(blank=True, default="", help_text="操作后处理状态", max_length=32, verbose_name="变更后状态")),
                ("operator_name", models.CharField(blank=True, default="", help_text="操作发生时的人名快照", max_length=255, verbose_name="操作人快照")),
                ("remark", models.TextField(blank=True, default="", help_text="系统自动备注或人工填写备注", verbose_name="操作备注")),
                ("operated_at", models.DateTimeField(db_index=True, help_text="操作发生时间", verbose_name="操作时间")),
                ("operator", models.ForeignKey(blank=True, db_constraint=False, help_text="人工操作人；系统操作为空", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="missing_merge_operation_logs", to="core.user", verbose_name="操作人")),
                ("record", models.ForeignKey(db_constraint=False, help_text="关联漏合风险记录", on_delete=django.db.models.deletion.CASCADE, related_name="operation_logs", to="code_compliance.compliancemissingmergerecord", verbose_name="漏合风险")),
                ("scan_task", models.ForeignKey(blank=True, db_constraint=False, help_text="触发本次系统操作的扫描任务", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="operation_logs", to="code_compliance.compliancemissingmergescantask", verbose_name="扫描任务")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规漏合风险操作历史",
                "verbose_name_plural": "代码合规漏合风险操作历史",
                "db_table": "compliance_missing_merge_operation_log",
                "ordering": ("-operated_at", "-sys_create_datetime"),
                "indexes": [
                    models.Index(fields=["record", "operated_at"], name="cc_mm_log_record_time_idx"),
                    models.Index(fields=["operation_type", "source"], name="cc_mm_log_type_source_idx"),
                ],
            },
        ),
        migrations.RunPython(backfill_operation_logs, noop_reverse),
    ]
