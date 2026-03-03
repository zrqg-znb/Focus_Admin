<script lang="ts" setup>
import type {
  HardwareConfigSummary,
  HardwarePhaseConfig,
} from '#/api/project-manager/report';

import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { ElEmpty, ElTable, ElTableColumn, ElTag } from 'element-plus';

const props = defineProps<{
  data?: HardwareConfigSummary | null;
}>();

const hardwareData = computed<HardwareConfigSummary | null>(
  () => props.data || null,
);
const isEnabled = computed(() => !!hardwareData.value?.enabled);
const scenario = computed(() => hardwareData.value?.scenario || 'vehicle');
const phases = computed(() => hardwareData.value?.phases || []);
const isVehicleScenario = computed(() => scenario.value === 'vehicle');

function formatPhaseRange(phase: HardwarePhaseConfig) {
  if (!phase.stage_start && !phase.stage_end) return '-';
  return `${phase.stage_start || '-'} ~ ${phase.stage_end || '-'}`;
}

function getPointText(phase: HardwarePhaseConfig, point: string) {
  const item = (phase.vehicle_hardware || []).find(
    (hardware) => hardware.point.toLowerCase() === point.toLowerCase(),
  );
  if (!item) return '-';
  const board = item.board || '-';
  const configType = item.config_type || '-';
  if (!item.bomid) return `${board} / ${configType}`;
  return `${board} / ${configType} / BOMID: ${item.bomid}`;
}

const vehicleRows = computed(() => {
  return phases.value.map((phase) => ({
    stage_name: phase.stage_name || '-',
    stage_range: formatPhaseRange(phase),
    idvp_platform_name: hardwareData.value?.idvp_platform_name || '-',
    viu0: getPointText(phase, 'viu0'),
    viu1: getPointText(phase, 'viu1'),
    viu2: getPointText(phase, 'viu2'),
    viu3: getPointText(phase, 'viu3'),
  }));
});

const cockpitPhase = computed(() => phases.value[0] || null);
</script>

<template>
  <section
    class="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-[#151515]"
  >
    <header
      class="flex items-center justify-between border-b border-gray-100 px-6 py-4 dark:border-gray-800"
    >
      <div class="flex items-center gap-2">
        <span class="h-4 w-1 rounded-full bg-blue-500"></span>
        <h3 class="text-base font-bold">典配信息</h3>
      </div>
      <div class="flex items-center gap-2">
        <ElTag v-if="isEnabled" type="success">已开启</ElTag>
        <ElTag v-else type="info">未开启</ElTag>
        <ElTag type="warning">
          {{ isVehicleScenario ? '车控领域' : '座舱领域' }}
        </ElTag>
      </div>
    </header>

    <div class="p-6">
      <ElEmpty
        v-if="!isEnabled"
        description="该项目未开启典配配置"
        :image-size="70"
      />

      <ElEmpty
        v-else-if="phases.length === 0"
        description="暂无典配数据"
        :image-size="70"
      />

      <template v-else-if="isVehicleScenario">
        <div class="mb-3 flex items-center gap-2 text-sm text-gray-500">
          <IconifyIcon icon="lucide:car-front" />
          <span>
            车控项目按阶段展示 IDVP 平台与各点位单板 / 典配类型 / BOMID
          </span>
        </div>
        <ElTable
          :data="vehicleRows"
          border
          stripe
          size="small"
          style="width: 100%"
        >
          <ElTableColumn prop="stage_name" label="阶段" min-width="140" />
          <ElTableColumn prop="stage_range" label="阶段起止" min-width="220" />
          <ElTableColumn
            prop="idvp_platform_name"
            label="IDVP 平台"
            min-width="180"
          />
          <ElTableColumn prop="viu0" label="viu0" min-width="220" />
          <ElTableColumn prop="viu1" label="viu1" min-width="220" />
          <ElTableColumn prop="viu2" label="viu2" min-width="220" />
          <ElTableColumn prop="viu3" label="viu3" min-width="220" />
        </ElTable>
      </template>

      <template v-else>
        <div class="mb-3 flex items-center gap-2 text-sm text-gray-500">
          <IconifyIcon icon="lucide:monitor" />
          <span>座舱项目展示 CDC 平台版本与智慧屏版本</span>
        </div>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div
            class="rounded-lg border border-gray-100 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/20"
          >
            <p class="text-xs text-gray-500">CDC 平台版本</p>
            <p class="mt-2 text-base font-semibold">
              {{ cockpitPhase?.cdc_platform_name || '-' }}
            </p>
          </div>
          <div
            class="rounded-lg border border-gray-100 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/20"
          >
            <p class="text-xs text-gray-500">智慧屏版本</p>
            <p class="mt-2 text-base font-semibold">
              {{ cockpitPhase?.smart_screen_version_name || '-' }}
            </p>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
