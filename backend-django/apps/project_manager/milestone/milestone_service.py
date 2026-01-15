from datetime import date, timedelta
from typing import List, Optional
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from common import fu_crud
from .milestone_model import Milestone, MilestoneQGConfig, MilestoneRiskItem, MilestoneRiskLog
from .milestone_schema import MilestoneUpdateSchema, MilestoneBoardSchema, RiskItemOut
from core.user.user_model import User


def get_milestone_board(filters: dict):
    queryset = Milestone.objects.select_related('project').prefetch_related('project__managers').filter(
        project__is_deleted=False,
        project__enable_milestone=True
    )
    
    # 模糊搜索
    keyword = filters.get('keyword')
    if keyword:
        queryset = queryset.filter(
            Q(project__name__icontains=keyword) | 
            Q(project__code__icontains=keyword)
        )
        
    project_type = filters.get('project_type')
    if project_type:
        queryset = queryset.filter(project__type=project_type)
        
    manager_id = filters.get('manager_id')
    if manager_id:
        queryset = queryset.filter(project__managers__id=manager_id)

    # 构造扁平化数据
    result = []
    for m in queryset:
        result.append(MilestoneBoardSchema(
            id=str(m.id),
            project_id=m.project.id,
            project_name=m.project.name,
            project_domain=m.project.domain,
            manager_names=[u.name or u.username for u in m.project.managers.all()],
            qg1_date=m.qg1_date,
            qg2_date=m.qg2_date,
            qg3_date=m.qg3_date,
            qg4_date=m.qg4_date,
            qg5_date=m.qg5_date,
            qg6_date=m.qg6_date,
            qg7_date=m.qg7_date,
            qg8_date=m.qg8_date,
        ))
    return result

def update_milestone(request, project_id: str, data: MilestoneUpdateSchema):
    milestone = get_object_or_404(Milestone, project_id=project_id)
    # 使用 fu_crud 更新，虽然是通过 project_id 查找的，但 fu_crud.update 需要主键
    # 这里我们直接用 ORM 更新更方便，或者先获取 ID 再调 fu_crud
    # 为了保持一致性，我们手动处理数据然后 save，或者复用 fu_crud.update
    return fu_crud.update(request, milestone.id, data.dict(exclude_unset=True), Milestone)


# --- QG Risk Logic ---

def upsert_qg_config(project_id: str, qg_name: str, target_di: Optional[float], enabled: bool):
    # Find milestone by project_id, or create if not exists (though milestone should exist for project)
    # Actually requirement says "Config from Project Page", project page usually has Project ID.
    milestone, _ = Milestone.objects.get_or_create(project_id=project_id)
    
    config, created = MilestoneQGConfig.objects.update_or_create(
        milestone=milestone,
        qg_name=qg_name,
        defaults={
            "target_di": target_di,
            "enabled": enabled
        }
    )
    return config

def get_qg_configs(project_id: str):
    # Find milestone by project_id
    try:
        milestone = Milestone.objects.get(project_id=project_id)
        return MilestoneQGConfig.objects.filter(milestone=milestone, is_deleted=False)
    except Milestone.DoesNotExist:
        return []

def list_pending_risks():
    """获取所有待处理风险，用于工作台展示"""
    qs = MilestoneRiskItem.objects.select_related(
        'config', 'config__milestone', 'config__milestone__project', 'manager'
    ).filter(
        status__in=['pending', 'confirmed'],
        is_deleted=False
    ).order_by('-record_date', 'id')
    
    result = []
    for item in qs:
        config = item.config
        milestone = config.milestone
        project = milestone.project
        
        result.append(RiskItemOut(
            id=str(item.id),
            config_id=str(config.id),
            qg_name=config.qg_name,
            milestone_id=str(milestone.id),
            project_id=str(project.id),
            project_name=project.name,
            record_date=item.record_date,
            risk_type=item.risk_type,
            description=item.description,
            status=item.status,
            manager_confirm_note=item.manager_confirm_note,
            manager_confirm_at=item.manager_confirm_at,
            manager_name=item.manager.name if item.manager else None
        ))
    return result

@transaction.atomic
def confirm_risk(risk_id: str, user: User, note: str, action: str):
    risk = get_object_or_404(MilestoneRiskItem, id=risk_id)
    
    if action == 'confirm':
        risk.status = 'confirmed'
    elif action == 'close':
        risk.status = 'closed'
    
    risk.manager_confirm_note = note
    risk.manager_confirm_at = date.today()
    risk.manager = user
    risk.save()
    
    # Log
    MilestoneRiskLog.objects.create(
        risk_item=risk,
        action=action,
        operator=user,
        note=note
    )
    return True

# --- Daily Check Logic ---

def mock_get_project_dts_issues(project_id):
    """Mock: Get open DTS issues count"""
    import random
    if random.random() > 0.7:
        return random.randint(1, 5)
    return 0

def mock_get_project_di(project_id):
    """Mock: Get current DI value"""
    import random
    return round(random.uniform(0, 100), 1)

@transaction.atomic
def check_qg_risks_daily():
    today = date.today()
    configs = MilestoneQGConfig.objects.select_related('milestone').filter(enabled=True, is_deleted=False)
    
    for config in configs:
        milestone = config.milestone
        qg_date = getattr(milestone, f"{config.qg_name.lower()}_date", None)
        
        if not qg_date:
            continue
            
        # Check if within 2 weeks before QG
        days_diff = (qg_date - today).days
        if 0 <= days_diff <= 14:
            _check_single_config(config, today)

def _check_single_config(config: MilestoneQGConfig, record_date: date):
    project_id = config.milestone.project_id
    
    # 1. Check DTS
    open_issues = mock_get_project_dts_issues(project_id)
    if open_issues > 0:
        _upsert_risk(
            config=config,
            record_date=record_date,
            risk_type='dts',
            description=f"存在 {open_issues} 个未关闭的 DTS 问题单",
            status='pending'
        )
    else:
        # Auto close if exists? Requirement says "processed day 1, reappears day 2 -> re-warn".
        # If processed (closed) day 1, and day 2 issues=0, do nothing.
        # If processed (closed) day 1, and day 2 issues>0, create new risk.
        pass

    # 2. Check DI
    # Always check DI if QG risk config is enabled, regardless of config.target_di value (which is now unused/optional)
    
    # 联动 DTS 模块：项目的 DI = 所有根节点团队的 DI 之和
    # 目标 DI = 所有根节点团队的目标 DI 之和 (从 DTS 数据表中获取)
    
    current_di, target_di_sum = mock_get_project_di_aggregation(project_id)
    
    # Risk Condition: Actual Project DI > Target Project DI (Sum from DTS)
    # 目标 DI 是不需要自己配置的这个要从dts 数据表中获取 -> We rely solely on target_di_sum
    
    if current_di > target_di_sum:
         _upsert_risk(
            config=config,
            record_date=record_date,
            risk_type='di',
            description=f"当前 DI 值 ({current_di}) 高于目标值 ({target_di_sum})",
            status='pending'
        )

def mock_get_project_di_aggregation(project_id):
    """
    Mock: Get aggregated DI values from DTS module.
    Returns: (Actual DI Sum, Target DI Sum)
    """
    import random
    # Simulate 3 root teams
    team_actuals = [random.uniform(0, 50) for _ in range(3)]
    team_targets = [random.uniform(0, 40) for _ in range(3)]
    
    return round(sum(team_actuals), 1), round(sum(team_targets), 1)

def _upsert_risk(config, record_date, risk_type, description, status):
    # Check if there is an existing OPEN risk (pending or confirmed)
    # Requirement: "If a risk item was processed (closed) on Day 1, and reappears on Day 2, it should be re-warned."
    # So we only look for *non-closed* risks to update. If all closed, create new.
    
    existing = MilestoneRiskItem.objects.filter(
        config=config,
        risk_type=risk_type,
        status__in=['pending', 'confirmed'],
        is_deleted=False
    ).first()
    
    if existing:
        # Update existing risk (e.g. update description with new numbers)
        if existing.description != description:
            existing.description = description
            existing.save(update_fields=['description'])
            
            MilestoneRiskLog.objects.create(
                risk_item=existing,
                action='update',
                note=f"自动更新: {description}"
            )
    else:
        # Create new risk
        item = MilestoneRiskItem.objects.create(
            config=config,
            record_date=record_date,
            risk_type=risk_type,
            description=description,
            status=status
        )
        MilestoneRiskLog.objects.create(
            risk_item=item,
            action='create',
            note="自动创建风险项"
        )

