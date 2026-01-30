# 绩效管理页面

## 页面列表

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 指标管理 | /performance/indicator | 绩效指标配置 |
| 数据导入 | /performance/import | 绩效数据导入 |
| 统计分析 | /performance/statistics | 绩效统计分析 |

## 统计分析页面

绩效统计页面展示各项指标的统计数据和图表。

```vue
<template>
  <Page>
    <!-- 筛选条件 -->
    <div class="filter-bar">
      <el-date-picker v-model="period" type="month" />
      <el-select v-model="deptId" placeholder="选择部门">
        <el-option
          v-for="dept in deptList"
          :key="dept.id"
          :label="dept.name"
          :value="dept.id"
        />
      </el-select>
      <el-button type="primary" @click="loadData">查询</el-button>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <StatCard title="总分" :value="summary.totalScore" />
      </el-col>
      <el-col :span="6">
        <StatCard title="排名" :value="summary.rank" />
      </el-col>
    </el-row>
    
    <!-- 图表 -->
    <el-card>
      <div ref="chartRef" style="height: 400px" />
    </el-card>
  </Page>
</template>
```
