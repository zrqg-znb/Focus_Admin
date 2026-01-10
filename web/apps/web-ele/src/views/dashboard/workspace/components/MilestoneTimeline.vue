<script lang="ts" setup>
import { computed, type PropType } from 'vue';
import type { QGNode } from '#/api/dashboard';
import { IconifyIcon } from '@vben/icons';

const props = defineProps({
  milestones: {
    type: Array as PropType<QGNode[]>,
    default: () => [],
  },
});

const sortedMilestones = computed(() => {
  return [...props.milestones].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
});

// 计算“今天”在时间轴上的相对位置 (0-100)
// 考虑到节点是等间距分布的 (justify-between)，时间轴是非线性的
// 我们需要先找到“今天”落在哪两个节点之间，再计算区间内的进度
const relativePosition = computed(() => {
  const milestones = sortedMilestones.value;
  if (milestones.length < 2) return -1;

  const today = new Date().getTime();

  // 1. 如果在第一个节点之前
  if (today < new Date(milestones[0]!.date).getTime()) {
    return 0;
  }

  // 2. 如果在最后一个节点之后
  if (today > new Date(milestones[milestones.length - 1]!.date).getTime()) {
    return 100;
  }

  // 3. 找到所在的区间
  const totalSegments = milestones.length - 1;
  const segmentWidth = 100 / totalSegments;

  for (let i = 0; i < totalSegments; i++) {
    const startNode = milestones[i]!;
    const endNode = milestones[i+1]!;

    const startTime = new Date(startNode.date).getTime();
    const endTime = new Date(endNode.date).getTime();

    if (today >= startTime && today <= endTime) {
      // 计算区间内的进度 (0-1)
      const segmentDuration = endTime - startTime;
      const elapsedInSegment = today - startTime;
      const progressInSegment = segmentDuration > 0 ? elapsedInSegment / segmentDuration : 1;

      // 映射到总进度
      // 位置 = (当前段索引 * 段宽) + (段内进度 * 段宽)
      return (i * segmentWidth) + (progressInSegment * segmentWidth);
    }
  }

  return 0;
});

function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-green-500 border-green-500';
    case 'delayed':
      return 'bg-red-500 border-red-500';
    default:
      return 'bg-gray-300 border-gray-300 dark:bg-gray-600 dark:border-gray-600';
  }
}

// 格式化今天的日期 YYYY-MM-DD
const todayStr = new Date().toISOString().split('T')[0];
</script>

<template>
  <div class="relative w-full h-24 flex items-center px-8 overflow-x-auto hide-scrollbar">
    <!-- 背景线 (绳子) -->
    <div class="absolute left-8 right-8 top-1/2 h-1 bg-gray-200 dark:bg-gray-700 -translate-y-1/2 rounded-full"></div>

    <!-- 今天指示器 (小旗子) -->
    <div class="absolute left-8 right-8 top-0 bottom-0 pointer-events-none">
       <!--
          为了让指示器准确显示在非线性时间轴（等间距节点）上，我们需要计算它在第几个区间。
          例如：如果在 Node1(index 0) 和 Node2(index 1) 之间，且时间过了 50%，那位置就是 (0.5 / (N-1)) * 100%。
       -->
       <div
          v-if="relativePosition >= 0"
          class="absolute top-1/2 -translate-y-1/2 z-20 flex flex-col items-center -ml-3"
          :style="{ left: `${relativePosition}%` }"
       >
          <div class="text-[10px] font-bold text-blue-500 mb-1 bg-blue-50 dark:bg-blue-900/30 px-1 rounded whitespace-nowrap">
            Today
          </div>
          <div class="h-8 border-l border-dashed border-blue-500"></div>
          <div class="w-2 h-2 rounded-full bg-blue-500 -mt-1"></div>
       </div>
    </div>

    <!-- 节点 (绳结) -->
    <div class="relative w-full flex justify-between min-w-[300px] z-10">
      <div
        v-for="(node, index) in sortedMilestones"
        :key="index"
        class="relative flex flex-col items-center group cursor-pointer"
      >
        <ElTooltip
           effect="dark"
           placement="top"
        >
           <template #content>
              <div class="text-center">
                 <div class="font-bold">{{ node.name }}</div>
                 <div class="text-xs text-gray-300">{{ node.date }}</div>
                 <div class="mt-1">
                    <span
                       class="px-1.5 py-0.5 rounded text-[10px]"
                       :class="node.status === 'completed' ? 'bg-green-500 text-white' : (node.status === 'delayed' ? 'bg-red-500 text-white' : 'bg-gray-500 text-white')"
                    >
                       {{ node.status === 'completed' ? '已完成' : (node.status === 'delayed' ? '已延期' : '进行中') }}
                    </span>
                 </div>
              </div>
           </template>

           <!-- 绳结圆点 -->
           <div
             class="w-4 h-4 rounded-full border-2 z-10 transition-all duration-300 group-hover:scale-125 bg-white dark:bg-[#151515]"
             :class="getStatusColor(node.status)"
           ></div>
        </ElTooltip>

        <!-- 简略标签 -->
        <div class="absolute -top-6 text-xs font-bold text-gray-600 dark:text-gray-400 whitespace-nowrap">
          {{ node.name }}
        </div>
      </div>
    </div>

  </div>
</template>

<script lang="ts">
// 辅助逻辑：计算非线性时间轴位置
// 假设节点在父容器中是均匀分布的 (justify-between)
// 那么总宽度被分成了 N-1 段。
// 我们先找到今天在哪两个节点之间，算出该段内的进度，再映射到总百分比。
</script>

<style scoped>
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.dashed {
    border-left: 1px dashed currentColor;
    background: transparent;
}
</style>
