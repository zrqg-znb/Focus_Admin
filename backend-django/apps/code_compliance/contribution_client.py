"""代码贡献采集的数据湖客户端出口。

CR 与漏合检测共用相同组织级传输协议，因此底层请求实现保留在
``missing_merge_client``；贡献服务只通过本模块依赖 CR/MR 客户端，避免
MR 采集逻辑扩散到漏合业务服务。
"""

from .missing_merge_client import CodeComplianceCRClient, CodeComplianceMRClient, DEFAULT_PAGE_SIZE


__all__ = ["CodeComplianceCRClient", "CodeComplianceMRClient", "DEFAULT_PAGE_SIZE"]
