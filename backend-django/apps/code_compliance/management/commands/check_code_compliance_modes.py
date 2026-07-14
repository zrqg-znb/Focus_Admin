from django.core.management.base import BaseCommand, CommandError
from django.db import models

from apps.code_compliance.models import ComplianceOrganization, ComplianceRepository


class Command(BaseCommand):
    help = "检查代码合规组织树与代码库的 CR/MR 模式一致性，不修改任何数据"

    def handle(self, *args, **options):
        """输出历史脏数据诊断，供上线前或初始化后人工修复。"""
        org_issues = list(
            ComplianceOrganization.objects.filter(is_deleted=False, parent__is_deleted=False)
            .exclude(mode=models.F("parent__mode"))
            .values_list("group_id", "name", "mode", "parent__group_id", "parent__mode")
        )
        repo_issues = list(
            ComplianceRepository.objects.filter(is_deleted=False, organization__is_deleted=False)
            .exclude(mode=models.F("organization__mode"))
            .values_list("project_id", "project_name", "mode", "organization__group_id", "organization__mode")
        )
        if not org_issues and not repo_issues:
            self.stdout.write(self.style.SUCCESS("代码合规 CR/MR 模式一致性检查通过"))
            return
        for group_id, name, mode, parent_group_id, parent_mode in org_issues:
            self.stderr.write(f"组织模式不一致: {name}({group_id})={mode}, 父组织 {parent_group_id}={parent_mode}")
        for project_id, name, mode, group_id, org_mode in repo_issues:
            self.stderr.write(f"代码库模式不一致: {name}({project_id})={mode}, 组织 {group_id}={org_mode}")
        raise CommandError(f"发现 {len(org_issues) + len(repo_issues)} 条 CR/MR 模式不一致数据")
