"""
数据库管理服务
使用工厂模式根据数据库类型创建对应的处理器
"""
import logging
from typing import Optional
from django.db import connections
from django.conf import settings
from .base_database_handler import BaseDatabaseHandler
from .postgresql_handler import PostgreSQLHandler
from .mysql_handler import MySQLHandler
from .sqlserver_handler import SQLServerHandler

logger = logging.getLogger(__name__)


class DatabaseManagerService:
    """数据库管理服务工厂"""
    
    @staticmethod
    def get_handler(db_name: str = "default") -> BaseDatabaseHandler:
        """
        根据数据库类型获取对应的处理器
        :param db_name: Django配置的数据库名称
        :return: 数据库处理器实例
        """
        try:
            connection = connections[db_name]
            engine = connection.settings_dict.get('ENGINE', '')
            
            if 'postgresql' in engine:
                return PostgreSQLHandler(db_name)
            elif 'mysql' in engine:
                return MySQLHandler(db_name)
            elif 'sql_server' in engine or 'mssql' in engine:
                return SQLServerHandler(db_name)
            else:
                # 默认使用基类（可能不支持某些特定操作）
                logger.warning(f"Unsupported database engine: {engine}, using base handler")
                raise ValueError(f"Unsupported database type: {engine}")
        except Exception as e:
            logger.error(f"Failed to get database handler for {db_name}: {e}")
            raise
    
    @staticmethod
    def get_database_configs():
        """获取所有配置的数据库信息"""
        configs = []
        
        for db_name, db_config in settings.DATABASES.items():
            engine = db_config.get('ENGINE', '')
            
            # 确定数据库类型
            if 'postgresql' in engine:
                db_type = 'postgresql'
            elif 'mysql' in engine:
                db_type = 'mysql'
            elif 'sql_server' in engine or 'mssql' in engine:
                db_type = 'sqlserver'
            elif 'sqlite' in engine:
                db_type = 'sqlite'
            elif 'oracle' in engine:
                db_type = 'oracle'
            else:
                db_type = 'unknown'
            
            config = {
                'db_name': db_name,
                'name': db_config.get('NAME', db_name),
                'db_type': db_type,
                'host': db_config.get('HOST', 'localhost'),
                'port': db_config.get('PORT', 5432),
                'database': db_config.get('NAME', ''),
                'user': db_config.get('USER', ''),
                'has_password': bool(db_config.get('PASSWORD', ''))
            }
            configs.append(config)
        
        return configs
    
    @staticmethod
    def test_connection(db_name: str = "default") -> dict:
        """
        测试数据库连接
        :param db_name: Django配置的数据库名称
        :return: 测试结果
        """
        try:
            connection = connections[db_name]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            return {
                "success": True,
                "message": "数据库连接成功",
                "db_name": db_name,
                "db_type": connection.settings_dict.get('ENGINE', '')
            }
        except Exception as e:
            logger.error(f"Database connection test failed for {db_name}: {e}")
            return {
                "success": False,
                "message": f"数据库连接失败: {str(e)}",
                "db_name": db_name
            }
