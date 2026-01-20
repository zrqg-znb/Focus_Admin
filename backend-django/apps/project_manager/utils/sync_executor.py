import threading
import logging
import time
from typing import Callable, Any
from apps.project_manager.models.sync_log_model import SyncLog

logger = logging.getLogger(__name__)

def run_sync_task(
    project_id: str, 
    sync_type: str, 
    user_id: str, 
    sync_func: Callable, 
    func_args: tuple = (),
    func_kwargs: dict = None
):
    """
    运行同步任务（线程中执行）
    
    :param project_id: 项目ID
    :param sync_type: 同步类型
    :param user_id: 用户ID
    :param sync_func: 同步函数
    :param func_args: 同步函数的位置参数
    :param func_kwargs: 同步函数的关键字参数
    """
    if func_kwargs is None:
        func_kwargs = {}

    # 创建同步日志
    log = SyncLog.objects.create(
        project_id=project_id,
        sync_type=sync_type,
        status='pending',
        sys_creator_id=user_id,
        result_summary="任务已提交，正在排队执行...",
    )
    
    def _wrapper():
        start_time = time.time()
        try:
            logger.info(f"开始执行同步任务: {sync_type} - {project_id}")
            
            # 执行同步逻辑
            result = sync_func(*func_args, **func_kwargs)
            
            # 计算耗时
            duration = time.time() - start_time
            
            # 更新日志为成功
            log.status = 'success'
            log.result_summary = "同步成功"
            log.detail_log = str(result) if result else "同步完成"
            log.duration = duration
            log.save()
            
            logger.info(f"同步任务完成: {sync_type} - {project_id}，耗时: {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"同步任务失败: {sync_type} - {project_id}, 错误: {str(e)}", exc_info=True)
            
            # 更新日志为失败
            log.status = 'failed'
            log.result_summary = "同步失败"
            log.detail_log = f"错误信息: {str(e)}"
            log.duration = duration
            log.save()
        finally:
            from django.db import connection
            connection.close()

    # 启动线程
    thread = threading.Thread(target=_wrapper)
    thread.start()
    
    return log
