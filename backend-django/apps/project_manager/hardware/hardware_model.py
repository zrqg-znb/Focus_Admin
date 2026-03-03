from django.db import models

from common.fu_model import RootModel


class HardwarePoint(RootModel):
    code = models.CharField(max_length=64, unique=True, verbose_name="硬件点位")
    boards = models.JSONField(default=list, blank=True, verbose_name="板子列表")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = "pm_hardware_point"
        verbose_name = "硬件点位"
        verbose_name_plural = verbose_name


class CdcPlatform(RootModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="CDC平台")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = "pm_cdc_platform"
        verbose_name = "CDC平台"
        verbose_name_plural = verbose_name


class ViuPlatform(RootModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="VIU硬件平台")
    configs = models.JSONField(default=list, blank=True, verbose_name="典配列表")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = "pm_viu_platform"
        verbose_name = "VIU硬件平台"
        verbose_name_plural = verbose_name


class IdvpPlatform(RootModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="IDVP软件平台")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = "pm_idvp_platform"
        verbose_name = "IDVP软件平台"
        verbose_name_plural = verbose_name


class SmartScreenVersion(RootModel):
    name = models.CharField(max_length=128, unique=True, verbose_name="智慧屏版本")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = "pm_smart_screen_version"
        verbose_name = "智慧屏版本"
        verbose_name_plural = verbose_name
