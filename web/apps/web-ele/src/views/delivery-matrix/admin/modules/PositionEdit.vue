<script setup lang="ts">
import { ref, watch } from 'vue';

import { Plus, Trash2 } from 'lucide-vue-next';

import { ElButton, ElInput, ElInputNumber } from 'element-plus';

import { UserSelector } from '#/components/zq-form/user-selector';

interface PositionItem {
  name: string;
  sort?: number;
  user_ids: string[];
}

const props = defineProps<{
  modelValue: PositionItem[];
}>();

const emit = defineEmits(['update:modelValue']);

const list = ref<PositionItem[]>([]);

watch(
  () => props.modelValue,
  (val) => {
    list.value = val ? [...val] : [];
  },
  { deep: true, immediate: true },
);

function update() {
  emit('update:modelValue', list.value);
}

function add() {
  list.value.push({ name: '', sort: 0, user_ids: [] });
  update();
}

function remove(index: number) {
  list.value.splice(index, 1);
  update();
}

function onUserChange(val: string | string[] | undefined, index: number) {
  const ids = Array.isArray(val) ? val : (val ? [val] : []);
  list.value[index].user_ids = ids;
  update();
}
</script>

<template>
  <div class="w-full">
    <div class="mb-2 flex items-center justify-between">
      <span class="text-sm font-medium">岗位配置</span>
      <ElButton link size="small" type="primary" @click="add">
        <Plus class="mr-1 size-4" /> 添加岗位
      </ElButton>
    </div>

    <div
      v-if="list.length === 0"
      class="rounded border border-dashed py-4 text-center text-gray-400"
    >
      暂无岗位配置
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="(item, index) in list"
        :key="index"
        class="flex items-start gap-2 rounded border bg-gray-50 p-2"
      >
        <div class="w-1/4">
          <div class="mb-1 text-xs text-gray-500">岗位名称</div>
          <ElInput
            v-model="item.name"
            placeholder="如：项目经理"
            @input="update"
          />
        </div>
        <div class="w-24">
          <div class="mb-1 text-xs text-gray-500">排序</div>
          <ElInputNumber
            v-model="item.sort"
            :min="0"
            :precision="0"
            controls-position="right"
            style="width: 100%"
            @change="update"
          />
        </div>
        <div class="flex-1">
          <div class="mb-1 text-xs text-gray-500">关联人员</div>
          <UserSelector
            v-model="item.user_ids"
            multiple
            placeholder="选择人员"
            @change="(val) => onUserChange(val, index)"
          />
        </div>
        <div class="pt-6">
          <ElButton link type="danger" @click="remove(index)">
            <Trash2 class="size-4" />
          </ElButton>
        </div>
      </div>
    </div>
  </div>
</template>
