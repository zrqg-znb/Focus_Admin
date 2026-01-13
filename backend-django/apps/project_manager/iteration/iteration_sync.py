from datetime import date, timedelta
import random
from django.utils import timezone
from .iteration_model import Iteration, IterationMetric
from apps.project_manager.project.project_model import Project

class DataPlatformMock:
    @staticmethod
    def get_iterations(design_id: str, sub_teams: list):
        """
        模拟从数据中台获取项目的所有迭代期
        """
        # 基于当前日期生成过去、现在和未来的几个迭代
        today = date.today()
        base_start = today - timedelta(days=60)
        
        iterations = []
        for i in range(5):
            start = base_start + timedelta(days=i*30)
            end = start + timedelta(days=29)
            code = f"{design_id}-IT-{i+1:02d}"
            name = f"迭代-{code}"
            
            iterations.append({
                "name": name,
                "code": code,
                "start_date": start,
                "end_date": end
            })
        return iterations

    @staticmethod
    def get_iteration_metrics(iteration_code: str):
        """
        模拟获取某个迭代期的指标数据
        """
        # Generate random base numbers
        sr_num = random.randint(10, 50)
        dr_num = random.randint(20, 100)
        ar_num = random.randint(15, 80)
        
        # Breakdown metrics
        need_break_sr_num = int(sr_num * random.uniform(0.8, 1.0))
        need_break_but_un_break_sr_num = int(need_break_sr_num * random.uniform(0.0, 0.3))
        
        need_break_dr_num = int(dr_num * random.uniform(0.8, 1.0))
        need_break_but_un_break_dr_num = int(need_break_dr_num * random.uniform(0.0, 0.3))
        
        # Workload metrics
        workload_man_dr_count = int(dr_num * random.uniform(0.9, 1.0))
        workload_loc_dr_count = int(dr_num * random.uniform(0.9, 1.0))
        workload_man_ar_count = int(ar_num * random.uniform(0.9, 1.0))
        workload_loc_ar_count = int(ar_num * random.uniform(0.9, 1.0))
        
        # State metrics for AR (I -> D -> P -> C -> A)
        remaining_ar = ar_num
        a_state_ar_num = int(remaining_ar * random.uniform(0.1, 0.4))
        remaining_ar -= a_state_ar_num
        c_state_ar_num = int(remaining_ar * random.uniform(0.2, 0.5))
        remaining_ar -= c_state_ar_num
        p_state_ar_num = int(remaining_ar * random.uniform(0.3, 0.6))
        remaining_ar -= p_state_ar_num
        d_state_ar_num = int(remaining_ar * random.uniform(0.4, 0.7))
        remaining_ar -= d_state_ar_num
        i_state_ar_num = remaining_ar # Rest in Initial
        
        # State metrics for DR
        remaining_dr = dr_num
        a_state_dr_num = int(remaining_dr * random.uniform(0.1, 0.4))
        remaining_dr -= a_state_dr_num
        c_state_dr_num = int(remaining_dr * random.uniform(0.2, 0.5))
        remaining_dr -= c_state_dr_num
        p_state_dr_num = int(remaining_dr * random.uniform(0.3, 0.6))
        remaining_dr -= p_state_dr_num
        d_state_dr_num = int(remaining_dr * random.uniform(0.4, 0.7))
        remaining_dr -= d_state_dr_num
        i_state_dr_num = remaining_dr
        
        return {
            "sr_num": sr_num,
            "dr_num": dr_num,
            "ar_num": ar_num,
            "need_break_sr_num": need_break_sr_num,
            "need_break_dr_num": need_break_dr_num,
            "need_break_but_un_break_sr_num": need_break_but_un_break_sr_num,
            "need_break_but_un_break_dr_num": need_break_but_un_break_dr_num,
            "workload_man_dr_count": workload_man_dr_count,
            "workload_loc_dr_count": workload_loc_dr_count,
            "workload_man_ar_count": workload_man_ar_count,
            "workload_loc_ar_count": workload_loc_ar_count,
            "i_state_ar_num": i_state_ar_num,
            "d_state_ar_num": d_state_ar_num,
            "p_state_ar_num": p_state_ar_num,
            "c_state_ar_num": c_state_ar_num,
            "a_state_ar_num": a_state_ar_num,
            "i_state_dr_num": i_state_dr_num,
            "d_state_dr_num": d_state_dr_num,
            "p_state_dr_num": p_state_dr_num,
            "c_state_dr_num": c_state_dr_num,
            "a_state_dr_num": a_state_dr_num,
        }

def sync_project_iterations(project: Project):
    """
    同步单个项目的迭代数据
    """
    if not project.enable_iteration or not project.design_id or not project.sub_teams:
        return

    # 1. 获取所有迭代期
    iterations_data = DataPlatformMock.get_iterations(project.design_id, project.sub_teams)
    
    today = date.today()
    current_iteration = None

    for it_data in iterations_data:
        # 2. 保存/更新迭代期
        iteration, created = Iteration.objects.update_or_create(
            project=project,
            code=it_data['code'],
            defaults={
                "name": it_data['name'],
                "start_date": it_data['start_date'],
                "end_date": it_data['end_date'],
                # is_current 稍后统一计算
            }
        )
        
        # 判断是否为当前迭代
        is_current = it_data['start_date'] <= today <= it_data['end_date']
        if is_current:
            current_iteration = iteration

        # 3. 获取并保存指标数据 (记录为今天的数据)
        metrics_data = DataPlatformMock.get_iteration_metrics(it_data['code'])
        IterationMetric.objects.update_or_create(
            iteration=iteration,
            record_date=today,
            defaults=metrics_data
        )

    # 4. 更新 is_current 状态
    # 先重置该项目所有迭代为 False
    project.iterations.update(is_current=False)
    
    if current_iteration:
        current_iteration.is_current = True
        current_iteration.save(update_fields=['is_current'])
    else:
        # 如果没有匹配日期的，尝试找最新的一个已开始的，或者未来的第一个
        # 这里简单处理：如果没有命中的，则不设置（或保持 False）
        pass

def sync_all_projects_iterations():
    """
    定时任务调用：同步所有开启了迭代统计的项目
    """
    projects = Project.objects.filter(
        enable_iteration=True,
        is_deleted=False,
        is_closed=False
    ).exclude(design_id__isnull=True).exclude(design_id__exact='')
    
    for project in projects:
        try:
            sync_project_iterations(project)
        except Exception as e:
            print(f"Failed to sync project {project.name}: {e}")
