<script lang="ts" setup>
import { computed } from 'vue';
import type { QGNode } from '#/api/dashboard';
import { ElTooltip } from 'element-plus';

const props = defineProps<{
  milestones: QGNode[];
}>();

// 根据状态获取颜色
function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-green-500 border-green-200';
    case 'pending':
      return 'bg-blue-500 border-blue-200';
    case 'delayed':
      return 'bg-red-500 border-red-200';
    default:
      return 'bg-gray-300 border-gray-100';
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'completed':
      return '已完成';
    case 'pending':
      return '进行中';
    case 'delayed':
      return '已延期';
    default:
      return '未知';
  }
}

// 计算时间轴位置
// 假设总长度 100%，根据 index 均匀分布，或者根据日期计算
// 这里简化为均匀分布，首尾留出空间
const timelineItems = computed(() => {
  const count = props.milestones.length;
  if (count === 0) return [];
  
  return props.milestones.map((ms, index) => {
    // 均匀分布：0% 到 100%
    // 例如 3个点：0%, 50%, 100%
    // 4个点：0%, 33%, 66%, 100%
    const left = count > 1 ? (index / (count - 1)) * 100 : 50;
    
    return {
      ...ms,
      left: `${left}%`,
      colorClass: getStatusColor(ms.status),
      label: getStatusLabel(ms.status)
    };
  });
});
</script>

<template>
  <div class="relative h-20 w-full pt-8 px-4">
    <!-- 背景线 -->
    <div class="absolute left-4 right-4 top-[39px] h-0.5 bg-gray-200 dark:bg-gray-700"></div>
    
    <!-- 节点 -->
    <div 
      v-for="(item, index) in timelineItems" 
      :key="index"
      class="absolute top-8 -ml-2 flex flex-col items-center"
      :style="{ left: item.left }"
    >
      <ElTooltip
        effect="dark"
        :content="`${item.name} (${item.date}) - ${item.label}`"
        placement="top"
      >
        <div 
          class="h-4 w-4 rounded-full border-2 bg-white transition-all hover:scale-125 cursor-pointer z-10 box-content"
          :class="[item.colorClass]"
        ></div>
      </ElTooltip>
      <div class="mt-2 text-xs font-medium text-gray-500 whitespace-nowrap">
        {{ item.name }}
      </div>
    </div>
  </div>
</template>
