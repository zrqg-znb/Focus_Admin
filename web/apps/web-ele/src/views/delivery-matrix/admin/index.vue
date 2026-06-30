<script lang="ts" setup>
import type { OrgNode } from '#/api/delivery-matrix';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElButton, ElMessage } from 'element-plus';

import { exportDeliveryMatrixMarkdown } from '#/api/delivery-matrix';

import DeliveryForm from './modules/DeliveryForm.vue';
import DeliveryTree from './modules/DeliveryTree.vue';

const treeRef = ref();
const selectedNode = ref<OrgNode>();
const isEdit = ref(false);
const createParent = ref<OrgNode>();
const showForm = ref(false);
const formRenderKey = ref(0);
const exportLoading = ref(false);

function formatExportTimestamp(date = new Date()) {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(
    date.getDate(),
  )}${pad(date.getHours())}${pad(date.getMinutes())}${pad(
    date.getSeconds(),
  )}`;
}

function downloadBlob(data: Blob, fileName: string) {
  const blob = data instanceof Blob ? data : new Blob([data]);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function onSelect(node: OrgNode | undefined) {
  if (!node) {
    showForm.value = false;
    return;
  }
  selectedNode.value = node;
  isEdit.value = true;
  createParent.value = undefined;
  formRenderKey.value += 1;
  showForm.value = true;
}

function onAdd(parentNode?: OrgNode) {
  selectedNode.value = undefined;
  isEdit.value = false;
  createParent.value = parentNode;
  formRenderKey.value += 1;
  showForm.value = true;
}

function onSuccess() {
  const currentId = isEdit.value ? selectedNode.value?.id : undefined;
  treeRef.value?.refresh(currentId);
}

async function onExportMarkdown() {
  if (exportLoading.value) return;
  exportLoading.value = true;
  try {
    const data = await exportDeliveryMatrixMarkdown();
    downloadBlob(data, `delivery-matrix-${formatExportTimestamp()}.md`);
    ElMessage.success('导出成功');
  } catch (error) {
    console.error('导出沟通矩阵失败:', error);
    ElMessage.error('导出失败，请稍后重试');
  } finally {
    exportLoading.value = false;
  }
}
</script>

<template>
  <Page auto-content-height content-class="flex h-full flex-col">
    <div class="flex items-center justify-between border-b bg-white px-3 py-2">
      <div class="text-base font-semibold text-gray-800">沟通矩阵数据配置</div>
      <ElButton
        type="primary"
        :loading="exportLoading"
        @click="onExportMarkdown"
      >
        <IconifyIcon icon="carbon:download" class="mr-1" />
        导出 Markdown
      </ElButton>
    </div>
    <div class="flex min-h-0 flex-1 gap-2 p-2">
      <!-- Left Tree -->
      <div
        class="w-1/4 min-w-[250px] rounded-lg border border-gray-100 bg-white shadow-sm"
      >
        <DeliveryTree ref="treeRef" @select="onSelect" @add="onAdd" />
      </div>

      <!-- Right Form -->
      <div class="flex-1 rounded-lg border border-gray-100 bg-white shadow-sm">
        <div
          v-if="!showForm"
          class="flex h-full items-center justify-center text-gray-400"
        >
          请选择左侧节点进行操作或点击添加
        </div>
        <DeliveryForm
          v-else
          :key="formRenderKey"
          :node="selectedNode"
          :is-edit="isEdit"
          :parent-node="createParent"
          @success="onSuccess"
        />
      </div>
    </div>
  </Page>
</template>
