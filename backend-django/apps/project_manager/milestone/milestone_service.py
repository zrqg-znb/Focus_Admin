from datetime import date, timedelta
from typing import List, Optional
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from common import fu_crud
from .milestone_model import Milestone, MilestoneQGConfig, MilestoneRiskItem, MilestoneRiskLog
from .milestone_schema import MilestoneUpdateSchema, MilestoneBoardSchema, RiskItemOut, RiskLogOut
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
    
    # 批量获取风险状态
    # Structure: { project_id: { 'QG1': 'high', 'QG2': 'medium' } }
    risk_map = {}
    if queryset.exists():
        # Get all milestones IDs
        milestone_ids = [m.id for m in queryset]
        
        # Query active risks for these milestones
        active_risks = MilestoneRiskItem.objects.filter(
            config__milestone_id__in=milestone_ids,
            status__in=['pending', 'confirmed'],
            is_deleted=False
        ).select_related('config', 'config__milestone')
        
        for risk in active_risks:
            ms_id = risk.config.milestone.id
            qg_name = risk.config.qg_name # e.g. "QG1"
            
            if ms_id not in risk_map:
                risk_map[ms_id] = {}
            
            # Populate detailed risk info
            risk_map[ms_id][qg_name] = {
                "id": str(risk.id),
                "level": "medium" if risk.status == 'confirmed' else "high",
                "description": risk.description,
                "status": risk.status
            }

    for m in queryset:
        # Inject risk info dynamically
        risks = risk_map.get(m.id, {})
        
        item_dict = {
            "id": str(m.id),
            "project_id": m.project.id,
            "project_name": m.project.name,
            "project_domain": m.project.domain,
            "manager_names": [u.name or u.username for u in m.project.managers.all()],
            "qg1_date": m.qg1_date,
            "qg2_date": m.qg2_date,
            "qg3_date": m.qg3_date,
            "qg4_date": m.qg4_date,
            "qg5_date": m.qg5_date,
            "qg6_date": m.qg6_date,
            "qg7_date": m.qg7_date,
            "qg8_date": m.qg8_date,
            "risks": risks
        }
        result.append(item_dict)
        
    return result

def update_milestone(request, project_id: str, data: MilestoneUpdateSchema):
    milestone = get_object_or_404(Milestone, project_id=project_id)
    # 使用 fu_crud 更新，虽然是通过 project_id 查找的，但 fu_crud.update 需要主键
    # 这里我们直接用 ORM 更新更方便，或者先获取 ID 再调 fu_crud
    # 为了保持一致性，我们手动处理数据然后 save，或者复用 fu_crud.update
    return fu_crud.update(request, milestone.id, data.dict(exclude_unset=True), Milestone)


# --- QG Risk Logic ---

def upsert_qg_config(project_id: str, qg_name: str, target_di: Optional[float], enabled: bool, is_delayed: bool = False):
    # Find milestone by project_id, or create if not exists (though milestone should exist for project)
    # Actually requirement says "Config from Project Page", project page usually has Project ID.
    milestone, _ = Milestone.objects.get_or_create(project_id=project_id)
    
    config, created = MilestoneQGConfig.objects.update_or_create(
        milestone=milestone,
        qg_name=qg_name,
        defaults={
            "target_di": target_di,
            "enabled": enabled,
            "is_delayed": is_delayed
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

def list_pending_risks(request=None, scope: str = 'all'):
    """获取所有待处理风险，用于工作台展示"""
    qs = MilestoneRiskItem.objects.select_related(
        'config', 'config__milestone', 'config__milestone__project', 'manager'
    ).filter(
        status__in=['pending', 'confirmed'],
        is_deleted=False
    )

    if scope == 'favorites' and request and request.auth:
        qs = qs.filter(config__milestone__project__favorited_by=request.auth)

    qs = qs.order_by('-record_date', 'id')
    
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

def get_project_risks(project_id: str):
    """获取项目的所有风险（包括历史记录）"""
    qs = MilestoneRiskItem.objects.select_related(
        'config', 'config__milestone', 'config__milestone__project', 'manager'
    ).filter(
        config__milestone__project_id=project_id,
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

def get_risk_logs(risk_id: str):
    """获取风险的处理日志"""
    logs = MilestoneRiskLog.objects.select_related('operator').filter(
        risk_item_id=risk_id,
        is_deleted=False
    ).order_by('-sys_create_datetime')
    
    result = []
    for log in logs:
        result.append(RiskLogOut(
            id=str(log.id),
            action=log.get_action_display(),
            operator_name=log.operator.name if log.operator else "系统",
            note=log.note,
            create_time=log.sys_create_datetime
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

from apps.project_manager.dts.dts_model import DtsTeam, DtsData

def get_project_latest_dts_data(project_id):
    """
    Get aggregated DI and open issues count from DTS module.
    Returns: (Actual DI Sum, Target DI Sum, Total Open Issues)
    """
    # Get all teams for the project
    teams = DtsTeam.objects.filter(project_id=project_id)
    
    total_di = 0.0
    total_target_di = 0.0
    total_issues = 0
    
    for team in teams:
        # Get latest data record for each team
        latest_data = DtsData.objects.filter(team=team).order_by('-record_date').first()
        if latest_data:
            total_di += latest_data.di
            total_target_di += (latest_data.target_di or 0.0)
            
            # Sum all issue types as open issues
            # Assuming these fields represent current open counts
            total_issues += (
                latest_data.fatal_num + 
                latest_data.major_num + 
                latest_data.minor_num + 
                latest_data.suggestion_num
            )
            
    return round(total_di, 1), round(total_target_di, 1), total_issues

@transaction.atomic
def check_qg_risks_daily():
    today = date.today()
    configs = MilestoneQGConfig.objects.select_related('milestone').filter(enabled=True, is_deleted=False)
    
    for config in configs:
        milestone = config.milestone
        qg_date = getattr(milestone, f"{config.qg_name.lower()}_date", None)
        
        should_check = False
        
        # Check if is_delayed is True, check anyway
        if config.is_delayed:
             should_check = True
        elif qg_date:
            # Check if within 2 weeks before QG OR past QG
            days_diff = (qg_date - today).days
            # If QG is in future 30 days or past 30 days, we check.
            if -30 <= days_diff <= 30: 
                should_check = True

        if should_check: 
            _check_single_config(config, today)

def _check_single_config(config: MilestoneQGConfig, record_date: date):
    project_id = config.milestone.project_id
    
    # Fetch real data from DTS module
    current_di, target_di_sum, open_issues = get_project_latest_dts_data(project_id)
    
    # 1. Check DTS Issues (REMOVED as per user request)
    # if open_issues > 0:
    #     _upsert_risk(...)
    
    # 2. Check DI
    if current_di > target_di_sum:
         _upsert_risk(
            config=config,
            record_date=record_date,
            risk_type='di',
            description=f"当前 DI 值 ({current_di}) 高于目标值 ({target_di_sum})",
            status='pending'
        )

def _upsert_risk(config, record_date, risk_type, description, status):
    # 查找该配置下同类型的最新一条风险记录（无论状态如何）
    # 按照 ID 倒序排列，取最新的一条
    latest_risk = MilestoneRiskItem.objects.filter(
        config=config,
        risk_type=risk_type,
        is_deleted=False
    ).order_by('-id').first()
    
    if latest_risk:
        updates = []
        should_log = False
        log_action = 'update'
        log_note = ""

        # 情况1: 已关闭 -> 重新打开
        if latest_risk.status == 'closed':
            latest_risk.status = 'pending'
            updates.append('status')
            latest_risk.record_date = record_date # 更新为最新的检测日期
            updates.append('record_date')
            
            should_log = True
            log_action = 'update'
            log_note = f"风险复发/未解决 (DI: {description})，系统自动重新打开"
            
            # 如果描述变了，也更新描述
            if latest_risk.description != description:
                latest_risk.description = description
                updates.append('description')

        # 情况2: 待处理/已确认 -> 更新信息
        else:
            if latest_risk.description != description:
                latest_risk.description = description
                updates.append('description')
                
                # 仅当只更新描述时记录日志（如果是重置状态，下面会单独处理）
                if latest_risk.status != 'confirmed':
                     MilestoneRiskLog.objects.create(
                        risk_item=latest_risk,
                        action='update',
                        note=f"自动更新: {description}"
                    )

            # If status is 'confirmed' (Warning), reset to 'pending' (Error) because risk persists
            if latest_risk.status == 'confirmed':
                latest_risk.status = 'pending'
                updates.append('status')
                
                MilestoneRiskLog.objects.create(
                    risk_item=latest_risk,
                    action='update', # Use 'update' but note it's a reset
                    note="风险持续存在，重置为待处理状态"
                )
        
        if updates:
             latest_risk.save(update_fields=updates)
             if should_log:
                 MilestoneRiskLog.objects.create(
                    risk_item=latest_risk,
                    action=log_action,
                    note=log_note
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
