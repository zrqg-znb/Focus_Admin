---
title: 自动化测试报告
description: Focus 自动化测试报告模块设计说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('auto-test-report');

const apis = [
  {
    consumer: '平台与车型配置页',
    method: 'GET / POST / PUT / DELETE',
    params: 'platform / vehicle payload',
    path: '/api/auto-test-report/platforms / /api/auto-test-report/vehicles',
    purpose: '维护 MCU 平台与车型主数据',
    returns: 'PlatformOut / VehicleOut',
  },
  {
    consumer: '用例管理页',
    method: 'GET / POST / PUT / DELETE / PATCH',
    params: 'vehicle_id, case rows, file, remark',
    path: '/api/auto-test-report/test-cases',
    purpose: '维护、导入、导出测试用例与备注',
    returns: 'TestCaseOut / ImportResultOut',
  },
  {
    consumer: '测试环境上报',
    method: 'POST',
    params: 'vehicle_code, execute_date, results[]',
    path: '/api/auto-test-report/report/daily-results',
    purpose: '由测试环境上报每日执行结果并触发汇总重算',
    returns: 'ReportDailyResultsOut',
  },
  {
    consumer: '日报汇总与总览',
    method: 'GET',
    params: 'vehicle_id, execute_date / 平台、状态筛选',
    path: '/api/auto-test-report/daily-results/summary / /api/auto-test-report/daily-results/overview',
    purpose: '返回单车型汇总和全量车型执行概览',
    returns: 'DailySummary / DailyOverviewResponse',
  },
  {
    consumer: '日报明细与历史',
    method: 'GET / PATCH',
    params: 'vehicle_id, execute_date / result_id, failure_reason / case_id',
    path: '/api/auto-test-report/daily-results/list / /api/auto-test-report/daily-results/{result_id}/failure-reason / /api/auto-test-report/test-cases/{case_id}/history',
    purpose: '查看每日执行明细、补充异常原因、查询用例历史执行',
    returns: 'DailyResultItem[] / bool / DailyHistoryPage',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

<FocusModuleSection
  kicker="Module Purpose"
  title="模块定位"
  summary="自动化测试报告模块把平台、车型、测试用例和每日执行结果连接成一条持续积累的验证数据链。它不是一次性报表页面，而是一套长期沉淀自动化执行数据的结构化系统。"
>

它重点解决四类问题：

- 用什么平台、什么车型在执行
- 哪些用例属于该车型
- 某一天这些用例跑出了什么结果
- 如何从明细回溯到历史趋势和异常原因

因此这是一个“主数据 + 日执行明细 + 日汇总视图”组合模块。

</FocusModuleSection>

<FocusModuleSection
  kicker="Data Model"
  title="表结构与关系设计"
  summary="模块结构是一条很清晰的层级链：平台 -> 车型 -> 用例 -> 每日结果 / 每日批次。"
>

```mermaid
erDiagram
    MCU_PLATFORM ||--o{ VEHICLE_MODEL : contains
    VEHICLE_MODEL ||--o{ TEST_CASE : contains
    VEHICLE_MODEL ||--o{ DAILY_EXECUTION_BATCH : summarizes
    VEHICLE_MODEL ||--o{ DAILY_EXECUTION_RESULT : runs
    TEST_CASE ||--o{ DAILY_EXECUTION_RESULT : executes

    MCU_PLATFORM {
        uuid id PK
        string name
        string version_code
        bool is_active
        text remark
    }

    VEHICLE_MODEL {
        uuid id PK
        uuid platform_id FK
        string name
        string vehicle_code UK
        string cdc_platform
        string execution_machine
        bool is_active
        text remark
    }

    TEST_CASE {
        uuid id PK
        uuid vehicle_id FK
        string case_no
        string case_name
        text remark
        bool is_active
    }

    DAILY_EXECUTION_BATCH {
        uuid id PK
        uuid vehicle_id FK
        date execute_date
        int total_count
        int success_count
        int failed_count
        int timeout_count
        int skip_count
        int total_duration_seconds
        datetime last_report_at
    }

    DAILY_EXECUTION_RESULT {
        uuid id PK
        uuid vehicle_id FK
        uuid test_case_id FK
        date execute_date
        datetime start_time
        int duration_seconds
        string result
        text failure_reason
        string log_url
        datetime reported_at
    }
```

## 关键字段说明

### `McuPlatform`

平台主数据层，区分 MCU 平台，关键字段包括：

- `name`
- `version_code`
- `is_active`
- `remark`

### `VehicleModel`

车型层对象，关键字段包括：

- `platform`
  所属平台
- `vehicle_code`
  外部上报识别码
- `cdc_platform`
  座舱平台信息
- `execution_machine`
  执行机器

这里同时有两个唯一性约束：

- `vehicle_code` 全局唯一
- `platform + name` 组合唯一

### `TestCase`

测试用例对象，关键字段包括：

- `vehicle`
  归属车型
- `case_no`
  用例编号
- `case_name`
  用例名称
- `remark`
  测试说明或补充信息
- `is_active`
  是否启用

同一车型下 `case_no` 唯一。

### `DailyExecutionResult` 与 `DailyExecutionBatch`

这两个对象共同构成“明细 + 汇总”双层视图：

- `DailyExecutionResult`
  保存单条执行结果
- `DailyExecutionBatch`
  保存同车型同日期的汇总结果

`DailyExecutionBatch` 通过 `vehicle + execute_date` 唯一，保证每日每车型只有一条汇总记录。

</FocusModuleSection>

<FocusModuleSection
  kicker="Implementation"
  title="关键实现原理"
  summary="自动化测试报告模块最重要的设计，不是页面多少，而是明细如何沉淀、汇总如何重算、异常原因如何复用。"
>

### 结果上报：`report_daily_results`

在 `backend-django/apps/auto_test_report/auto_test_report_services.py` 中，上报流程会：

1. 根据 `vehicle_code` 找到有效车型
2. 读取该车型下全部有效用例
3. 校验每条上报结果中的 `case_no`
4. 为每条结果创建 `DailyExecutionResult`
5. 调用 `recalculate_daily_batch`

这说明系统不是直接覆盖结果，而是按上报事件追加结果，再重新计算当前视图。

### 汇总重算：`recalculate_daily_batch`

汇总逻辑会：

1. 读取该车型下所有启用用例数
2. 查询某天每个用例的最新执行结果
3. 统计 `success / failed / timeout`
4. 用“总用例数 - 实际有结果的用例数”计算 `skip_count`
5. 更新 `DailyExecutionBatch`

这意味着：

- `skip` 不是由外部上报直接传入，而是系统根据未出现的用例推导出来
- 汇总表是派生视图，而不是独立业务来源

### 历史原因建议：`get_suggested_failure_reason`

如果当前失败或超时结果没有填写异常原因，系统会回看同车型同用例最近一次非空 `failure_reason`，作为前端建议值。  
这是一种很实用的知识复用机制，可以减少重复录入。

### 每日明细视图：`list_daily_results`

明细页不是直接查某天存在的结果，而是：

1. 先拿到车型下全部有效用例
2. 再查某天每个用例的最新结果
3. 没有结果的用例默认显示为 `skip`

所以日报页天然是一张“全量用例视图”，而不是“只有执行记录的列表”。

</FocusModuleSection>

<FocusModuleSection
  kicker="Frontend Entry"
  title="前端入口与页面结构"
  summary="前端按主数据管理和日报分析两条主线拆分，和后端模型层级保持一致。"
>

前端主入口包括：

- `web/apps/web-ele/src/views/auto-test-report/vehicle-config/index.vue`
  平台与车型配置页
- `web/apps/web-ele/src/views/auto-test-report/test-cases/index.vue`
  用例管理页，支持导入、导出、批量删除
- `web/apps/web-ele/src/views/auto-test-report/daily-results/index.vue`
  每日执行概览、明细、异常原因编辑
- `web/apps/web-ele/src/views/auto-test-report/components/test-case-history-drawer.vue`
  查看单用例历史执行记录

对应 API 位于 `web/apps/web-ele/src/api/auto-test-report/index.ts`。

其中：

- 车型配置页可以跳转到日报页
- 日报页会展示总览、车型级汇总和用例级明细三层信息
- 失败/超时结果允许在前端补录 `failure_reason`

</FocusModuleSection>

<FocusModuleSection
  kicker="Sequence"
  title="时序图：一次执行结果如何沉淀为日报"
  summary="自动化测试报告的主链是‘外部上报 -> 明细落库 -> 汇总重算 -> 页面回查’。"
>

```mermaid
sequenceDiagram
    participant Client as 测试环境
    participant ReportAPI as Report API
    participant Service as auto_test_report_services
    participant Result as DailyExecutionResult
    participant Batch as DailyExecutionBatch
    participant UI as 日报页面

    Client->>ReportAPI: POST /auto-test-report/report/daily-results
    ReportAPI->>Service: report_daily_results
    Service->>Result: 为每条结果写入执行明细
    Service->>Batch: recalculate_daily_batch
    ReportAPI-->>Client: 返回 created_count / execute_date

    UI->>Service: get_daily_overview / get_daily_summary / list_daily_results
    Service-->>UI: 返回车型汇总、全量概览、用例明细
    UI->>Service: PATCH failure_reason
    Service->>Result: 更新异常原因并保留历史建议逻辑
```

</FocusModuleSection>

<FocusModuleSection
  kicker="Dependencies"
  title="相关依赖与上下游"
  summary="自动化测试报告以车型与用例主数据为上游，以日报分析和问题回溯为下游。"
>

- 上游输入
  测试环境上报的 `vehicle_code + results[]`
- 上游依赖
  平台、车型、测试用例主数据
- 下游消费
  每日执行概览、车型明细、异常原因补录、历史回溯
- 结构特征
  明细与汇总双表并存，汇总由明细重算而来

</FocusModuleSection>

<FocusModuleSection kicker="Core APIs" title="核心 API 清单" summary="以下接口覆盖主数据管理、结果上报、日报汇总与异常原因处理。">

<FocusApiTable :items="apis" />

</FocusModuleSection>

<FocusModuleSection kicker="Related Docs" title="相关文档" summary="继续下钻实现附录可参考这些页面。">

- [后端技术参考](/backend/apps/auto-test-report)
- [前端页面参考](/frontend/views/auto-test-report)
- [项目管理](/modules/project-manager)

</FocusModuleSection>
