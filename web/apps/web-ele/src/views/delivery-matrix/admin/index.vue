<script lang="ts" setup>
import type { OrgNode } from '#/api/delivery-matrix';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import DeliveryForm from './modules/DeliveryForm.vue';
import DeliveryTree from './modules/DeliveryTree.vue';

const treeRef = ref();
const selectedNode = ref<OrgNode>();
const isEdit = ref(false);
const createParent = ref<OrgNode>();
const showForm = ref(false);

function onSelect(node: OrgNode | undefined) {
  if (!node) {
      showForm.value = false;
      return;
  }
  selectedNode.value = node;
  isEdit.value = true;
  createParent.value = undefined;
  showForm.value = true;
}

function onAdd(parentNode?: OrgNode) {
  selectedNode.value = undefined;
  isEdit.value = false;
  createParent.value = parentNode;
  showForm.value = true;
}

function onSuccess() {
  treeRef.value?.refresh();
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full gap-2 p-2">
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
          :node="selectedNode"
          :is-edit="isEdit"
          :parent-node="createParent"
          @success="onSuccess"
        />
      </div>
    </div>
  </Page>
</template>
