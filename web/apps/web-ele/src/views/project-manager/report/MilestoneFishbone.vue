<script lang="ts" setup>
import type { QGNode } from '#/api/project-manager/report';
import { computed } from 'vue';
import { ElTooltip } from 'element-plus';

const props = defineProps<{
  milestones: QGNode[];
}>();

// Fishbone Logic
// We will alternate items top and bottom
const fishboneItems = computed(() => {
  return props.milestones.map((ms, index) => {
    return {
      ...ms,
      isTop: index % 2 === 0,
      left: `${(index / (props.milestones.length - 1 || 1)) * 90 + 5}%` // Distributed 5% to 95%
    };
  });
});

function getStatusColor(status: string) {
  switch (status) {
    case 'completed': return 'bg-green-500 border-green-200';
    case 'pending': return 'bg-blue-500 border-blue-200';
    case 'delayed': return 'bg-red-500 border-red-200';
    default: return 'bg-gray-300';
  }
}
</script>

<template>
  <div class="h-full w-full flex items-center px-4 relative">
      <!-- Main Axis -->
      <div class="absolute w-[calc(100%-48px)] left-6 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full z-0">
         <div class="absolute right-0 -top-1.5 w-0 h-0 border-l-[12px] border-l-gray-100 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent dark:border-l-gray-700"></div>
      </div>
      
      <!-- Nodes -->
      <div v-for="(item, index) in fishboneItems" :key="index" 
           class="absolute h-full flex flex-col items-center justify-center transition-all group hover:z-20"
           :style="{ left: item.left }">
           
         <!-- Connection Line (Top) -->
         <div v-if="item.isTop" class="absolute bottom-[50%] h-12 w-0.5 bg-gray-200 dark:bg-gray-600 origin-bottom -rotate-[20deg] translate-x-3 group-hover:bg-primary transition-colors"></div>
         
         <!-- Connection Line (Bottom) -->
         <div v-if="!item.isTop" class="absolute top-[50%] h-12 w-0.5 bg-gray-200 dark:bg-gray-600 origin-top rotate-[20deg] translate-x-3 group-hover:bg-primary transition-colors"></div>
         
         <!-- Content Bubble -->
         <div class="absolute w-28 p-2 rounded-xl border bg-white dark:bg-gray-800 shadow-sm text-center z-10 transition-all duration-300 hover:shadow-md hover:scale-110 cursor-default"
              :class="[
                  item.isTop ? 'bottom-[65%]' : 'top-[65%]',
                  item.status === 'delayed' ? 'border-red-200 bg-red-50 dark:bg-red-900/20' : 'border-gray-200 dark:border-gray-700'
              ]">
            <div class="text-xs font-bold truncate text-gray-800 dark:text-gray-100" :title="item.name">{{ item.name }}</div>
            <div class="text-[10px] text-gray-400 mt-0.5 font-mono">{{ item.date }}</div>
            <div class="mt-1.5 h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div class="h-full w-full transition-all duration-500" :class="getStatusColor(item.status).split(' ')[0]"></div>
            </div>
         </div>
         
         <!-- Axis Point -->
         <div class="w-3.5 h-3.5 rounded-full border-[3px] bg-white z-10 transition-all group-hover:scale-125 group-hover:border-primary" 
              :class="item.status === 'delayed' ? 'border-red-400' : 'border-gray-300 dark:border-gray-500'"></div>
      </div>
  </div>
</template>
