<script lang="ts" setup>
import type { IterationDetailMetrics, IterationSummary } from '#/api/project-manager/report';
import { IconifyIcon } from '@vben/icons';
import { ElButton } from 'element-plus';
import { computed, ref } from 'vue';

const props = defineProps<{
  data: IterationSummary;
  detail?: IterationDetailMetrics | null;
}>();

const detailVisible = ref(false);

const rateRows = computed(() => {
  if (!props.detail) return [];
  return [
    { label: '分解率', items: [
      { name: 'DR', value: props.detail.dr_breakdown_rate },
      { name: 'SR', value: props.detail.sr_breakdown_rate },
    ]},
    { label: '置A率', items: [
      { name: 'DR', value: props.detail.dr_set_a_rate },
      { name: 'AR', value: props.detail.ar_set_a_rate },
    ]},
    { label: '置C率(C+A)', items: [
      { name: 'DR', value: props.detail.dr_set_c_rate },
      { name: 'AR', value: props.detail.ar_set_c_rate },
    ]},
  ];
});

function fmtRate(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}
</script>

<template>
  <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515] hover:shadow-md transition-shadow">
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center">
          <IconifyIcon icon="lucide:layers" class="text-purple-500 text-xl" />
        </div>
        <div>
          <h3 class="text-base font-bold text-gray-800 dark:text-white">健康迭代</h3>
          <p class="text-xs text-gray-400">当前迭代周期概览</p>
        </div>
      </div>
      <div class="px-3 py-1 rounded-full bg-green-50 text-green-600 text-xs font-bold dark:bg-green-900/20">
        {{ data.completion_rate }}% 完成度
      </div>
    </div>
    
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="flex flex-col items-center p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
        <span class="text-xs text-gray-400 mb-1">活跃迭代</span>
        <span class="text-xl font-bold text-gray-800 dark:text-white">{{ data.active_iterations }}</span>
      </div>
      <div class="flex flex-col items-center p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 relative overflow-hidden">
        <div v-if="data.delayed_iterations > 0" class="absolute top-0 right-0 w-2 h-2 rounded-full bg-red-500"></div>
        <span class="text-xs text-gray-400 mb-1">延期风险</span>
        <span class="text-xl font-bold" :class="data.delayed_iterations > 0 ? 'text-red-500' : 'text-gray-800 dark:text-white'">{{ data.delayed_iterations }}</span>
      </div>
      <div class="flex flex-col items-center p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
        <span class="text-xs text-gray-400 mb-1">总需求数</span>
        <span class="text-xl font-bold text-gray-800 dark:text-white">{{ data.total_req_count }}</span>
      </div>
    </div>
    
    <div class="space-y-2">
      <div class="flex justify-between text-xs text-gray-500">
        <span>迭代进度条</span>
        <span>剩余任务需加紧处理</span>
      </div>
      <div class="h-2.5 w-full bg-gray-100 rounded-full overflow-hidden dark:bg-gray-700">
        <div class="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(168,85,247,0.4)]" :style="{ width: `${data.completion_rate}%` }"></div>
      </div>
    </div>

    <div class="mt-4 flex justify-end">
      <ElButton
        size="small"
        plain
        type="primary"
        @click="detailVisible = !detailVisible"
        :disabled="!props.detail"
      >
        {{ detailVisible ? '收起详情' : '展开详情' }}
      </ElButton>
    </div>

    <transition name="el-collapse-transition">
      <div v-show="detailVisible" class="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-900/20">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-purple-500" />
            <div class="text-sm font-bold text-gray-800 dark:text-gray-100">当前迭代关键指标</div>
          </div>
          <div v-if="props.detail" class="text-xs text-gray-400">
            SR {{ props.detail.sr_num }} · DR {{ props.detail.dr_num }} · AR {{ props.detail.ar_num }}
          </div>
        </div>

        <div class="space-y-3">
          <div v-for="row in rateRows" :key="row.label" class="rounded-xl border border-gray-100 bg-white p-3 dark:border-gray-800 dark:bg-[#151515]">
            <div class="mb-2 flex items-center justify-between">
              <div class="text-xs font-bold text-gray-700 dark:text-gray-200">{{ row.label }}</div>
              <div class="text-[10px] text-gray-400">越高越好</div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div v-for="it in row.items" :key="it.name" class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/50">
                <div class="flex items-center justify-between">
                  <div class="text-xs font-medium text-gray-600 dark:text-gray-300">{{ it.name }}</div>
                  <div class="text-xs font-bold text-gray-900 dark:text-white">{{ fmtRate(it.value) }}</div>
                </div>
                <div class="mt-2 h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div class="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500" :style="{ width: `${it.value * 100}%` }" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>
