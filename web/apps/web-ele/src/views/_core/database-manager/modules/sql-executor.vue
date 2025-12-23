<script setup lang="ts">
import { ref } from 'vue';
import {
  ElCard,
  ElButton,
  ElTable,
  ElTableColumn,
  ElAlert,
  ElMessage,
} from 'element-plus';
import { Zap } from '@vben/icons';
import { executeSQLApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';
import type { ExecuteSQLResponse } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const sqlText = ref('');
const executing = ref(false);
const result = ref<ExecuteSQLResponse | null>(null);

// 执行SQL
async function executeSQL() {
  if (!sqlText.value.trim()) {
    ElMessage.warning('请输入SQL语句');
    return;
  }

  if (!props.node.meta?.dbName) {
    ElMessage.error('无效的数据库连接');
    return;
  }

  executing.value = true;
  result.value = null;

  try {
    const sql = sqlText.value.trim();
    const isQuery = /^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\s+/i.test(sql);

    const data = await executeSQLApi(props.node.meta.dbName, {
      sql,
      is_query: isQuery,
    });

    result.value = data;

    if (data.success) {
      ElMessage.success(data.message || '执行成功');
    } else {
      ElMessage.error(data.message || '执行失败');
    }
  } catch (error: any) {
    console.error('Failed to execute SQL:', error);
    ElMessage.error(error.message || 'SQL执行失败');
  } finally {
    executing.value = false;
  }
}

// 清空
function clearSQL() {
  sqlText.value = '';
  result.value = null;
}

// 示例SQL
function loadExample() {
  if (props.node.meta?.table) {
    sqlText.value = `SELECT * FROM ${props.node.meta.schema ? props.node.meta.schema + '.' : ''}${props.node.meta.table} LIMIT 10;`;
  } else {
    sqlText.value = 'SELECT 1;';
  }
}
</script>

<template>
  <div class="h-full flex flex-col gap-3">
    <!-- SQL编辑器 -->
    <ElCard shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-semibold">SQL编辑器</span>
          <div class="flex gap-2">
            <ElButton size="small" @click="loadExample">加载示例</ElButton>
            <ElButton size="small" @click="clearSQL">清空</ElButton>
            <ElButton
              type="primary"
              size="small"
              @click="executeSQL"
              :loading="executing"
            >
              <Zap :size="14" />
              <span class="ml-1">执行</span>
            </ElButton>
          </div>
        </div>
      </template>

      <textarea
        v-model="sqlText"
        class="w-full h-48 p-3 font-mono text-sm border rounded resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        placeholder="输入SQL语句...&#10;&#10;示例:&#10;SELECT * FROM users WHERE id > 100;&#10;UPDATE users SET status = 'active' WHERE id = 1;&#10;DELETE FROM users WHERE id = 999;"
        spellcheck="false"
      />
    </ElCard>

    <!-- 执行结果 -->
    <ElCard v-if="result" shadow="never" class="flex-1">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-semibold">执行结果</span>
          <span class="text-sm text-gray-500">
            执行时间: {{ result.execution_time?.toFixed(2) }}ms
          </span>
        </div>
      </template>

      <!-- 成功提示 -->
      <ElAlert
        v-if="result.success && !result.rows"
        type="success"
        :closable="false"
        class="mb-3"
      >
        <template #title>
          <div>{{ result.message }}</div>
          <div v-if="result.affected_rows !== undefined" class="text-sm mt-1">
            影响行数: {{ result.affected_rows }}
          </div>
        </template>
      </ElAlert>

      <!-- 错误提示 -->
      <ElAlert
        v-if="!result.success"
        type="error"
        :closable="false"
        class="mb-3"
      >
        <template #title>
          <div class="font-mono text-sm">{{ result.message }}</div>
        </template>
      </ElAlert>

      <!-- 查询结果表格 -->
      <div v-if="result.success && result.rows && result.rows.length > 0">
        <div class="mb-2 text-sm text-gray-500">
          返回 {{ result.rows.length }} 行记录
        </div>
        <ElTable
          :data="result.rows"
          stripe
          border
          max-height="400"
          style="width: 100%"
        >
          <ElTableColumn
            v-for="column in result.columns || []"
            :key="column"
            :prop="column"
            :label="column"
            min-width="120"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span v-if="row[column] === null" class="text-gray-400 italic">NULL</span>
              <span v-else>{{ row[column] }}</span>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>

      <!-- 无结果 -->
      <div
        v-if="result.success && result.rows && result.rows.length === 0"
        class="text-center text-gray-400 py-8"
      >
        查询成功，但没有返回数据
      </div>
    </ElCard>

    <!-- 提示信息 -->
    <ElCard v-else shadow="never" class="flex-1">
      <div class="flex flex-col items-center justify-center h-full text-gray-400">
        <Zap :size="48" class="mb-4 opacity-50" />
        <div class="text-sm">在上方输入SQL语句并点击"执行"按钮</div>
        <div class="text-xs mt-2">
          ⚠️ 请谨慎执行UPDATE、DELETE等修改数据的语句
        </div>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
}
</style>
