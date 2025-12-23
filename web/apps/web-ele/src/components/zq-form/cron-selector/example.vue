<template>
  <div class="cron-example">
    <h1>Cron 选择器示例</h1>

    <!-- 基础用法 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>基础用法</span>
          <div class="demo-code">基础配置，隐藏秒和年</div>
        </div>
      </template>
      <div class="demo-content">
        <CronSelector
          v-model="basicCron"
          placeholder="输入或编辑Cron表达式"
        />
        <div class="demo-result">
          <p><strong>当前表达式:</strong> {{ basicCron }}</p>
          <p><strong>说明:</strong> 每天晚上 8 点执行</p>
        </div>
      </div>
    </el-card>

    <!-- 支持秒 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>支持秒</span>
          <div class="demo-code">显示秒配置</div>
        </div>
      </template>
      <div class="demo-content">
        <CronSelector
          v-model="secondCron"
          :hideSecond="false"
          placeholder="包含秒的Cron表达式"
        />
        <div class="demo-result">
          <p><strong>当前表达式:</strong> {{ secondCron }}</p>
          <p><strong>说明:</strong> 每分钟的第 0 秒执行</p>
        </div>
      </div>
    </el-card>

    <!-- 支持秒和年 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>支持秒和年</span>
          <div class="demo-code">精确到年</div>
        </div>
      </template>
      <div class="demo-content">
        <CronSelector
          v-model="precisionCron"
          :hideSecond="false"
          :hideYear="false"
          placeholder="最完整的Cron表达式"
        />
        <div class="demo-result">
          <p><strong>当前表达式:</strong> {{ precisionCron }}</p>
          <p><strong>说明:</strong> 仅在 2024 年执行</p>
        </div>
      </div>
    </el-card>

    <!-- 禁用状态 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>禁用状态</span>
          <div class="demo-code">不可编辑</div>
        </div>
      </template>
      <div class="demo-content">
        <CronSelector
          v-model="disabledCron"
          :disabled="true"
          placeholder="已禁用"
        />
        <div class="demo-result">
          <p><strong>当前表达式:</strong> {{ disabledCron }}</p>
          <p><strong>说明:</strong> 此组件已被禁用</p>
        </div>
      </div>
    </el-card>

    <!-- 常见表达式示例 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>快速选择</span>
          <div class="demo-code">常见的Cron表达式</div>
        </div>
      </template>
      <div class="demo-content">
        <div class="quick-select">
          <el-button @click="basicCron = '* * * * *'">每分钟</el-button>
          <el-button @click="basicCron = '0 * * * *'">每小时</el-button>
          <el-button @click="basicCron = '0 0 * * *'">每天</el-button>
          <el-button @click="basicCron = '0 8 * * 1-5'">工作日 8 点</el-button>
          <el-button @click="basicCron = '0 0 1 * *'">每月 1 号</el-button>
          <el-button @click="basicCron = '0 0 * * 0'">每周日</el-button>
          <el-button @click="basicCron = '0/15 * * * *'">每 15 分钟</el-button>
        </div>
      </div>
    </el-card>

    <!-- Cron 表达式说明 -->
    <el-card class="example-card">
      <template #header>
        <div class="card-header">
          <span>Cron 表达式说明</span>
        </div>
      </template>
      <div class="demo-content">
        <el-table :data="cronExpressions" stripe style="width: 100%">
          <el-table-column prop="description" label="描述" width="200" />
          <el-table-column prop="expression" label="表达式" width="200" />
          <el-table-column prop="explanation" label="解释" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="basicCron = row.expression">
                使用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElCard, ElButton, ElTable, ElTableColumn } from 'element-plus';
import { CronSelector } from './index';

const basicCron = ref('0 20 * * *');
const secondCron = ref('0 0 * * * * *');
const precisionCron = ref('0 0 0 1 1 * 2024');
const disabledCron = ref('0 0 * * *');

const cronExpressions = [
  {
    description: '每分钟',
    expression: '* * * * *',
    explanation: '在每一分钟的每一秒执行',
  },
  {
    description: '每小时',
    expression: '0 * * * *',
    explanation: '在每一小时的整点执行',
  },
  {
    description: '每天午夜',
    expression: '0 0 * * *',
    explanation: '每天凌晨 00:00 执行',
  },
  {
    description: '每周一 8 点',
    expression: '0 8 * * 1',
    explanation: '每周一上午 8:00 执行',
  },
  {
    description: '每月 1 号',
    expression: '0 0 1 * *',
    explanation: '每个月的第 1 天凌晨 00:00 执行',
  },
  {
    description: '工作日 9 点',
    expression: '0 9 * * 1-5',
    explanation: '周一到周五上午 9:00 执行',
  },
  {
    description: '每 15 分钟',
    expression: '0/15 * * * *',
    explanation: '从 00 分开始，每隔 15 分钟执行',
  },
  {
    description: '每两小时',
    expression: '0 0/2 * * *',
    explanation: '从 00 时开始，每隔 2 小时执行',
  },
  {
    description: '午餐时间',
    expression: '0 12,18 * * *',
    explanation: '每天中午 12 点和晚上 6 点执行',
  },
  {
    description: '范围',
    expression: '0 9-17 * * *',
    explanation: '每天 9 点到 17 点每小时执行',
  },
];
</script>

<style scoped lang="css">
.cron-example {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.cron-example h1 {
  margin-bottom: 30px;
  color: #333;
}

.example-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.demo-code {
  color: #909399;
  font-size: 12px;
}

.demo-content {
  padding: 16px;
}

.demo-result {
  margin-top: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

.demo-result p {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
}

.demo-result strong {
  color: #333;
}

.quick-select {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

:deep(.el-button) {
  flex: 0 0 auto;
}
</style>

