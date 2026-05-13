"""驱动初始化顺序与失败回滚"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_DRIVER_INIT_SEQUENCE = KnowledgeDocument(
    id='c_driver_init_sequence',
    title='驱动初始化顺序与失败回滚',
    category=KnowledgeCategory.BEST_PRACTICE,
    tags=['c', 'embedded', 'automotive', 'driver', 'init', 'hal', 'bsp', 'startup'],
    severity='medium',
    content="""
适用场景
- MCU 启动、外设驱动、HAL 包装、板级初始化、传感器/执行器驱动
- 设备电源、时钟、GPIO、DMA、中断和通信外设的组合初始化

核心原则
- 初始化顺序要与硬件依赖一致：时钟、引脚、复位、外设、DMA、IRQ
- 只有在状态完全就绪后才对外开放句柄或使能中断
- 失败回滚要按逆序释放，避免半初始化状态残留
- 初始化函数应当可重复调用或明确声明不可重入

审计要点
- 检查 enable IRQ / start DMA / 使能外设的顺序是否早于状态准备
- 检查失败分支是否把已申请资源、锁、缓冲区和状态位全部回滚
- 检查设备句柄是否在完成初始化前被其他线程或回调读取
- 检查 reset / power / clock / cache 相关调用是否缺失或重复

建议
- 使用清晰的 state machine 表达初始化阶段
- 将资源申请和资源发布分离，避免未就绪对象泄漏到外部
- 对复杂驱动保留统一 cleanup 标签，防止早返回打断回滚
""".strip(),
)
