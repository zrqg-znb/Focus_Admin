<script lang="ts" setup>
import type { EnvironmentItem } from '#/api/environment-management';

import { computed } from 'vue';

import {
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { ZqDrawer } from '#/components/zq-drawer';

import { detailDeviceColumns } from '../data';

const props = withDefaults(
  defineProps<{
    environment?: EnvironmentItem | null;
    modelValue?: boolean;
  }>(),
  {
    environment: null,
    modelValue: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const title = computed(() =>
  props.environment ? `${props.environment.ip_address} 环境详情` : '环境详情',
);

const baseItems = computed(() => {
  const row = props.environment;
  if (!row) return [];
  return [
    { label: 'IP地址', value: row.ip_address || '-' },
    { label: '账号', value: row.account || '-' },
    { label: 'BOMID', value: row.bomid || '-' },
    { label: '环境资产编号', value: row.asset_number || '-' },
    { label: '领域', value: row.domain_label || '-' },
    { label: '分类', value: row.category_label || '-' },
    { label: '项目', value: row.project_name || '-' },
    { label: '车型', value: row.vehicle_model || '-' },
    { label: '货架位置', value: row.shelf_location || '-' },
    { label: '占用人', value: row.current_user_name || '无人占用' },
  ];
});
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :show-confirm-button="false"
    :show-footer="false"
    :title="title"
    size="720px"
  >
    <div v-if="environment" class="environment-detail-drawer">
      <section class="detail-section">
        <div class="section-title">基础信息</div>
        <ElDescriptions :column="2" border size="small">
          <ElDescriptionsItem
            v-for="item in baseItems"
            :key="item.label"
            :label="item.label"
          >
            {{ item.value }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="environment.status === 'idle' ? 'success' : 'danger'">
              {{ environment.status_label }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="队列人数">
            {{ environment.queue_count }} 人
          </ElDescriptionsItem>
        </ElDescriptions>
      </section>

      <section class="detail-section">
        <div class="section-title">配置情况</div>
        <div class="detail-text">{{ environment.config_description || '-' }}</div>
      </section>

      <section class="detail-section">
        <div class="section-title">备注</div>
        <div class="detail-text">{{ environment.remark || '-' }}</div>
      </section>

      <section class="detail-section">
        <div class="section-title">测试设备</div>
        <!-- 抽屉中的设备明细是当前环境 DTO 的静态详情矩阵，不做分页、筛选或 CRUD，因此不使用 zq-table。 -->
        <ElTable v-if="environment.devices.length" :data="environment.devices" border>
          <ElTableColumn
            v-for="column in detailDeviceColumns"
            :key="column.key"
            :label="column.label"
            :min-width="column.minWidth"
            :prop="column.prop"
            :width="column.width"
          >
            <template #default="{ row }">
              {{ row[column.prop || column.key] || '-' }}
            </template>
          </ElTableColumn>
        </ElTable>
        <ElEmpty v-else description="暂无测试设备" />
      </section>
    </div>
  </ZqDrawer>
</template>

<style scoped>
.environment-detail-drawer {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 8px 12px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.detail-text {
  min-height: 40px;
  padding: 10px 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 6px;
  color: var(--el-text-color-regular);
}
</style>
