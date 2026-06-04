# Generated manually for code compliance foundation data.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0002_remove_compliancerecord_missing_branches_and_more"),
        ("core", "0009_alter_permission_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceOrganization",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("group_id", models.CharField(db_index=True, help_text="公司代码库系统中的组织ID", max_length=128, unique=True, verbose_name="组织ID")),
                ("name", models.CharField(help_text="组织名", max_length=255, verbose_name="组织名")),
                ("mode", models.CharField(choices=[("CR", "CR"), ("MR", "MR")], db_index=True, default="CR", help_text="CR/MR模式", max_length=8, verbose_name="模式")),
                ("domain", models.CharField(choices=[("cockpit", "座舱"), ("vehicle", "车控")], db_index=True, default="cockpit", help_text="座舱/车控", max_length=16, verbose_name="领域")),
                ("remark", models.TextField(blank=True, help_text="备注", null=True, verbose_name="备注")),
                ("parent", models.ForeignKey(blank=True, db_constraint=False, help_text="父组织", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="code_compliance.complianceorganization", verbose_name="父组织")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规组织",
                "verbose_name_plural": "代码合规组织",
                "db_table": "compliance_organization",
                "ordering": ("sort", "name"),
                "indexes": [
                    models.Index(fields=["parent", "is_deleted"], name="cc_org_parent_deleted_idx"),
                    models.Index(fields=["domain", "mode"], name="cc_org_domain_mode_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ComplianceManagedBranch",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("branch_name", models.CharField(db_index=True, help_text="分支名称", max_length=255, verbose_name="分支名称")),
                ("created_date", models.DateField(blank=True, db_index=True, help_text="创建日期", null=True, verbose_name="创建日期")),
                ("branch_type", models.CharField(choices=[("development", "开发"), ("trunk", "主干"), ("release", "发布"), ("other", "其他")], db_index=True, default="other", help_text="开发/主干/发布/其他", max_length=32, verbose_name="分支类型")),
                ("alias", models.CharField(blank=True, default="", help_text="分支别名", max_length=255, verbose_name="分支别名")),
                ("purpose", models.TextField(blank=True, default="", help_text="分支用途", verbose_name="分支用途")),
                ("remark", models.TextField(blank=True, help_text="备注", null=True, verbose_name="备注")),
                ("domain", models.CharField(choices=[("cockpit", "座舱"), ("vehicle", "车控")], db_index=True, default="cockpit", help_text="座舱/车控", max_length=16, verbose_name="领域")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规分支主数据",
                "verbose_name_plural": "代码合规分支主数据",
                "db_table": "compliance_managed_branch",
                "ordering": ("domain", "branch_name"),
                "indexes": [
                    models.Index(fields=["domain", "branch_type"], name="cc_branch_domain_type_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("domain", "branch_name"), name="cc_branch_domain_name_uniq"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ComplianceRepository",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("project_id", models.CharField(db_index=True, help_text="公司代码库系统中的代码库ID", max_length=128, unique=True, verbose_name="代码库ID")),
                ("project_name", models.CharField(db_index=True, help_text="代码库名", max_length=255, verbose_name="代码库名")),
                ("project_url", models.CharField(blank=True, default="", help_text="代码库URL", max_length=1024, verbose_name="代码库URL")),
                ("mode", models.CharField(choices=[("CR", "CR"), ("MR", "MR")], db_index=True, default="CR", help_text="CR/MR模式", max_length=8, verbose_name="模式")),
                ("repo_type", models.CharField(blank=True, db_index=True, default="", help_text="core 字典 code_compliance_repo_type 的字典项 value", max_length=100, verbose_name="代码仓类型")),
                ("domain", models.CharField(choices=[("cockpit", "座舱"), ("vehicle", "车控")], db_index=True, default="cockpit", help_text="座舱/车控", max_length=16, verbose_name="领域")),
                ("remark", models.TextField(blank=True, help_text="备注", null=True, verbose_name="备注")),
                ("organization", models.ForeignKey(db_constraint=False, help_text="所属组织", on_delete=django.db.models.deletion.PROTECT, related_name="repositories", to="code_compliance.complianceorganization", verbose_name="所属组织")),
                ("responsibility_groups", models.ManyToManyField(blank=True, db_constraint=False, help_text="责任PL资源组", related_name="compliance_repositories", to="core.plgroup", verbose_name="责任领域")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码合规代码库",
                "verbose_name_plural": "代码合规代码库",
                "db_table": "compliance_repository",
                "ordering": ("project_name",),
                "indexes": [
                    models.Index(fields=["organization", "is_deleted"], name="cc_repo_org_deleted_idx"),
                    models.Index(fields=["domain", "mode"], name="cc_repo_domain_mode_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ComplianceRepositoryBranch",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("branch", models.ForeignKey(db_constraint=False, help_text="分支", on_delete=django.db.models.deletion.CASCADE, related_name="repository_links", to="code_compliance.compliancemanagedbranch", verbose_name="分支")),
                ("repository", models.ForeignKey(db_constraint=False, help_text="代码库", on_delete=django.db.models.deletion.CASCADE, related_name="branch_links", to="code_compliance.compliancerepository", verbose_name="代码库")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
            ],
            options={
                "verbose_name": "代码库分支绑定",
                "verbose_name_plural": "代码库分支绑定",
                "db_table": "compliance_repository_branch",
                "ordering": ("repository__project_name", "branch__branch_name"),
                "indexes": [
                    models.Index(fields=["repository", "is_deleted"], name="cc_rb_repo_deleted_idx"),
                    models.Index(fields=["branch", "is_deleted"], name="cc_rb_branch_deleted_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("repository", "branch"), name="cc_repo_branch_uniq"),
                ],
            },
        ),
        migrations.AddField(
            model_name="compliancemanagedbranch",
            name="repositories",
            field=models.ManyToManyField(blank=True, related_name="managed_branches", through="code_compliance.ComplianceRepositoryBranch", to="code_compliance.compliancerepository", verbose_name="关联代码库"),
        ),
    ]
