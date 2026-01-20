from datetime import date
from django.db import transaction
from apps.project_manager.project.project_model import Project
from .dts_model import DtsTeam, DtsData
from .dts_schema import (
    DtsDashboardSchema, 
    DtsTeamSchema, 
    DtsDataSchema, 
    DtsProjectOverviewSchema,
    DtsDefectListResponseSchema
)

def get_mock_dts_data(root_team_name):
    """
    根据传入的根团队名称，返回该团队的 mock 数据（树结构）。
    在真实场景中，这里会根据 ws_id 和 root_team_name 去调用中台接口。
    """
    if "leaf" in root_team_name.lower():
        # Case 1: Root only (no children)
        return {
            "di_team": root_team_name,
            "di": 5.0,
            "target_di": 4.0,
            "today_in_di": 2.0,
            "today_out_di": 1.1,
            "solve_rate": "96%",
            "critical_solve_rate": "71%",
            "suggestion_num": 2,
            "major_num": 1,
            "minor_num": 1,
            "fatal_num": 1,
            "children": []
        }
    
    # Case 2: Multi-level tree
    return {
        "di_team": root_team_name,
        "di": 5.0,
        "target_di": 4.0,
        "today_in_di": 2.0,
        "today_out_di": 1.1,
        "solve_rate": "96%",
        "critical_solve_rate": "71%",
        "suggestion_num": 2,
        "major_num": 1,
        "minor_num": 1,
        "fatal_num": 1,
        "children": [
            {
                "di_team": f"{root_team_name}_L1_Child1",
                "di": 5.0,
                "target_di": 4.0,
                "today_in_di": 2.0,
                "today_out_di": 1.1,
                "solve_rate": "96%",
                "critical_solve_rate": "71%",
                "suggestion_num": 2,
                "major_num": 1,
                "minor_num": 1,
                "fatal_num": 1,
                "children": [
                     {
                        "di_team": f"{root_team_name}_L2_GrandChild1",
                        "di": 5.0,
                        "target_di": 4.0,
                        "today_in_di": 1.0,
                        "today_out_di": 0.5,
                        "solve_rate": "98%",
                        "critical_solve_rate": "80%",
                        "suggestion_num": 1,
                        "major_num": 0,
                        "minor_num": 1,
                        "fatal_num": 0,
                    }
                ]
            },
            {
                "di_team": f"{root_team_name}_L1_Child2",
                "di": 5.0,
                "target_di": 4.0,
                "today_in_di": 2.0,
                "today_out_di": 1.1,
                "solve_rate": "96%",
                "critical_solve_rate": "71%",
                "suggestion_num": 2,
                "major_num": 1,
                "minor_num": 1,
                "fatal_num": 1,
                # Leaf node
            }
        ]
    }

@transaction.atomic
def sync_project_dts(project: Project):
    if not project.enable_dts or not project.ws_id or not project.di_teams:
        return
    
    today = date.today()
    
    # 获取项目配置的根团队列表
    # di_teams 是一个列表，例如 ["TeamA", "TeamB"]
    root_teams = project.di_teams if isinstance(project.di_teams, list) else []

    def process_node(node_data, parent_team=None):
        team_name = node_data.get("di_team")
        if not team_name:
            return

        # Find or create team
        team, _ = DtsTeam.objects.update_or_create(
            project=project,
            team_name=team_name,
            defaults={'parent_team': parent_team}
        )
        
        # Save Data
        DtsData.objects.update_or_create(
            team=team,
            record_date=today,
            defaults={
                "di": node_data.get("di", 0),
                "target_di": node_data.get("target_di", 0),
                "today_in_di": node_data.get("today_in_di", 0),
                "today_out_di": node_data.get("today_out_di", 0),
                "solve_rate": node_data.get("solve_rate", "0%"),
                "critical_solve_rate": node_data.get("critical_solve_rate", "0%"),
                "suggestion_num": node_data.get("suggestion_num", 0),
                "minor_num": node_data.get("minor_num", 0),
                "major_num": node_data.get("major_num", 0),
                "fatal_num": node_data.get("fatal_num", 0),
            }
        )
        
        # Process children
        children = node_data.get("children", [])
        if children:
            for child in children:
                process_node(child, parent_team=team)

    # 针对每个配置的根团队，分别获取数据并处理
    for team_name in root_teams:
        # In a real scenario: data = fetch_from_middleware(project.ws_id, team_name)
        data = get_mock_dts_data(team_name)
        process_node(data, parent_team=None)

def get_dts_dashboard(project_id: str) -> DtsDashboardSchema:
    project = Project.objects.get(id=project_id)
    
    # Get all teams for the project
    teams = DtsTeam.objects.filter(project=project).prefetch_related('data')
    
    # Helper to build tree
    def build_tree(parent_id=None):
        nodes = []
        for team in teams:
            if team.parent_team_id == parent_id:
                # Get latest data
                latest_data_obj = team.data.order_by('-record_date').first()
                latest_data = None
                if latest_data_obj:
                    latest_data = DtsDataSchema(
                        di=latest_data_obj.di,
                        target_di=latest_data_obj.target_di,
                        today_in_di=latest_data_obj.today_in_di,
                        today_out_di=latest_data_obj.today_out_di,
                        solve_rate=latest_data_obj.solve_rate,
                        critical_solve_rate=latest_data_obj.critical_solve_rate,
                        suggestion_num=latest_data_obj.suggestion_num,
                        minor_num=latest_data_obj.minor_num,
                        major_num=latest_data_obj.major_num,
                        fatal_num=latest_data_obj.fatal_num
                    )
                
                node = DtsTeamSchema(
                    id=str(team.id),
                    team_name=team.team_name,
                    latest_data=latest_data,
                    children=build_tree(team.id)
                )
                nodes.append(node)
        return nodes

    root_nodes = build_tree(None)
    
    return DtsDashboardSchema(
        project_id=str(project.id),
        root_teams=root_nodes
    )

def get_dts_overview() -> list[DtsProjectOverviewSchema]:
    projects = Project.objects.filter(enable_dts=True, is_deleted=False)
    result = []
    today = date.today()
    
    for p in projects:
        # Check if any data exists for today
        # Efficient check: are there any DtsData objects for this project's teams today?
        has_data = DtsData.objects.filter(team__project=p, record_date=today).exists()
        
        # Count root teams (teams with no parent)
        root_count = DtsTeam.objects.filter(project=p, parent_team__isnull=True).count()
        
        managers = ",".join([m.name for m in p.managers.all()])
        
        result.append(DtsProjectOverviewSchema(
            project_id=str(p.id),
            project_name=p.name,
            project_domain=p.domain,
            project_type=p.type,
            project_managers=managers,
            ws_id=p.ws_id or "",
            root_teams_count=root_count,
            has_data_today=has_data
        ))
    return result

def get_mock_dts_details(project_id: str, page: int, page_size: int) -> DtsDefectListResponseSchema:
    # Mock data as requested
    base_data = [
         { 
             "defectNo": "DTS235689542", 
             "brief": "问题单简洁", 
             "severity": "一般", 
             "currentTeam": "", 
             "currentHandler": "当前处理人，对应用户", 
             "currentStageStayDay": 3, 
             "progress": "【2026/01/07】【张瑞卿】soc 改 skew 时钟和数据相位差值，待验证\n" 
         }, 
         { 
             "defectNo": "DTS235689543", 
             "brief": "问题单简洁2", 
             "severity": "严重", 
             "currentTeam": "Backend", 
             "currentHandler": "UserB", 
             "currentStageStayDay": 5, 
             "progress": "Pending fix" 
         }
    ]
    
    # Generate mock data
    full_list = base_data * 15 # 30 items
    total = len(full_list)
    
    start = (page - 1) * page_size
    end = start + page_size
    page_items = full_list[start:end]
    
    return {
        "pageResult": {
            "pageNo": page,
            "pageSize": page_size,
            "total": total,
            "currentPageNo": page,
            "npage": end < total
        },
        "dataList": page_items
    }
