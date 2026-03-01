<script setup lang="ts">
import type { MilestoneConfig } from './types';

import type { MilestoneBoardItem } from '#/api/project-manager/milestone';

import { computed, onMounted, onUnmounted, ref } from 'vue';

import { FullScreen } from '@element-plus/icons-vue';
import { useFullscreen } from '@vueuse/core';
import { ElButton, ElButtonGroup, ElIcon } from 'element-plus';

import RiskHandleDialog from './RiskHandleDialog.vue';

interface Props {
  data: MilestoneBoardItem[];
  basePixelsPerDay?: number;
}

const props = withDefaults(defineProps<Props>(), {
  basePixelsPerDay: 5,
});

const emit = defineEmits(['refresh']);

// Risk Handle Dialog
const riskHandleDialogRef = ref();

function handleRiskClick(milestone: any) {
  if (milestone.hasRisk && milestone.riskInfo) {
    // 直接打开风险处理弹窗
    // 这里假设 milestone.riskInfo 包含了 RiskItem 所需的完整信息（特别是 id）
    riskHandleDialogRef.value?.open(milestone.riskInfo, 'handle');
  }
}

function handleRiskSuccess() {
  // 处理成功后刷新数据
  emit('refresh');
}

// 风险信息来自里程碑概览接口返回的 row.risks 字段
function getRiskInfo(row: MilestoneBoardItem, qgKey: string): any | null {
  const risks = (row as any).risks || {};
  const [qgPrefix = ''] = qgKey.split('_');
  const qgName = qgPrefix.toUpperCase();
  if (!qgName) {
    return null;
  }
  const risk = risks[qgName];
  if (risk) {
    return risk;
  }
  return null;
}

// 配置信息
const milestoneConfigs: MilestoneConfig[] = [
  { key: 'qg1_date', label: 'QG1', color: 'var(--milestone-qg1)' },
  { key: 'qg2_date', label: 'QG2', color: 'var(--milestone-qg2)' },
  { key: 'qg3_date', label: 'QG3', color: 'var(--milestone-qg3)' },
  { key: 'qg4_date', label: 'QG4', color: 'var(--milestone-qg4)' },
  { key: 'qg5_date', label: 'QG5', color: 'var(--milestone-qg5)' },
  { key: 'qg6_date', label: 'QG6', color: 'var(--milestone-qg6)' },
  { key: 'qg7_date', label: 'QG7', color: 'var(--milestone-qg7)' },
  { key: 'qg8_date', label: 'QG8', color: 'var(--milestone-qg8)' },
];

// 状态
const zoomLevel = ref(1);
const offsetX = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartOffsetX = ref(0);
const projectColumnWidth = ref(200);
const isResizing = ref(false);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);

const timelineContainerRef = ref<HTMLElement>();
const ganttBodyRef = ref<HTMLElement>();
const ganttContainerRef = ref<HTMLElement>();

const { isFullscreen, toggle: toggleFullscreen } =
  useFullscreen(ganttContainerRef);

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  title: '',
  type: 'segment' as 'milestone' | 'segment',
  content: {} as any,
});

// 计算属性
const pixelsPerDay = computed(() => props.basePixelsPerDay * zoomLevel.value);

const dateRange = computed(() => {
  const dates: number[] = [];
  props.data.forEach((row) => {
    milestoneConfigs.forEach((config) => {
      const dateStr = row[config.key];
      if (dateStr) dates.push(new Date(dateStr).getTime());
    });
  });

  if (dates.length === 0) {
    const today = new Date();
    return {
      start: new Date(today.getFullYear(), today.getMonth() - 1, 1),
      end: new Date(today.getFullYear(), today.getMonth() + 5, 1),
    };
  }

  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);

  const start = new Date(minDate);
  start.setMonth(start.getMonth() - 2);
  const end = new Date(maxDate);
  end.setMonth(end.getMonth() + 2);

  return { start, end };
});

const timelineTotalWidth = computed(() => {
  const start = dateRange.value.start.getTime();
  const end = dateRange.value.end.getTime();
  const days = (end - start) / (1000 * 60 * 60 * 24);
  return days * pixelsPerDay.value;
});

const todayPosition = computed(() => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dateToPosition(today);
});

const timelineScale = computed(() => {
  const scales: Array<{
    isToday: boolean;
    label: string;
    position: number;
    timestamp: number;
  }> = [];

  const start = new Date(dateRange.value.start);
  const end = new Date(dateRange.value.end);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const startMonth = new Date(start);
  startMonth.setDate(1);
  const endTime = end.getTime();
  let cursor = startMonth.getTime();

  while (cursor <= endTime) {
    const current = new Date(cursor);
    const isToday =
      current.getMonth() === today.getMonth() &&
      current.getFullYear() === today.getFullYear();
    scales.push({
      timestamp: current.getTime(),
      position: dateToPosition(current),
      label: `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`,
      isToday,
    });
    current.setMonth(current.getMonth() + 1);
    cursor = current.getTime();
  }
  return scales;
});

const dragBoundary = computed(() => {
  if (!timelineContainerRef.value) return { min: 0, max: 0 };
  const containerWidth = timelineContainerRef.value.clientWidth;
  // 最小偏移：让时间轴右端不要离开容器左侧太远，或者让右端对齐
  // 简单处理：最小偏移是 (containerWidth - totalWidth)，如果 totalWidth > containerWidth
  const minOffset = Math.min(0, containerWidth - timelineTotalWidth.value);
  const maxOffset = 0;
  return { min: minOffset, max: maxOffset };
});

// 方法
function dateToPosition(date: Date): number {
  const start = dateRange.value.start;
  const diffTime = date.getTime() - start.getTime();
  const diffDays = diffTime / (1000 * 60 * 60 * 24);
  return diffDays * pixelsPerDay.value;
}

function getDaysBetween(date1: string, date2: string): number {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  const diffTime = Math.abs(d2.getTime() - d1.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

function getProjectSegments(row: MilestoneBoardItem) {
  const segments = [];
  for (let i = 0; i < milestoneConfigs.length - 1; i++) {
    const current = milestoneConfigs[i];
    const next = milestoneConfigs[i + 1];

    if (!current || !next) continue;

    const d1 = row[current.key];
    const d2 = row[next.key];

    if (d1 && d2) {
      const start = dateToPosition(new Date(d1));
      const end = dateToPosition(new Date(d2));
      const width = end - start;

      if (width > 0) {
        segments.push({
          start,
          width,
          color: current.color,
          label: `${current.label}-${next.label}`,
          startDate: d1,
          endDate: d2,
        });
      }
    }
  }
  return segments;
}

function getProjectMilestones(row: MilestoneBoardItem) {
  const milestones: Array<{
    color: string;
    date: string;
    hasRisk: boolean;
    key: string;
    label: string;
    position: number;
    riskInfo?: any;
  }> = [];
  milestoneConfigs.forEach((config) => {
    const d = row[config.key];
    if (d) {
      const riskInfo = getRiskInfo(row, config.key);
      milestones.push({
        key: config.key,
        position: dateToPosition(new Date(d)),
        color: config.color,
        label: config.label,
        date: d,
        hasRisk: !!riskInfo,
        riskInfo,
      });
    }
  });
  return milestones;
}

// Tooltip
function showBarTooltip(e: MouseEvent, segment: any, row: MilestoneBoardItem) {
  const duration = getDaysBetween(segment.startDate, segment.endDate);
  tooltip.value = {
    visible: true,
    x: e.clientX + 15,
    y: e.clientY + 15,
    title: row.project_name,
    type: 'segment',
    content: {
      label: segment.label,
      startDate: segment.startDate,
      endDate: segment.endDate,
      duration,
    },
  };
}

function showMilestoneTooltip(
  e: MouseEvent,
  milestone: any,
  row: MilestoneBoardItem,
) {
  tooltip.value = {
    visible: true,
    x: e.clientX + 15,
    y: e.clientY + 15,
    title: row.project_name,
    type: 'milestone',
    content: {
      label: milestone.label,
      date: milestone.date,
      hasRisk: milestone.hasRisk,
      riskLevel: milestone.riskInfo?.level,
    },
  };
}

function updateTooltipPosition(e: MouseEvent) {
  if (tooltip.value.visible) {
    tooltip.value.x = e.clientX + 15;
    tooltip.value.y = e.clientY + 15;
  }
}

function hideBarTooltip() {
  tooltip.value.visible = false;
}

// Zoom & Drag
function zoomIn() {
  if (zoomLevel.value < 3) {
    const oldZoom = zoomLevel.value;
    zoomLevel.value = Math.min(3, zoomLevel.value + 0.2);
    adjustOffsetAfterZoom(oldZoom, zoomLevel.value);
  }
}

function zoomOut() {
  if (zoomLevel.value > 0.5) {
    const oldZoom = zoomLevel.value;
    zoomLevel.value = Math.max(0.5, zoomLevel.value - 0.2);
    adjustOffsetAfterZoom(oldZoom, zoomLevel.value);
  }
}

function adjustOffsetAfterZoom(oldZoom: number, newZoom: number) {
  if (!timelineContainerRef.value) return;
  const containerWidth = timelineContainerRef.value.clientWidth;
  const centerX = containerWidth / 2;
  const timePointFactor = (centerX - offsetX.value) / oldZoom;

  offsetX.value = centerX - timePointFactor * newZoom;
  applyBoundary();
}

function resetView() {
  zoomLevel.value = 1;
  if (timelineContainerRef.value) {
    const containerWidth = timelineContainerRef.value.clientWidth;
    offsetX.value = containerWidth / 2 - todayPosition.value;
    applyBoundary();
  }
}

function applyBoundary() {
  const boundary = dragBoundary.value;
  // Always clamp, even if content is smaller than container (pins it to 0)
  offsetX.value = Math.max(boundary.min, Math.min(boundary.max, offsetX.value));
}

function handleMouseDown(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (
    target.closest('.gantt-bar') ||
    target.closest('.milestone-node') ||
    target.closest('.control-group') ||
    target.closest('.column-resizer')
  )
    return;
  isDragging.value = true;
  dragStartX.value = e.clientX;
  dragStartOffsetX.value = offsetX.value;
  document.body.style.cursor = 'grabbing';
  e.preventDefault();
}

function handleResizeStart(e: MouseEvent) {
  isResizing.value = true;
  resizeStartX.value = e.clientX;
  resizeStartWidth.value = projectColumnWidth.value;
  document.body.style.cursor = 'col-resize';
  e.preventDefault();
}

function handleMouseMove(e: MouseEvent) {
  if (isResizing.value) {
    const deltaX = e.clientX - resizeStartX.value;
    const newWidth = Math.max(100, resizeStartWidth.value + deltaX);
    projectColumnWidth.value = newWidth;
    return;
  }
  if (!isDragging.value) return;
  const deltaX = e.clientX - dragStartX.value;
  offsetX.value = dragStartOffsetX.value + deltaX;
  applyBoundary();
}

function handleMouseUp() {
  isDragging.value = false;
  isResizing.value = false;
  document.body.style.cursor = 'default';
}

function handleWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault();
    const oldZoom = zoomLevel.value;
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    zoomLevel.value = Math.max(0.5, Math.min(3, zoomLevel.value + delta));
    adjustOffsetAfterZoom(oldZoom, zoomLevel.value);
  }
}

onMounted(() => {
  resetView();
  const container = timelineContainerRef.value;
  const body = ganttBodyRef.value;
  if (container)
    container.addEventListener('wheel', handleWheel, { passive: false });
  if (body) body.addEventListener('wheel', handleWheel, { passive: false });
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
});

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
});
</script>

<template>
  <div class="milestone-gantt-container" ref="ganttContainerRef">
    <!-- 头部区域 -->
    <div class="gantt-header">
      <!-- 左侧：项目名称列 -->
      <div class="table-header" :style="{ width: `${projectColumnWidth}px` }">
        <div class="header-cell">项目名称</div>
        <div class="column-resizer" @mousedown.stop="handleResizeStart"></div>
      </div>

      <!-- 右侧：时间轴头部 -->
      <div
        class="timeline-header-container"
        ref="timelineContainerRef"
        @mousedown="handleMouseDown"
      >
        <div
          class="timeline-content"
          :style="{
            width: `${timelineTotalWidth}px`,
            transform: `translateX(${offsetX}px)`,
          }"
        >
          <div class="timeline-scale">
            <div
              v-for="date in timelineScale"
              :key="date.timestamp"
              class="scale-item"
              :class="{ 'is-today': date.isToday }"
              :style="{ left: `${date.position}px` }"
            >
              <div class="scale-line"></div>
              <div class="scale-label">{{ date.label }}</div>
            </div>
          </div>
          <div class="today-line" :style="{ left: `${todayPosition}px` }"></div>
        </div>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="gantt-body" ref="ganttBodyRef" @mousedown="handleMouseDown">
      <div v-for="row in data" :key="row.project_id" class="gantt-row">
        <!-- 左侧：项目名称 -->
        <div class="table-row" :style="{ width: `${projectColumnWidth}px` }">
          <div class="row-cell" :title="row.project_name">
            {{ row.project_name }}
          </div>
        </div>

        <!-- 右侧：时间轴行 -->
        <div class="timeline-row-container">
          <div
            class="timeline-content"
            :style="{
              width: `${timelineTotalWidth}px`,
              transform: `translateX(${offsetX}px)`,
            }"
          >
            <!-- 甘特条（阶段） -->
            <div
              v-for="(segment, index) in getProjectSegments(row)"
              :key="`seg-${index}`"
              class="gantt-bar"
              :style="{
                left: `${segment.start}px`,
                width: `${segment.width}px`,
                backgroundColor: segment.color,
              }"
              @mouseenter="(e) => showBarTooltip(e, segment, row)"
              @mousemove="(e) => updateTooltipPosition(e)"
              @mouseleave="hideBarTooltip"
            >
              <span class="bar-label">{{ segment.label }}</span>
            </div>

            <!-- 里程碑节点 -->
            <div
              v-for="milestone in getProjectMilestones(row)"
              :key="`ms-${milestone.key}`"
              class="milestone-node"
              :class="{
                'has-risk': milestone.hasRisk,
                'risk-confirmed': milestone.riskInfo?.level === 'medium',
              }"
              :style="{
                left: `${milestone.position}px`,
                backgroundColor: milestone.hasRisk
                  ? milestone.riskInfo?.level === 'medium'
                    ? 'var(--milestone-risk-medium)'
                    : 'var(--milestone-risk-high)'
                  : milestone.color,
                borderColor: milestone.hasRisk
                  ? milestone.riskInfo?.level === 'medium'
                    ? 'var(--milestone-risk-medium)'
                    : 'var(--milestone-risk-high)'
                  : 'var(--milestone-node-border)',
              }"
              @click.stop="() => handleRiskClick(milestone)"
              @mouseenter="(e) => showMilestoneTooltip(e, milestone, row)"
              @mousemove="(e) => updateTooltipPosition(e)"
              @mouseleave="hideBarTooltip"
            >
              <div v-if="milestone.hasRisk" class="risk-indicator">!</div>
            </div>

            <div
              class="today-line"
              :style="{ left: `${todayPosition}px` }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 控制栏 -->
    <div class="gantt-controls">
      <div class="control-group">
        <ElButtonGroup size="small">
          <ElButton @click="zoomOut" :disabled="zoomLevel <= 0.5">-</ElButton>
          <ElButton disabled class="scale-text">
            {{ Math.round(zoomLevel * 100) }}%
          </ElButton>
          <ElButton @click="zoomIn" :disabled="zoomLevel >= 3">+</ElButton>
        </ElButtonGroup>
        <ElButton size="small" @click="resetView">重置视图</ElButton>
        <ElButton size="small" @click="toggleFullscreen">
          <ElIcon class="mr-1"><FullScreen /></ElIcon>
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </ElButton>
      </div>
      <div class="legend">
        <div
          v-for="config in milestoneConfigs"
          :key="config.key"
          class="legend-item"
        >
          <span
            class="legend-color"
            :style="{ backgroundColor: config.color }"
          ></span>
          <span>{{ config.label }}</span>
        </div>
      </div>
    </div>

    <!-- Risk Handle Dialog -->
    <RiskHandleDialog ref="riskHandleDialogRef" @success="handleRiskSuccess" />

    <!-- Tooltip -->
    <Teleport to="body">
      <div
        v-if="tooltip.visible"
        class="gantt-tooltip"
        :style="{
          left: `${tooltip.x}px`,
          top: `${tooltip.y}px`,
        }"
      >
        <div class="tooltip-header">{{ tooltip.title }}</div>
        <div class="tooltip-body">
          <div v-if="tooltip.type === 'segment'">
            <div class="tooltip-row">
              <span>阶段:</span>
              <span>{{ tooltip.content.label }}</span>
            </div>
            <div class="tooltip-row">
              <span>开始:</span>
              <span>{{ tooltip.content.startDate }}</span>
            </div>
            <div class="tooltip-row">
              <span>结束:</span>
              <span>{{ tooltip.content.endDate }}</span>
            </div>
            <div class="tooltip-row">
              <span>时长:</span>
              <span>{{ tooltip.content.duration }} 天</span>
            </div>
          </div>
          <div v-else-if="tooltip.type === 'milestone'">
            <div class="tooltip-row">
              <span>节点:</span>
              <span>{{ tooltip.content.label }}</span>
            </div>
            <div class="tooltip-row">
              <span>日期:</span>
              <span>{{ tooltip.content.date }}</span>
            </div>
            <div v-if="tooltip.content.hasRisk" class="tooltip-row risk-row">
              <span
                :class="
                  tooltip.content.riskLevel === 'medium'
                    ? 'text-yellow-500'
                    : 'text-red-500'
                "
              >
                风险:
              </span>
              <span
                :class="
                  tooltip.content.riskLevel === 'medium'
                    ? 'font-bold text-yellow-500'
                    : 'font-bold text-red-500'
                "
              >
                {{
                  tooltip.content.riskLevel === 'medium'
                    ? '已确认 (持续跟踪)'
                    : '存在高风险'
                }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
.milestone-gantt-container {
  --milestone-bg: var(--el-bg-color);
  --milestone-bg-soft: var(--el-fill-color-light);
  --milestone-bg-soft-strong: var(--el-fill-color);
  --milestone-border: var(--el-border-color);
  --milestone-border-soft: var(--el-border-color-lighter);
  --milestone-text: var(--el-text-color-primary);
  --milestone-text-muted: var(--el-text-color-secondary);
  --milestone-text-regular: var(--el-text-color-regular);
  --milestone-primary: var(--el-color-primary);
  --milestone-header-bg: var(--milestone-board-header-bg, #f7faff);
  --milestone-header-bg-strong: var(
    --milestone-board-header-bg-strong,
    #f2f7ff
  );
  --milestone-header-border: var(--milestone-board-header-border, #dbe7fa);
  --milestone-header-text: var(--milestone-board-header-text, #6a7b95);
  --milestone-header-shadow: var(
    --milestone-board-header-shadow,
    inset 0 -1px 0 #e7effc
  );
  --milestone-header-track: var(
    --milestone-board-header-track,
    linear-gradient(
      90deg,
      rgb(63 140 255 / 14%) 0%,
      rgb(34 160 107 / 13%) 20%,
      rgb(229 162 53 / 13%) 40%,
      rgb(225 106 106 / 13%) 58%,
      rgb(139 124 247 / 13%) 76%,
      rgb(38 181 165 / 13%) 100%
    )
  );
  --milestone-controls-bg: var(--milestone-board-controls-bg, #f7faff);
  --milestone-controls-border: var(--milestone-board-controls-border, #dbe7fa);
  --milestone-controls-shadow: var(
    --milestone-board-controls-shadow,
    inset 0 1px 0 rgb(255 255 255 / 70%)
  );
  --milestone-controls-text: var(--milestone-board-controls-text, #6a7b95);
  --milestone-node-border: var(--el-bg-color);
  --milestone-bar-shadow: 0 1px 2px rgb(15 23 42 / 18%);
  --milestone-bar-shadow-hover: 0 4px 10px rgb(15 23 42 / 24%);
  --milestone-node-shadow: 0 2px 5px rgb(15 23 42 / 22%);
  --milestone-tooltip-bg: var(--el-bg-color-overlay);
  --milestone-tooltip-shadow: var(--el-box-shadow-dark);

  --milestone-qg1: var(--milestone-board-qg1, #3f8cff);
  --milestone-qg2: var(--milestone-board-qg2, #22a06b);
  --milestone-qg3: var(--milestone-board-qg3, #e5a235);
  --milestone-qg4: var(--milestone-board-qg4, #e16a6a);
  --milestone-qg5: var(--milestone-board-qg5, #8b7cf7);
  --milestone-qg6: var(--milestone-board-qg6, #e272b1);
  --milestone-qg7: var(--milestone-board-qg7, #6a79ff);
  --milestone-qg8: var(--milestone-board-qg8, #26b5a5);

  --milestone-risk-high: var(--milestone-board-risk-high, #ef4444);
  --milestone-risk-medium: var(--milestone-board-risk-medium, #f59e0b);
  --milestone-risk-high-rgb: var(--milestone-board-risk-high-rgb, 239, 68, 68);
  --milestone-risk-medium-rgb: var(
    --milestone-board-risk-medium-rgb,
    245,
    158,
    11
  );

  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--milestone-bg);
  border: 1px solid var(--milestone-border);
  border-radius: 10px;
  overflow: hidden;
  font-size: 14px;
  color: var(--milestone-text);
}

.gantt-header {
  display: flex;
  height: 48px;
  background: var(--milestone-header-bg);
  border-bottom: 1px solid var(--milestone-header-border);
  box-shadow: var(--milestone-header-shadow);
  flex-shrink: 0;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 2px;
    background: var(--milestone-header-track);
    opacity: 0.95;
    pointer-events: none;
  }

  .table-header {
    position: relative;
    border-right: 1px solid var(--milestone-header-border);
    background: var(--milestone-header-bg-strong);
    display: flex;
    align-items: center;
    padding-left: 12px;
    font-weight: 600;
    color: var(--milestone-header-text);

    .column-resizer {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      width: 6px;
      cursor: col-resize;
      z-index: 10;
      opacity: 0;
      transition:
        opacity 0.2s,
        background-color 0.2s;

      &:hover {
        opacity: 1;
        background-color: var(--milestone-primary);
      }
    }
  }

  .timeline-header-container {
    flex: 1;
    overflow: hidden;
    position: relative;
    background: var(--milestone-header-bg);
    cursor: grab;

    &:active {
      cursor: grabbing;
    }
  }
}

.gantt-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  background: var(--milestone-bg);
}

.gantt-row {
  display: flex;
  height: 48px;
  border-bottom: 1px solid var(--milestone-border-soft);
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--milestone-bg-soft);
  }

  .table-row {
    border-right: 1px solid var(--milestone-border);
    background: var(--milestone-bg);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding-left: 12px;

    .row-cell {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--milestone-text);
    }
  }

  .timeline-row-container {
    flex: 1;
    position: relative;
    overflow: hidden;
    cursor: grab;

    &:active {
      cursor: grabbing;
    }
  }
}

.timeline-content {
  height: 100%;
  position: relative;
}

.timeline-scale {
  position: relative;
  height: 100%;

  .scale-item {
    position: absolute;
    top: 0;
    height: 100%;
    display: flex;
    align-items: center;

    .scale-line {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 1px;
      background: var(--milestone-header-border);
    }

    .scale-label {
      margin-left: 6px;
      font-size: 12px;
      color: var(--milestone-header-text);
      font-weight: 500;
    }

    &.is-today .scale-label {
      color: var(--milestone-primary);
      font-weight: 700;
    }
  }
}

.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--milestone-primary);
  z-index: 10;
  pointer-events: none;
  opacity: 0.55;
}

.gantt-bar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: 24px;
  border-radius: 6px;
  opacity: 0.86;
  display: flex;
  align-items: center;
  padding: 0 8px;
  cursor: pointer;
  transition:
    opacity 0.2s,
    box-shadow 0.2s,
    height 0.2s;
  box-shadow: var(--milestone-bar-shadow);

  &:hover {
    opacity: 1;
    height: 28px;
    z-index: 20;
    box-shadow: var(--milestone-bar-shadow-hover);
  }

  .bar-label {
    font-size: 11px;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 1px 2px rgb(15 23 42 / 32%);
  }
}

.milestone-node {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--milestone-node-border);
  box-shadow: var(--milestone-node-shadow);
  z-index: 15;
  cursor: pointer;
  transition: transform 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    transform: translate(-50%, -50%) scale(1.35);
    z-index: 25;
  }

  &.has-risk {
    animation: pulse-red 2s infinite;
  }

  &.risk-confirmed {
    animation: pulse-yellow 2s infinite;
  }

  .risk-indicator {
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
  }
}

@keyframes pulse-red {
  0% {
    box-shadow: 0 0 0 0 rgba(var(--milestone-risk-high-rgb), 0.72);
  }

  70% {
    box-shadow: 0 0 0 6px rgba(var(--milestone-risk-high-rgb), 0);
  }

  100% {
    box-shadow: 0 0 0 0 rgba(var(--milestone-risk-high-rgb), 0);
  }
}

@keyframes pulse-yellow {
  0% {
    box-shadow: 0 0 0 0 rgba(var(--milestone-risk-medium-rgb), 0.72);
  }

  70% {
    box-shadow: 0 0 0 6px rgba(var(--milestone-risk-medium-rgb), 0);
  }

  100% {
    box-shadow: 0 0 0 0 rgba(var(--milestone-risk-medium-rgb), 0);
  }
}

.gantt-controls {
  padding: 8px 16px;
  border-top: 1px solid var(--milestone-controls-border);
  background: var(--milestone-controls-bg);
  box-shadow: var(--milestone-controls-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;

  .control-group {
    display: flex;
    align-items: center;
    gap: 12px;

    .scale-text {
      width: 60px;
    }
  }

  .legend {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--milestone-controls-text);

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;

      .legend-color {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }
    }
  }
}

.gantt-tooltip {
  position: fixed;
  background: var(--milestone-tooltip-bg);
  color: var(--milestone-text);
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  z-index: 9999;
  pointer-events: none;
  box-shadow: var(--milestone-tooltip-shadow);
  backdrop-filter: blur(4px);
  min-width: 200px;
  border: 1px solid var(--milestone-border-soft);

  .tooltip-header {
    font-weight: 600;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--milestone-border-soft);
  }

  .tooltip-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .tooltip-row {
    display: flex;
    justify-content: space-between;
    gap: 16px;

    span:first-child {
      color: var(--milestone-text-muted);
    }

    span:last-child {
      font-weight: 500;
    }
  }
}
</style>
