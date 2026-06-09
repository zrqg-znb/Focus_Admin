# Generated manually for code compliance missing merge PL ownership.

import django.db.models.deletion
from django.db import migrations, models


UNKNOWN_PL_GROUP_NAME = "非底软领域"


def _clean_text(value):
    """迁移中使用的轻量字符串清洗，避免依赖运行期 service。"""
    if value is None:
        return ""
    return str(value).strip()


def _load_author_mapping(apps):
    """按 username 批量加载 Focus 用户和启用 PL 组归属。"""
    Record = apps.get_model("code_compliance", "ComplianceMissingMergeRecord")
    User = apps.get_model("core", "User")
    PlGroup = apps.get_model("core", "PlGroup")

    usernames = {
        _clean_text(value)
        for value in Record.objects.filter(is_deleted=False).values_list("author_username", flat=True)
        if _clean_text(value)
    }
    users = {
        _clean_text(row["username"]): row
        for row in User.objects.filter(username__in=usernames).values("id", "username", "name")
    }

    pl_groups = {}
    rows = (
        PlGroup.objects.filter(status=True, members__username__in=usernames)
        .values("id", "name", "sort", "members__username")
        .order_by("-sort", "name", "id")
    )
    for row in rows:
        username = _clean_text(row.get("members__username"))
        if username and username not in pl_groups:
            pl_groups[username] = row
    return users, pl_groups


def backfill_author_pl_group(apps, schema_editor):
    """为已有漏合记录补齐创建人用户和 PL 组归属快照。"""
    Record = apps.get_model("code_compliance", "ComplianceMissingMergeRecord")
    users, pl_groups = _load_author_mapping(apps)

    update_fields = [
        "author_user_id",
        "author_user_name",
        "author_pl_group_id",
        "author_pl_group_name",
    ]
    batch = []
    for record in Record.objects.filter(is_deleted=False).iterator():
        username = _clean_text(record.author_username)
        user = users.get(username)
        group = pl_groups.get(username)

        record.author_user_id = user["id"] if user else None
        record.author_user_name = (
            (_clean_text(user.get("name")) or _clean_text(user.get("username")))
            if user
            else ""
        )
        record.author_pl_group_id = group["id"] if group else None
        record.author_pl_group_name = _clean_text(group.get("name")) if group else UNKNOWN_PL_GROUP_NAME
        batch.append(record)
        if len(batch) >= 500:
            Record.objects.bulk_update(batch, update_fields)
            batch = []

    if batch:
        Record.objects.bulk_update(batch, update_fields)


def noop_reverse(apps, schema_editor):
    """反向迁移删除字段即可，无需恢复快照。"""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0005_missing_merge_operation_log"),
        ("core", "0009_alter_permission_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="compliancemissingmergerecord",
            name="author_user",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="按 CR 创建人 username 匹配到的 Focus 用户",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="authored_missing_merge_records",
                to="core.user",
                verbose_name="创建人用户",
            ),
        ),
        migrations.AddField(
            model_name="compliancemissingmergerecord",
            name="author_user_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="识别风险时匹配到的 Focus 用户姓名快照",
                max_length=255,
                verbose_name="创建人姓名快照",
            ),
        ),
        migrations.AddField(
            model_name="compliancemissingmergerecord",
            name="author_pl_group",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="按创建人所属 PL 资源组自动识别的归属",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="missing_merge_records",
                to="core.plgroup",
                verbose_name="创建人PL组",
            ),
        ),
        migrations.AddField(
            model_name="compliancemissingmergerecord",
            name="author_pl_group_name",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="创建人所属 PL 资源组名称快照；未识别时为非底软领域",
                max_length=255,
                verbose_name="创建人PL组快照",
            ),
        ),
        migrations.AddIndex(
            model_name="compliancemissingmergerecord",
            index=models.Index(fields=["author_pl_group", "status"], name="cc_mm_pl_status_idx"),
        ),
        migrations.RunPython(backfill_author_pl_group, noop_reverse),
    ]
