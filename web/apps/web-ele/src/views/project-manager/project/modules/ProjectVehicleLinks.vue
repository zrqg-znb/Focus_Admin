<script lang="ts" setup>
import type { ProjectVehicleLinkItem } from '#/api/project-manager/project';

import { computed } from 'vue';

import { ElButton, ElInput } from 'element-plus';

const props = defineProps<{
  modelValue?: ProjectVehicleLinkItem[];
  title: string;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: ProjectVehicleLinkItem[]): void;
}>();

const rows = computed(() => props.modelValue || []);

function updateRows(nextRows: ProjectVehicleLinkItem[]) {
  emit('update:modelValue', nextRows);
}

function addRow() {
  updateRows([...rows.value, { chip_name: '', url: '' }]);
}

function removeRow(index: number) {
  updateRows(rows.value.filter((_, currentIndex) => currentIndex !== index));
}

function updateField(
  index: number,
  field: keyof ProjectVehicleLinkItem,
  value: string,
) {
  updateRows(
    rows.value.map((row, currentIndex) =>
      currentIndex === index ? { ...row, [field]: value } : row,
    ),
  );
}
</script>

<template>
  <div class="rounded-md border border-dashed p-4">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div class="text-sm font-medium">{{ title }}</div>
      <ElButton size="small" type="primary" plain @click="addRow">
        添加一条
      </ElButton>
    </div>

    <div v-if="rows.length === 0" class="text-muted-foreground text-sm">
      暂未配置
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="(row, index) in rows"
        :key="index"
        class="grid grid-cols-[160px_1fr_auto] items-center gap-2"
      >
        <ElInput
          :model-value="row.chip_name"
          clearable
          placeholder="芯片名称"
          @update:model-value="
            (value) => updateField(index, 'chip_name', String(value || ''))
          "
        />
        <ElInput
          :model-value="row.url"
          clearable
          placeholder="请输入链接"
          @update:model-value="
            (value) => updateField(index, 'url', String(value || ''))
          "
        />
        <ElButton type="danger" link @click="removeRow(index)">删除</ElButton>
      </div>
    </div>
  </div>
</template>
