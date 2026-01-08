<script lang="ts" setup>
import { computed } from 'vue';
import { ElTooltip } from 'element-plus';
import { IconifyIcon } from '@vben/icons';

const props = defineProps({
  // 指标名称
  title: {
    type: String,
    required: true,
  },
  // 指标定义
  definition: {
    type: String,
    required: true,
  },
  // 计算规则
  rule: {
    type: String,
    required: true,
  },
  // 图标大小
  iconSize: {
    type: Number,
    default: 14,
  },
});
</script>

<template>
  <div class="inline-flex items-center gap-1 cursor-help group">
    <span>{{ title }}</span>
    
    <ElTooltip placement="top" effect="custom">
      <template #content>
        <div class="max-w-md p-1">
          <div class="grid grid-cols-[80px_1fr] gap-x-4 gap-y-2 text-sm">
            <div class="font-bold text-right text-gray-500 dark:text-gray-400">指标定义</div>
            <div class="text-gray-900 dark:text-gray-100">{{ definition }}</div>
            
            <div class="font-bold text-right text-gray-500 dark:text-gray-400">计算规则</div>
            <div class="text-gray-900 dark:text-gray-100 font-mono text-xs bg-gray-50 dark:bg-gray-800 p-1 rounded">{{ rule }}</div>
          </div>
        </div>
      </template>
      
      <IconifyIcon 
        icon="ep:question-filled" 
        class="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
        :style="{ fontSize: `${iconSize}px` }"
      />
    </ElTooltip>
  </div>
</template>

<style>
/* 
  自定义 Element Plus Tooltip 主题 
  使其背景色跟随当前亮色/暗色模式，而不是默认的黑色
*/
.el-popper.is-custom {
  /* 覆盖默认的黑色背景 */
  background: var(--el-bg-color) !important;
  border: 1px solid var(--el-border-color-light) !important;
  color: var(--el-text-color-primary) !important;
  box-shadow: var(--el-box-shadow-light) !important;
}

.el-popper.is-custom .el-popper__arrow::before {
  background: var(--el-bg-color) !important;
  border: 1px solid var(--el-border-color-light) !important;
}

/* 暗黑模式适配 (如果 Element Plus 的 CSS 变量未自动生效) */
html.dark .el-popper.is-custom {
  background: #1d1e1f !important;
  border-color: #414243 !important;
  color: #cfd3dc !important;
}

html.dark .el-popper.is-custom .el-popper__arrow::before {
  background: #1d1e1f !important;
  border-color: #414243 !important;
}
</style>
