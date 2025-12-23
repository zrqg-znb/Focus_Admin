<script lang="ts" setup>
import type { OperationLog } from '#/api/core/operation-log';

import { computed } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElDescriptions, ElDescriptionsItem, ElTag } from 'element-plus';

import { getMethodOptions, getStatusOptions } from '../data';

interface Props { log?: OperationLog }
const props = defineProps<Props>();

const [Drawer, drawerApi] = useVbenDrawer({ title: $t('operationLog.detailTitle'), footer: false, loading: false });

const statusDisplay = computed(() => {
  if (!props.log) return '';
  const option = getStatusOptions().find((opt) => opt.value === props.log?.status);
  return option?.label || '';
});

const statusType = computed(() => {
  if (!props.log) return 'info';
  const option = getStatusOptions().find((opt) => opt.value === props.log?.status);
  return option?.type || 'info';
});

const methodDisplay = computed(() => {
  if (!props.log) return '';
  const option = getMethodOptions().find((opt) => opt.value === props.log?.request_method);
  return option?.label || props.log.request_method;
});

defineExpose({ open: drawerApi.open, close: drawerApi.close });
</script>

<template>
  <Drawer>
    <template v-if="log">
      <ElDescriptions :column="1" border>
        <ElDescriptionsItem :label="$t('operationLog.username')">{{ log.request_username }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.status')">
          <ElTag :type="statusType as any">{{ statusDisplay }}</ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.method')">
          <ElTag type="info">{{ methodDisplay }}</ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.path')">{{ log.request_path }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.modular')" v-if="log.request_modular">{{ log.request_modular }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.ip')">{{ log.request_ip }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.responseCode')" v-if="log.response_code !== undefined">{{ log.response_code }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.os')" v-if="log.request_os">{{ log.request_os }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.browser')" v-if="log.request_browser">{{ log.request_browser }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.time')">{{ log.sys_create_datetime }}</ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.requestBody')" v-if="log.request_body">
          <div class="max-w-full break-all text-sm">{{ JSON.stringify(log.request_body, null, 2) }}</div>
        </ElDescriptionsItem>
        <ElDescriptionsItem :label="$t('operationLog.jsonResult')" v-if="log.json_result">
          <div class="max-w-full break-all text-sm">{{ JSON.stringify(log.json_result, null, 2) }}</div>
        </ElDescriptionsItem>
      </ElDescriptions>
    </template>
    <template v-else>
      <div class="py-8 text-center text-gray-500">{{ $t('operationLog.noData') }}</div>
    </template>
  </Drawer>
</template>

