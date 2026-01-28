#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Scheduler Service - APScheduler 调度服务
基于 APScheduler 实现的定时任务调度核心服务
"""
import json
import logging
import inspect  # 添加 inspect 模块
from datetime import datetime
from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.schedulers.base import STATE_RUNNING, STATE_PAUSED, STATE_STOPPED
from django.conf import settings
from django.core.cache import cache
import time

logger = logging.getLogger(__name__)

SCHEDULER_HEARTBEAT_KEY = "scheduler_heartbeat"
SCHEDULER_COMMAND_PREFIX = "scheduler_cmd_"

class SchedulerService:
    """
    定时任务调度服务
    
    功能特点：
    1. 单例模式，全局唯一调度器实例
    2. 支持多种触发器类型（cron、interval、date）
    3. 自动从数据库加载任务
    4. 监听任务执行事件
    5. 自动更新任务状态
    6. 支持多进程同步（通过数据库和缓存）
    """
    
    _instance = None
    _scheduler: Optional[BackgroundScheduler] = None
    _initialized = False
    _job_versions: Dict[str, datetime] = {}  # 记录任务版本，用于同步
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化调度器"""
        if not self._initialized:
            self._init_scheduler()
            self._initialized = True
    
    def _init_scheduler(self):
        """初始化 APScheduler"""
        try:
            # 创建后台调度器
            self._scheduler = BackgroundScheduler(
                timezone=settings.TIME_ZONE,
                job_defaults={
                    'coalesce': True,  # 合并执行
                    'max_instances': 1,  # 最大实例数
                    'misfire_grace_time': 60,  # 错过执行的宽限时间（秒）
                }
            )
            
            # 添加事件监听器
            self._scheduler.add_listener(
                self._job_executed_listener,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
            )
            
            logger.info("APScheduler 初始化成功")
        except Exception as e:
            logger.error(f"APScheduler 初始化失败: {str(e)}")
            raise

    def start_monitor(self):
        """启动监控循环（阻塞模式，用于独立进程）"""
        from django.db import close_old_connections

        self.start()
        logger.info("调度器监控进程已启动")
        
        try:
            while True:
                close_old_connections()
                # 1. 更新心跳
                self.touch_heartbeat()
                
                # 2. 同步任务
                self.sync_jobs_from_db()
                
                # 3. 检查命令（如立即执行）
                self.check_commands()
                
                # 休眠
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在停止...")
            self.shutdown()
        except Exception as e:
            logger.error(f"监控进程异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5) # 防止死循环快速报错

    def touch_heartbeat(self):
        """更新心跳"""
        try:
            cache.set(SCHEDULER_HEARTBEAT_KEY, time.time(), timeout=30)
        except Exception as e:
            logger.error(f"更新心跳失败: {e}")

    @staticmethod
    def is_scheduler_alive():
        """检查调度器进程是否存活"""
        try:
            last_beat = cache.get(SCHEDULER_HEARTBEAT_KEY)
            if last_beat and (time.time() - last_beat < 30):
                return True
            return False
        except Exception:
            return False

    def check_commands(self):
        """检查并执行命令"""
        try:
            # 这里简单实现：遍历所有任务，检查是否有立即执行的命令
            # 更高效的方式是维护一个命令队列，但对于少量任务，这样也行
            jobs = self._scheduler.get_jobs()
            for job in jobs:
                cmd_key = f"{SCHEDULER_COMMAND_PREFIX}run_{job.id}"
                if cache.get(cmd_key):
                    logger.info(f"收到立即执行命令: {job.id}")
                    self.run_job_now(job.id)
                    cache.delete(cmd_key)
        except Exception as e:
            logger.error(f"检查命令失败: {e}")

    def sync_jobs_from_db(self):
        """从数据库同步任务"""
        try:
            from django.db import close_old_connections
            from scheduler.models import SchedulerJob
            close_old_connections()
            
            # 获取所有未删除的任务
            db_jobs = SchedulerJob.objects.filter(is_deleted=False)
            active_codes = []
            
            for job in db_jobs:
                # 如果任务被禁用，确保从调度器移除
                if job.status == 0:
                    if self._scheduler.get_job(job.code):
                        self.remove_job(job.code)
                    continue
                
                active_codes.append(job.code)
                
                current_job = self._scheduler.get_job(job.code)
                last_version = self._job_versions.get(job.code)
                
                # 1. 添加或更新任务
                # 如果任务不存在，或者版本号不一致（且任务在DB中是启用或暂停状态）
                if not current_job:
                    self.add_job(job)
                elif last_version != job.sys_update_datetime:
                    logger.info(f"检测到任务变更: {job.code}")
                    self.modify_job(job)
                
                # 2. 同步暂停/恢复状态
                # modify_job 会根据 status 重新添加任务（如果是 enabled）
                # 但如果仅仅是状态变更（例如 pause -> resume），modify_job 也会处理
                # 这里做一次额外的状态检查以确保一致性
                current_job = self._scheduler.get_job(job.code)
                if current_job:
                    if job.status == 2 and current_job.next_run_time is not None:
                        self.pause_job(job.code)
                    elif job.status == 1 and current_job.next_run_time is None:
                        self.resume_job(job.code)
            
            # 移除数据库中不存在的任务
            for job in self._scheduler.get_jobs():
                if job.id not in active_codes:
                    logger.info(f"任务已从数据库删除，移除调度: {job.id}")
                    self.remove_job(job.id)
                    
        except Exception as e:
            logger.error(f"同步任务失败: {str(e)}")

    @staticmethod
    def _with_db_connection_cleanup(task_func):
        from functools import wraps
        from django.db import close_old_connections

        @wraps(task_func)
        def wrapped(*args, **kwargs):
            close_old_connections()
            try:
                return task_func(*args, **kwargs)
            finally:
                close_old_connections()

        return wrapped

    def start(self):
        """启动调度器"""
        if self._scheduler and not self._scheduler.running:
            try:
                self._scheduler.start()
                logger.info("APScheduler 已启动")
                # 加载数据库中的任务
                self.load_jobs_from_db()
            except Exception as e:
                logger.error(f"APScheduler 启动失败: {str(e)}")
                raise
    
    def shutdown(self, wait=True):
        """关闭调度器"""
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=wait)
                logger.info("APScheduler 已关闭")
            except Exception as e:
                logger.error(f"APScheduler 关闭失败: {str(e)}")
                raise
    
    def pause(self):
        """暂停调度器"""
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.pause()
                logger.info("APScheduler 已暂停")
            except Exception as e:
                logger.error(f"APScheduler 暂停失败: {str(e)}")
                raise
    
    def resume(self):
        """恢复调度器"""
        if self._scheduler:
            try:
                self._scheduler.resume()
                logger.info("APScheduler 已恢复")
            except Exception as e:
                logger.error(f"APScheduler 恢复失败: {str(e)}")
                raise
    
    def is_running(self) -> bool:
        """
        判断调度器是否运行中
        
        如果是在 Web 进程中调用，会检查调度器进程的心跳
        如果是在调度器进程中调用，直接返回本地状态
        """
        # 检查是否是独立进程模式（通过检查心跳）
        if self.is_scheduler_alive():
            return True
            
        # 回退到本地检查 (兼容单进程模式)
        return self._scheduler and self._scheduler.running
    
    def is_paused(self) -> bool:
        """判断调度器是否暂停"""
        return self._scheduler and self._scheduler.state == STATE_PAUSED

    def get_state(self) -> int:
        """
        获取调度器状态
        """
        if self.is_scheduler_alive():
            return STATE_RUNNING
            
        if not self._scheduler:
            return STATE_STOPPED
        return self._scheduler.state
    
    def load_jobs_from_db(self):
        """从数据库加载所有启用的任务 (已废弃，请使用 sync_jobs_from_db)"""
        self.sync_jobs_from_db()
    
    def add_job(self, job_obj):
        """添加任务到调度器"""
        try:
            # 构建触发器
            trigger = self._build_trigger(job_obj)
            if not trigger:
                logger.error(f"无法为任务 {job_obj.code} 构建触发器")
                return False
            
            # 解析任务参数
            args = json.loads(job_obj.task_args) if job_obj.task_args else []
            kwargs = json.loads(job_obj.task_kwargs) if job_obj.task_kwargs else {}
            
            # 导入任务函数
            task_func = self._import_task_func(job_obj.task_func)
            if not task_func:
                logger.error(f"无法导入任务函数: {job_obj.task_func}")
                return False

            task_func = self._with_db_connection_cleanup(task_func)
            
            # 智能注入 job_code 参数
            # 检查函数签名，如果函数接受 job_code 参数或接受 **kwargs，则注入
            try:
                sig = inspect.signature(task_func)
                params = sig.parameters
                if 'job_code' in params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                    kwargs['job_code'] = job_obj.code
            except Exception as e:
                # 如果检查签名失败，为了保险起见，不注入参数，避免调用失败
                logger.warning(f"检查任务函数签名失败 {job_obj.code}: {str(e)}")

            # 添加任务
            self._scheduler.add_job(
                func=task_func,
                trigger=trigger,
                args=args,
                kwargs=kwargs,
                id=job_obj.code,
                name=job_obj.name,
                max_instances=job_obj.max_instances,
                coalesce=job_obj.coalesce,
                replace_existing=True,
            )
            
            # 更新下次执行时间
            self._update_next_run_time(job_obj)
            
            # 更新版本记录
            self._job_versions[job_obj.code] = job_obj.sys_update_datetime
            
            logger.info(f"任务 {job_obj.code} 已添加到调度器")
            return True
        except Exception as e:
            logger.error(f"添加任务失败 {job_obj.code}: {str(e)}")
            return False
    
    def remove_job(self, job_code: str):
        """从调度器移除任务"""
        try:
            if self._scheduler.get_job(job_code):
                self._scheduler.remove_job(job_code)
                # 清除版本记录
                if job_code in self._job_versions:
                    del self._job_versions[job_code]
                logger.info(f"任务 {job_code} 已从调度器移除")
                return True
            return False
        except Exception as e:
            logger.error(f"移除任务失败 {job_code}: {str(e)}")
            return False
    
    def pause_job(self, job_code: str):
        """暂停任务"""
        try:
            if self._scheduler.get_job(job_code):
                self._scheduler.pause_job(job_code)
                logger.info(f"任务 {job_code} 已暂停")
                return True
            return False
        except Exception as e:
            logger.error(f"暂停任务失败 {job_code}: {str(e)}")
            return False
    
    def resume_job(self, job_code: str):
        """恢复任务"""
        try:
            if self._scheduler.get_job(job_code):
                self._scheduler.resume_job(job_code)
                logger.info(f"任务 {job_code} 已恢复")
                return True
            return False
        except Exception as e:
            logger.error(f"恢复任务失败 {job_code}: {str(e)}")
            return False
    
    def modify_job(self, job_obj):
        """修改任务"""
        try:
            # 先移除旧任务
            self.remove_job(job_obj.code)
            
            # 如果任务是启用状态，重新添加
            if job_obj.is_enabled():
                return self.add_job(job_obj)
            
            return True
        except Exception as e:
            logger.error(f"修改任务失败 {job_obj.code}: {str(e)}")
            return False
    
    def run_job_now(self, job_code: str):
        """立即执行任务（不影响正常调度）"""
        try:
            job = self._scheduler.get_job(job_code)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"任务 {job_code} 将立即执行")
                return True
            return False
        except Exception as e:
            logger.error(f"立即执行任务失败 {job_code}: {str(e)}")
            return False
    
    def get_job_info(self, job_code: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        try:
            job = self._scheduler.get_job(job_code)
            if job:
                return {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger),
                }
            return None
        except Exception as e:
            logger.error(f"获取任务信息失败 {job_code}: {str(e)}")
            return None
    
    def get_all_jobs(self) -> list:
        """获取所有任务"""
        try:
            jobs = self._scheduler.get_jobs()
            return [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger),
                }
                for job in jobs
            ]
        except Exception as e:
            logger.error(f"获取所有任务失败: {str(e)}")
            return []
    
    def _build_trigger(self, job_obj):
        """构建触发器"""
        try:
            if job_obj.trigger_type == 'cron':
                # Cron 触发器
                # 解析 cron 表达式：minute hour day month day_of_week
                parts = job_obj.cron_expression.split()
                if len(parts) != 5:
                    logger.error(f"Cron 表达式格式错误: {job_obj.cron_expression}")
                    return None
                
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone=settings.TIME_ZONE,
                )
            
            elif job_obj.trigger_type == 'interval':
                # 间隔触发器
                return IntervalTrigger(
                    seconds=job_obj.interval_seconds,
                    timezone=settings.TIME_ZONE,
                )
            
            elif job_obj.trigger_type == 'date':
                # 指定时间触发器
                return DateTrigger(
                    run_date=job_obj.run_date,
                    timezone=settings.TIME_ZONE,
                )
            
            else:
                logger.error(f"不支持的触发器类型: {job_obj.trigger_type}")
                return None
        
        except Exception as e:
            logger.error(f"构建触发器失败: {str(e)}")
            return None
    
    def _import_task_func(self, task_path: str):
        """动态导入任务函数"""
        try:
            module_path, func_name = task_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[func_name])
            return getattr(module, func_name)
        except Exception as e:
            logger.error(f"导入任务函数失败 {task_path}: {str(e)}")
            return None
    
    def _update_next_run_time(self, job_obj):
        """更新任务的下次执行时间"""
        try:
            from django.db import close_old_connections
            job = self._scheduler.get_job(job_obj.code)
            if job and job.next_run_time:
                from scheduler.models import SchedulerJob
                close_old_connections()
                # 处理时区问题：如果 USE_TZ=False，需要将时间转换为 naive datetime
                next_run_time = job.next_run_time
                if not settings.USE_TZ and next_run_time and next_run_time.tzinfo:
                    next_run_time = next_run_time.replace(tzinfo=None)
                
                SchedulerJob.objects.filter(id=job_obj.id).update(
                    next_run_time=next_run_time
                )
        except Exception as e:
            logger.error(f"更新下次执行时间失败: {str(e)}")
    
    def _job_executed_listener(self, event: JobExecutionEvent):
        """任务执行事件监听器"""
        try:
            from django.db import close_old_connections
            from scheduler.models import SchedulerJob, SchedulerLog
            from django.utils import timezone
            import traceback
            close_old_connections()

            job_code = event.job_id
            
            # 更新任务统计信息
            job_obj = SchedulerJob.objects.filter(code=job_code).first()
            if job_obj:
                # 准备日志数据
                log_data = {
                    'job': job_obj,
                    'job_name': job_obj.name,
                    'job_code': job_obj.code,
                    'start_time': event.scheduled_run_time,
                    'end_time': timezone.now(),
                    'hostname': 'localhost',  # 简单实现
                }

                # 处理时区问题
                if not settings.USE_TZ:
                    if log_data['start_time'] and log_data['start_time'].tzinfo:
                        log_data['start_time'] = log_data['start_time'].replace(tzinfo=None)
                    if log_data['end_time'] and log_data['end_time'].tzinfo:
                        log_data['end_time'] = log_data['end_time'].replace(tzinfo=None)

                if event.exception:
                    # 执行失败
                    job_obj.last_run_status = 'failed'
                    job_obj.last_run_result = str(event.exception)
                    job_obj.increment_run_count(success=False)
                    
                    log_data['status'] = 'failed'
                    log_data['exception'] = str(event.exception)
                    log_data['traceback'] = event.traceback
                    log_data['result'] = None
                else:
                    # 执行成功
                    job_obj.last_run_status = 'success'
                    job_obj.last_run_result = str(event.retval) if event.retval else None
                    job_obj.increment_run_count(success=True)
                    
                    log_data['status'] = 'success'
                    log_data['exception'] = None
                    log_data['traceback'] = None
                    log_data['result'] = str(event.retval) if event.retval else "Success"
                
                # 计算耗时
                if log_data['start_time'] and log_data['end_time']:
                    # 确保两者都是 offset-aware 或 offset-naive
                    start_dt = log_data['start_time']
                    end_dt = log_data['end_time']
                    
                    if start_dt.tzinfo and not end_dt.tzinfo:
                         end_dt = end_dt.replace(tzinfo=start_dt.tzinfo)
                    elif not start_dt.tzinfo and end_dt.tzinfo:
                         start_dt = start_dt.replace(tzinfo=end_dt.tzinfo)
                         
                    duration = (end_dt - start_dt).total_seconds()
                    log_data['duration'] = max(0, duration) # 避免负数
                
                # 创建日志
                SchedulerLog.objects.create(**log_data)

                job_obj.last_run_time = timezone.now()
                job_obj.save(update_fields=[
                    'last_run_status',
                    'last_run_result',
                    'last_run_time',
                    'total_run_count',
                    'success_count',
                    'failure_count'
                ])
                
                # 更新下次执行时间
                self._update_next_run_time(job_obj)
        
        except Exception as e:
            logger.error(f"处理任务执行事件失败: {str(e)}")
        finally:
            try:
                from django.db import close_old_connections
                close_old_connections()
            except Exception:
                pass


# 全局调度器实例
scheduler_service = SchedulerService()
