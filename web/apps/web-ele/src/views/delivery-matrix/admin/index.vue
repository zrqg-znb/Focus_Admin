<script lang="ts" setup>
import type { DeliveryTreeNode } from '#/api/delivery-matrix';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import DeliveryForm from './modules/DeliveryForm.vue';
import DeliveryTree from './modules/DeliveryTree.vue';

const treeRef = ref();
const selectedNode = ref<DeliveryTreeNode>();
const isEdit = ref(false);
const createType = ref<'component' | 'domain' | 'group'>();
const createParent = ref<DeliveryTreeNode>();

function onSelect(node: DeliveryTreeNode | undefined) {
  selectedNode.value = node;
  isEdit.value = true;
  createType.value = undefined;
  createParent.value = undefined;
}

function onAdd(
  type: 'component' | 'domain' | 'group',
  parentNode?: DeliveryTreeNode,
) {
  selectedNode.value = undefined; // Clear selection to show create form
  isEdit.value = false;
  createType.value = type;
  createParent.value = parentNode;
}

function onSuccess() {
  treeRef.value?.refresh();
  // If created, maybe select it? For now just refresh
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
          v-if="!selectedNode && !createType"
          class="flex h-full items-center justify-center text-gray-400"
        >
          请选择左侧节点进行操作
        </div>
        <DeliveryForm
          v-else
          :node="selectedNode"
          :is-edit="isEdit"
          :type="createType || selectedNode?.type"
          :parent-node="createParent"
          @success="onSuccess"
        />
      </div>
    </div>
  </Page>
</template>
