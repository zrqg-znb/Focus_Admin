<script lang="ts" setup>
import type { TestCaseHistoryPage } from '#/api/auto-test-report';

import { ref, watch } from 'vue';

import { ElDrawer, ElEmpty, ElLink, ElPagination, ElTag } from 'element-plus';

import { getTestCaseHistoryApi } from '#/api/auto-test-report';

import {
  formatDuration,
  RESULT_LABEL_MAP,
  RESULT_TAG_MAP,
} from '../daily-results/data';

const props = defineProps<{
  caseId: string;
  title: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean];
}>();

const rows = ref<TestCaseHistoryPage['items']>([]);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

async function loadHistory() {
  if (!props.caseId) {
    rows.value = [];
    total.value = 0;
    return;
  }
  const pageData = await getTestCaseHistoryApi(
    props.caseId,
    page.value,
    pageSize.value,
  );
  rows.value = pageData.items || [];
  total.value = pageData.total || 0;
}

watch(
  () => [props.visible, props.caseId],
  async ([visible]) => {
    if (!visible) {
      return;
    }
    page.value = 1;
    await loadHistory();
  },
);
</script>

<template>
  <ElDrawer
    :model-value="visible"
    :title="title"
    size="40%"
    @update:model-value="emit('update:visible', $event)"
  >
    <div class="space-y-3">
      <div v-if="rows.length === 0"><ElEmpty description="暂无历史记录" /></div>
      <div
        v-for="item in rows"
        :key="item.id"
        class="rounded-lg border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)] p-4 shadow-sm transition-shadow hover:shadow-md"
      >
        <div class="mb-2 flex items-center justify-between">
          <div class="text-base font-semibold">{{ item.execute_date }}</div>
          <ElTag :type="RESULT_TAG_MAP[item.status]">
            {{ RESULT_LABEL_MAP[item.status] }}
          </ElTag>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm text-gray-500">
          <div>开始时间：{{ item.start_time || '-' }}</div>
          <div>执行时长：{{ formatDuration(item.duration_seconds) }}</div>
          <div>上报时间：{{ item.reported_at || '-' }}</div>
          <div>
            运行日志：
            <ElLink
              v-if="item.log_url"
              :href="item.log_url"
              target="_blank"
              type="primary"
            >
              查看
            </ElLink>
            <span v-else>-</span>
          </div>
        </div>
      </div>
      <div class="flex justify-end">
        <ElPagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="prev, pager, next, total"
          :page-sizes="[10, 20, 50]"
          :total="total"
          @current-change="loadHistory"
          @size-change="loadHistory"
        />
      </div>
    </div>
  </ElDrawer>
</template>
