<script lang="ts" setup>
import type { PropType } from 'vue';
import type { UpcomingMilestone } from '#/api/dashboard';

defineProps({
  milestones: {
    type: Array as PropType<UpcomingMilestone[]>,
    default: () => [],
  },
});
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-xs text-gray-500 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
        <tr>
          <th scope="col" class="px-6 py-3">项目名称</th>
          <th scope="col" class="px-6 py-3">项目经理</th>
          <th scope="col" class="px-6 py-3">即将到达节点</th>
          <th scope="col" class="px-6 py-3">节点日期</th>
          <th scope="col" class="px-6 py-3 text-center">剩余天数</th>
        </tr>
      </thead>
      <tbody>
        <tr 
          v-for="(item, index) in milestones" 
          :key="index"
          class="bg-white border-b dark:bg-[#151515] dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        >
          <td class="px-6 py-4 font-medium text-gray-900 dark:text-white whitespace-nowrap">
            {{ item.project_name }}
          </td>
          <td class="px-6 py-4">
            {{ item.project_manager }}
          </td>
          <td class="px-6 py-4">
            <span class="px-2 py-1 text-xs font-semibold text-blue-600 bg-blue-100 rounded-full dark:bg-blue-900/30 dark:text-blue-400">
              {{ item.qg_name }}
            </span>
          </td>
          <td class="px-6 py-4 font-mono text-gray-500">
            {{ item.qg_date }}
          </td>
          <td class="px-6 py-4 text-center">
            <span 
              class="font-bold text-lg"
              :class="item.days_left <= 7 ? 'text-red-500' : 'text-green-500'"
            >
              {{ item.days_left }}
            </span>
          </td>
        </tr>
        <tr v-if="milestones.length === 0">
          <td colspan="5" class="px-6 py-8 text-center text-gray-500">
            暂无未来30天内的重要节点
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
