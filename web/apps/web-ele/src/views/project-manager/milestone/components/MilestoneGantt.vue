<template>
  <div class="milestone-gantt-container">
    <!-- 头部区域 -->
    <div class="gantt-header">
      <!-- 左侧：项目名称列 -->
      <div class="table-header" :style="{ width: `${projectColumnWidth}px` }">
        <div class="header-cell">项目名称</div>
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
              :style="{
                left: `${milestone.position}px`,
                backgroundColor: milestone.color,
              }"
              @mouseenter="(e) => showMilestoneTooltip(e, milestone, row)"
              @mousemove="(e) => updateTooltipPosition(e)"
              @mouseleave="hideBarTooltip"
            ></div>

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
        <el-button-group size="small">
          <el-button @click="zoomOut" :disabled="zoomLevel <= 0.5">-</el-button>
          <el-button disabled class="scale-text"
            >{{ Math.round(zoomLevel * 100) }}%</el-button
          >
          <el-button @click="zoomIn" :disabled="zoomLevel >= 3">+</el-button>
        </el-button-group>
        <el-button size="small" @click="resetView">重置视图</el-button>
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
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import type { MilestoneBoardItem } from '#/api/project-manager/milestone';
import type { MilestoneConfig } from './types';

import { computed, onMounted, onUnmounted, ref } from 'vue';

import { ElButton, ElButtonGroup } from 'element-plus';

interface Props {
  data: MilestoneBoardItem[];
  basePixelsPerDay?: number;
}

const props = withDefaults(defineProps<Props>(), {
  basePixelsPerDay: 2,
});

// 配置信息
const milestoneConfigs: MilestoneConfig[] = [
  { key: 'qg1_date', label: 'QG1', color: '#3b82f6' },
  { key: 'qg2_date', label: 'QG2', color: '#10b981' },
  { key: 'qg3_date', label: 'QG3', color: '#f59e0b' },
  { key: 'qg4_date', label: 'QG4', color: '#ef4444' },
  { key: 'qg5_date', label: 'QG5', color: '#8b5cf6' },
  { key: 'qg6_date', label: 'QG6', color: '#ec4899' },
  { key: 'qg7_date', label: 'QG7', color: '#6366f1' },
  { key: 'qg8_date', label: 'QG8', color: '#14b8a6' },
];

// 状态
const zoomLevel = ref(1);
const offsetX = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartOffsetX = ref(0);
const projectColumnWidth = 200;

const timelineContainerRef = ref<HTMLElement>();
const ganttBodyRef = ref<HTMLElement>();

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  title: '',
  type: 'segment' as 'segment' | 'milestone',
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
    timestamp: number;
    position: number;
    label: string;
    isToday: boolean;
  }> = [];

  const start = new Date(dateRange.value.start);
  const end = new Date(dateRange.value.end);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const current = new Date(start);
  current.setDate(1);

  while (current <= end) {
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
    key: string;
    position: number;
    color: string;
    label: string;
    date: string;
  }> = [];
  milestoneConfigs.forEach((config) => {
    const d = row[config.key];
    if (d) {
      milestones.push({
        key: config.key,
        position: dateToPosition(new Date(d)),
        color: config.color,
        label: config.label,
        date: d,
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
    content: { label: milestone.label, date: milestone.date },
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
  // 当前中心点对应的时间偏移量（像素）
  const contentCenterX = (centerX - offsetX.value) / oldZoom;
  // 新的偏移量 = 中心点 - (时间偏移 * 新倍率)
  // 注意：这里 contentCenterX 是 "basePixels 坐标系下的位置"，所以要乘 newZoom
  // 等等，之前的逻辑是 (centerX - offset) / oldScale 得到的是 "缩放前的像素位置"?
  // 实际上 dateToPosition 返回的是 pixelsPerDay * zoom.
  // 所以 (centerX - offset) 是 "当前视图中心点相对于时间轴起点的像素距离"
  // 这个距离是 zoom 后的。
  // 我们需要保持这个"时间点"不变。
  // TimePoint = (centerX - offset) / pixelsPerDay_Current
  // NewOffset = centerX - (TimePoint * pixelsPerDay_New)

  const timePointFactor = (centerX - offsetX.value) / oldZoom;
  // 因为 pixelsPerDay = base * zoom, 所以除以 zoom 就得到 basePixels 下的位置

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
    target.closest('.control-group')
  )
    return;
  isDragging.value = true;
  dragStartX.value = e.clientX;
  dragStartOffsetX.value = offsetX.value;
  document.body.style.cursor = 'grabbing';
  e.preventDefault();
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return;
  const deltaX = e.clientX - dragStartX.value;
  offsetX.value = dragStartOffsetX.value + deltaX;
  applyBoundary();
}

function handleMouseUp() {
  isDragging.value = false;
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

<style scoped lang="scss">
.milestone-gantt-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.gantt-header {
  display: flex;
  height: 48px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
  flex-shrink: 0;

  .table-header {
    border-right: 1px solid var(--el-border-color);
    background: var(--el-fill-color);
    display: flex;
    align-items: center;
    padding-left: 12px;
    font-weight: 600;
    color: var(--el-text-color-regular);
  }

  .timeline-header-container {
    flex: 1;
    overflow: hidden;
    position: relative;
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
  background: var(--el-bg-color);
}

.gantt-row {
  display: flex;
  height: 48px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background-color 0.2s;
  &:hover {
    background-color: var(--el-fill-color-light);
  }

  .table-row {
    border-right: 1px solid var(--el-border-color);
    background: var(--el-bg-color);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding-left: 12px;

    .row-cell {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: var(--el-text-color-primary);
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

/* Timeline Elements */
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
      background: var(--el-border-color-lighter);
    }

    .scale-label {
      margin-left: 6px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      font-weight: 500;
    }

    &.is-today .scale-label {
      color: var(--el-color-primary);
      font-weight: 600;
    }
  }
}

.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--el-color-primary);
  z-index: 10;
  pointer-events: none;
  opacity: 0.5;
}

.gantt-bar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: 24px;
  border-radius: 4px;
  opacity: 0.8;
  display: flex;
  align-items: center;
  padding: 0 8px;
  cursor: pointer;
  transition: opacity 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);

  &:hover {
    opacity: 1;
    height: 28px;
    z-index: 20;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .bar-label {
    font-size: 11px;
    color: #fff; /* Always white for contrast on colored bars */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  }
}

.milestone-node {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--el-bg-color);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 15;
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: translate(-50%, -50%) scale(1.4);
    z-index: 25;
  }
}

/* Controls */
.gantt-controls {
  padding: 8px 16px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
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
    color: var(--el-text-color-regular);
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

/* Tooltip */
.gantt-tooltip {
  position: fixed;
  background: var(--el-bg-color-overlay);
  color: var(--el-text-color-primary);
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  pointer-events: none;
  box-shadow: var(--el-box-shadow-dark);
  backdrop-filter: blur(4px);
  min-width: 200px;
  border: 1px solid var(--el-border-color-lighter);

  .tooltip-header {
    font-weight: 600;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--el-border-color-lighter);
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
      color: var(--el-text-color-secondary);
    }
    span:last-child {
      font-weight: 500;
    }
  }
}
</style>
