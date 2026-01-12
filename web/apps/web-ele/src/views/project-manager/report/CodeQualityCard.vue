<script lang="ts" setup>
import type { CodeQualitySummary } from '#/api/project-manager/report';
import { IconifyIcon } from '@vben/icons';

defineProps<{
  data: CodeQualitySummary;
}>();
</script>

<template>
  <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515] hover:shadow-md transition-shadow">
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
         <div class="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
            <IconifyIcon icon="lucide:code-2" class="text-blue-500 text-xl" />
         </div>
         <div>
            <h3 class="text-base font-bold text-gray-800 dark:text-white">代码质量</h3>
            <p class="text-xs text-gray-400">代码静态分析结果</p>
         </div>
      </div>
      <div class="flex items-baseline gap-1">
         <span class="text-3xl font-bold text-green-600 dark:text-green-500">{{ data.health_score }}</span>
         <span class="text-xs text-gray-400">分</span>
      </div>
    </div>
    
    <div class="grid grid-cols-4 gap-2 mb-6">
       <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">LOC</span>
          <span class="text-sm font-bold font-mono text-gray-700 dark:text-gray-200">{{ (data.total_loc / 1000).toFixed(1) }}k</span>
       </div>
       <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Modules</span>
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ data.total_modules }}</span>
       </div>
       <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Issues</span>
          <span class="text-sm font-bold" :class="data.total_issues > 0 ? 'text-red-500' : 'text-gray-700 dark:text-gray-200'">{{ data.total_issues }}</span>
       </div>
       <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Dup</span>
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ data.avg_duplication_rate }}%</span>
       </div>
    </div>
    
    <div class="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-xl flex items-start gap-3 border border-blue-100 dark:border-blue-900/20">
       <IconifyIcon icon="lucide:info" class="text-blue-500 mt-0.5 flex-shrink-0" />
       <div class="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
          <p v-if="data.health_score >= 80">代码质量整体表现优秀，请继续保持较低的重复率和问题数。</p>
          <p v-else-if="data.health_score >= 60">代码质量尚可，建议关注高重复率模块和潜在的安全风险。</p>
          <p v-else>代码质量堪忧，存在较多阻断性问题，建议立即安排重构或修复计划。</p>
       </div>
    </div>
  </div>
</template>
