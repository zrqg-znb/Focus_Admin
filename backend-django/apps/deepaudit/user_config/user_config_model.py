from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User


class AuditUserConfig(RootModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deepaudit_config', db_constraint=False, verbose_name='所属用户')
    llm_config = models.JSONField(default=dict, blank=True, verbose_name='LLM 配置')
    other_config = models.JSONField(default=dict, blank=True, verbose_name='其他配置')

    class Meta:
        db_table = 'deepaudit_user_config'
        verbose_name = 'DeepAudit 用户配置'
        verbose_name_plural = verbose_name


class AuditGlobalEmbeddingConfig(RootModel):
    """Singleton configuration used by every DeepAudit worker."""

    config_key = models.CharField(max_length=64, unique=True, default='default', verbose_name='配置键')
    provider = models.CharField(max_length=64, blank=True, default='', verbose_name='Embedding Provider')
    model = models.CharField(max_length=255, blank=True, default='', verbose_name='Embedding 模型')
    base_url = models.CharField(max_length=1024, blank=True, default='', verbose_name='Embedding 服务地址')
    api_key_encrypted = models.TextField(blank=True, default='', verbose_name='加密后的 API Key')
    dimensions = models.PositiveIntegerField(blank=True, null=True, verbose_name='向量维度')
    batch_size = models.PositiveIntegerField(blank=True, null=True, verbose_name='批处理大小')

    class Meta:
        db_table = 'deepaudit_global_embedding_config'
        verbose_name = 'DeepAudit 全局 Embedding 配置'
        verbose_name_plural = verbose_name


class AuditSshCredential(RootModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deepaudit_ssh_credential', db_constraint=False, verbose_name='所属用户')
    private_key_encrypted = models.TextField(blank=True, null=True, verbose_name='加密后的私钥')
    public_key = models.TextField(blank=True, null=True, verbose_name='公钥')
    fingerprint = models.CharField(max_length=255, blank=True, null=True, verbose_name='指纹')
    known_hosts = models.TextField(blank=True, null=True, verbose_name='known_hosts')

    class Meta:
        db_table = 'deepaudit_ssh_credential'
        verbose_name = 'DeepAudit SSH 凭据'
        verbose_name_plural = verbose_name
