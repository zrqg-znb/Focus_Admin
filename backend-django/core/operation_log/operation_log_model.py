#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from common.fu_model import RootModel


class OperationLog(RootModel):
    request_username = models.CharField(max_length=150, help_text="请求用户名", db_index=True)
    request_ip = models.GenericIPAddressField(help_text="请求IP", db_index=True)
    request_method = models.CharField(max_length=10, help_text="请求方法", db_index=True)
    request_path = models.CharField(max_length=255, help_text="请求路径", db_index=True)
    request_modular = models.CharField(max_length=100, null=True, blank=True, help_text="所属模块", db_index=True)
    request_body = models.JSONField(null=True, blank=True, help_text="请求体")
    response_code = models.IntegerField(null=True, blank=True, help_text="响应业务码", db_index=True)
    request_os = models.CharField(max_length=50, null=True, blank=True, help_text="操作系统")
    request_browser = models.CharField(max_length=50, null=True, blank=True, help_text="浏览器")
    request_msg = models.CharField(max_length=255, null=True, blank=True, help_text="请求消息")
    status = models.BooleanField(default=False, help_text="是否成功", db_index=True)
    json_result = models.JSONField(null=True, blank=True, help_text="响应结果摘要")

    class Meta:
        db_table = "core_operation_log"
        ordering = ("-sys_create_datetime",)
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["request_username", "sys_create_datetime"]),
            models.Index(fields=["request_ip", "sys_create_datetime"]),
            models.Index(fields=["request_method", "sys_create_datetime"]),
            models.Index(fields=["request_path", "sys_create_datetime"]),
            models.Index(fields=["request_modular", "sys_create_datetime"]),
            models.Index(fields=["status", "sys_create_datetime"]),
        ]

    def __str__(self):
        return f"{self.request_username} {self.request_method} {self.request_path}"

