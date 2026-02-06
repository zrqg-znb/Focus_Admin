# 代码扫描

代码扫描模块（`code_scan`）用于集成静态代码分析工具，提供缺陷看板展示和屏蔽审批流程。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ScanProject (扫描项目)                                │
│  - 项目名称、代码仓地址、分支                                             │
│  - project_key (流水线认证标识)                                          │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ScanTask (扫描任务)                                 │
│  - 工具名称 (tscan/cppcheck)                                             │
│  - 来源 (pipeline/manual)                                                │
│  - 状态 (pending/processing/success/failed)                             │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ScanResult (扫描结果)                                │
│  - 文件路径、行号、缺陷类型、严重程度                                      │
│  - fingerprint (缺陷指纹，用于跨版本匹配)                                  │
│  - shield_status (Normal/Pending/Shielded/Rejected)                     │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  ShieldApplication (屏蔽申请)                            │
│  - 申请人、审批人                                                         │
│  - 申请理由、审批意见                                                     │
│  - 状态 (Pending/Approved/Rejected)                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| ScanProject | ScanTask | 1:N | 一个项目可以有多次扫描任务 |
| ScanTask | ScanResult | 1:N | 每次扫描产生多个缺陷结果 |
| ScanResult | ShieldApplication | 1:N | 一个缺陷可以有多次屏蔽申请 |
| ShieldApplication | User | N:1 | 申请人/审批人关联用户 |

## 核心概念

### 扫描工具支持

| 工具 | 代码 | 报告格式 | 说明 |
| --- | --- | --- | --- |
| TScanCode | `tscan` | XML | 腾讯开源静态代码分析工具 |
| CppCheck | `cppcheck` | XML | C/C++ 静态分析工具 |

### 缺陷严重程度

| 等级 | 代码 | 说明 |
| --- | --- | --- |
| 高 | `High` | 严重缺陷，需立即修复 |
| 中 | `Medium` | 中等缺陷，建议修复 |
| 低 | `Low` | 轻微缺陷，可选修复 |

### 屏蔽状态流转

```
Normal (正常)
    │
    │ 申请屏蔽
    ▼
Pending (申请中)
    │
    ├─── 审批通过 ──▶ Shielded (已屏蔽)
    │
    └─── 审批驳回 ──▶ Rejected (已驳回)
```

### 缺陷指纹

系统通过 `fingerprint` 字段实现缺陷的跨版本追踪：

- **生成规则**: `MD5(file_path + defect_type + description)`
- **不包含行号**: 支持代码移动后仍能匹配
- **屏蔽继承**: 新扫描时自动匹配已屏蔽的相同指纹

## 数据流程

### 流水线集成流程

```
CI/CD 流水线
    │
    │ 执行 TScan/CppCheck 扫描
    ▼
生成报告文件 (XML)
    │
    │ POST /api/code-scan/upload
    │ (携带 project_key + 报告文件)
    ▼
┌─────────────────────────────────────────┐
│            ScanService                  │
│  1. 验证 project_key                    │
│  2. 保存报告文件                          │
│  3. 创建 ScanTask (status=processing)   │
│  4. 调用 Parser 解析报告                  │
│  5. 批量创建 ScanResult                  │
│  6. 自动匹配已屏蔽缺陷                     │
│  7. 更新 ScanTask (status=success)      │
└─────────────────────────────────────────┘
```

### 屏蔽审批流程

```
开发人员                          审批人
    │                               │
    │ 选择缺陷 + 提交屏蔽申请          │
    │ POST /api/code-scan/shield/apply
    ▼                               │
ScanResult.shield_status = Pending  │
ShieldApplication 创建              │
    │                               │
    │ ─────────通知审批─────────────▶│
    │                               │
    │                        审批通过/驳回
    │                        POST /api/code-scan/shield/audit
    │                               │
    │◀────────返回审批结果────────── │
    ▼                               ▼
ScanResult.shield_status 更新   审批流程结束
```

## 解析器设计

### 工厂模式

```python
# parsers/factory.py
class ParserFactory:
    _parsers = {
        'tscan': TScanParser,
        'cppcheck': CppCheckParser,
    }
    
    @classmethod
    def get_parser(cls, tool_name: str) -> BaseParser:
        parser_cls = cls._parsers.get(tool_name.lower())
        if not parser_cls:
            raise ValueError(f"No parser found for tool: {tool_name}")
        return parser_cls()
```

### 解析器接口

```python
# parsers/base.py
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        返回格式:
        [
            {
                "file_path": str,
                "line_number": int,
                "defect_type": str,
                "severity": str,  # High/Medium/Low
                "description": str,
                "help_info": str,      # 可选
                "code_snippet": str,   # 可选
            }
        ]
        """
        pass
```

## 目录结构

```
apps/code_scan/
├── parsers/                 # 报告解析器
│   ├── base.py             # 解析器基类
│   ├── factory.py          # 工厂模式
│   ├── tscan_parser.py     # TScanCode 解析器
│   └── cppcheck_parser.py  # CppCheck 解析器
│
├── api.py                   # API 接口
├── models.py                # 数据模型
├── schemas.py               # Pydantic Schema
└── services.py              # 业务服务
```

## API 路由

| 路径 | 方法 | 说明 | 认证 |
| --- | --- | --- | --- |
| `/api/code-scan/projects` | GET | 项目列表 | Bearer |
| `/api/code-scan/projects` | POST | 创建项目 | Bearer |
| `/api/code-scan/projects/overview` | GET | 项目概览（含统计） | Bearer |
| `/api/code-scan/upload` | POST | 上传扫描报告 | project_key |
| `/api/code-scan/upload/chunk` | POST | 分片上传 | project_key |
| `/api/code-scan/tasks` | GET | 任务列表 | Bearer |
| `/api/code-scan/results` | GET | 扫描结果 | Bearer |
| `/api/code-scan/projects/{id}/latest-results` | GET | 最新扫描结果 | Bearer |
| `/api/code-scan/shield/apply` | POST | 提交屏蔽申请 | Bearer |
| `/api/code-scan/shield/applications` | GET | 申请列表 | Bearer |
| `/api/code-scan/shield/audit` | POST | 审批屏蔽申请 | Bearer |

## 前端页面

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 项目管理 | `/code-scan/project` | 项目 CRUD、project_key 管理 |
| 扫描结果 | `/code-scan/result` | 缺陷列表、屏蔽申请 |
| 审批管理 | `/code-scan/audit` | 我的申请、待我审批 |

## 扩展指南

### 添加新的扫描工具

1. 在 `parsers/` 下创建新的解析器类，继承 `BaseParser`
2. 实现 `parse()` 方法，返回标准格式的缺陷列表
3. 在 `ParserFactory._parsers` 中注册新解析器

```python
# parsers/coverity_parser.py
class CoverityParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        # 解析 Coverity JSON 报告
        ...

# parsers/factory.py
_parsers = {
    'tscan': TScanParser,
    'cppcheck': CppCheckParser,
    'coverity': CoverityParser,  # 新增
}
```

### 流水线集成示例

```bash
# 1. 执行扫描
tscancode --xml -o result.xml ./src

# 2. 上传报告
curl -X POST "${API_BASE}/api/code-scan/upload" \
  -F "project_key=${PROJECT_KEY}" \
  -F "tool_name=tscan" \
  -F "file=@result.xml"
```
