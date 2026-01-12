<script lang="ts" setup>
import type { IterationSummary } from '#/api/project-manager/report';
import { IconifyIcon } from '@vben/icons';

defineProps<{
  data: IterationSummary;
}>();
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
  </div>
</template>
