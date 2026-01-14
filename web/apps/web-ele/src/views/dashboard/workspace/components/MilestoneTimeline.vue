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
    const left = count > 1 ? (index / (count - 1)) * 100 : 50;
    
    return {
      ...ms,
      left: `${left}%`,
      colorClass: getStatusColor(ms.status),
      label: getStatusLabel(ms.status)
    };
  });
});

const todayPosition = computed(() => {
  const count = props.milestones.length;
  if (count < 2) return null;

  const now = new Date().getTime();
  // 确保按日期排序
  const sortedMs = [...props.milestones].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  
  // 找到第一个比现在大的节点
  const nextIndex = sortedMs.findIndex(ms => new Date(ms.date).getTime() > now);
  
  let percent = 0;
  
  if (nextIndex === 0) {
    // 在第一个节点之前
    percent = 0;
  } else if (nextIndex === -1) {
    // 在最后一个节点之后
    percent = 100;
  } else {
    // 在 prevIndex 和 nextIndex 之间
    const prevIndex = nextIndex - 1;
    const prevMs = sortedMs[prevIndex]!;
    const nextMs = sortedMs[nextIndex]!;
    
    const prevTime = new Date(prevMs.date).getTime();
    const nextTime = new Date(nextMs.date).getTime();
    
    // 避免除以零
    if (nextTime === prevTime) {
       percent = (prevIndex / (count - 1)) * 100;
    } else {
        const timeRatio = (now - prevTime) / (nextTime - prevTime);
        const gapPercent = 100 / (count - 1);
        const prevUiPos = (prevIndex / (count - 1)) * 100;
        
        percent = prevUiPos + (gapPercent * timeRatio);
    }
  }
  
  return `${Math.max(0, Math.min(100, percent))}%`;
});
</script>

<template>
  <div class="relative h-20 w-full pt-8">
    <div class="absolute left-4 right-4 top-0 bottom-0">
      <!-- 背景线 -->
      <div class="absolute left-0 right-0 top-[39px] h-0.5 bg-gray-200 dark:bg-gray-700"></div>
      
      <!-- Today Flag (Global) -->
      <div 
         v-if="todayPosition" 
         class="absolute top-2 z-20 flex flex-col items-center pointer-events-none -translate-x-1/2"
         :style="{ left: todayPosition }" 
      >
         <div class="px-1.5 py-0.5 bg-red-500 text-white text-[10px] rounded shadow-sm whitespace-nowrap">Today</div>
         <div class="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[4px] border-t-red-500"></div>
         <div class="w-0.5 h-6 bg-red-500/50 mt-1"></div>
      </div>
      
      <!-- 节点 -->
      <div 
        v-for="(item, index) in timelineItems" 
        :key="index"
        class="absolute top-8 flex flex-col items-center group -translate-x-1/2"
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
  </div>
</template>
