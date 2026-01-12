<script lang="ts" setup>
import type { DtsSummary } from '#/api/dashboard';
import { useRouter } from 'vue-router';
import { ElLink } from 'element-plus';

defineProps<{
  data: DtsSummary;
}>();

const router = useRouter();

function goToDts() {
  router.push('/project-manager/dts');
}
</script>

<template>
  <div
    class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
  >
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center">
        <div class="mr-3 rounded-lg bg-red-50 p-2 dark:bg-red-900/20">
          <span class="text-xl font-bold text-red-500">DTS</span>
        </div>
        <h3 class="text-lg font-bold">问题单监控</h3>
      </div>
      <ElLink type="primary" :underline="false" @click="goToDts">更多 ></ElLink>
    </div>

    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <span class="text-gray-500 dark:text-gray-400">总问题数</span>
        <span class="text-lg font-semibold">{{ data.total_issues }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-gray-500 dark:text-gray-400">严重问题数</span>
        <span
          class="text-lg font-bold"
          :class="data.critical_issues > 0 ? 'text-red-500' : 'text-green-500'"
        >
          {{ data.critical_issues }}
        </span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-gray-500 dark:text-gray-400">平均解决时长</span>
        <span class="font-medium">{{ data.avg_solve_time }} 天</span>
      </div>
      <div class="mt-2">
        <div class="mb-2 flex justify-between text-sm">
          <span class="text-gray-500 dark:text-gray-400">解决率</span>
          <span class="font-bold">{{ data.solve_rate }}%</span>
        </div>
        <div class="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700">
          <div
            class="h-2 rounded-full transition-all duration-500"
            :class="
              data.solve_rate >= 80 ? 'bg-green-500' : data.solve_rate >= 60 ? 'bg-orange-500' : 'bg-red-500'
            "
            :style="{ width: `${data.solve_rate}%` }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>
