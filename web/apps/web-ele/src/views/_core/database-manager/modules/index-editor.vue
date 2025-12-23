<script setup lang="ts">
import { computed } from 'vue';
import {
  ElTable,
  ElTableColumn,
  ElInput,
  ElSelect,
  ElOption,
  ElCheckbox,
  ElButton,
  ElMessage,
} from 'element-plus';
import { Plus, Trash } from '@vben/icons';

interface IndexDefinition {
  name: string;
  type: string;
  columns: string[];
  unique: boolean;
}

interface FieldDefinition {
  name: string;
}

interface Props {
  indexes: IndexDefinition[];
  fields: FieldDefinition[];
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});
const emit = defineEmits<{
  'update:indexes': [indexes: IndexDefinition[]];
}>();

// 索引类型选项
const indexTypes = [
  { label: 'BTREE', value: 'btree' },
  { label: 'HASH', value: 'hash' },
  { label: 'GIN', value: 'gin' },
  { label: 'GIST', value: 'gist' },
  { label: 'BRIN', value: 'brin' },
];

const localIndexes = computed({
  get: () => props.indexes,
  set: (value) => emit('update:indexes', value),
});

// 添加索引
function addIndex() {
  const newIndex: IndexDefinition = {
    name: '',
    type: 'btree',
    columns: [],
    unique: false,
  };
  localIndexes.value = [...localIndexes.value, newIndex];
}

// 删除索引
function deleteIndex(index: number) {
  localIndexes.value = localIndexes.value.filter((_, i) => i !== index);
  ElMessage.success('索引已删除');
}
</script>

<template>
  <div class="index-editor">
    <div class="mb-3 flex justify-between items-center">
      <div class="text-sm font-semibold">索引列表</div>
      <ElButton type="primary" size="small" @click="addIndex" :disabled="disabled">
        <Plus :size="14" />
        <span class="ml-1">添加索引</span>
      </ElButton>
    </div>

    <ElTable :data="localIndexes" border stripe max-height="400">
      <ElTableColumn label="序号" width="60" align="center">
        <template #default="{ $index }">
          {{ $index + 1 }}
        </template>
      </ElTableColumn>

      <ElTableColumn label="索引名" width="200">
        <template #default="{ row }">
          <ElInput v-model="row.name" placeholder="索引名" size="small" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="索引类型" width="130">
        <template #default="{ row }">
          <ElSelect v-model="row.type" placeholder="类型" size="small">
            <ElOption
              v-for="type in indexTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </ElSelect>
        </template>
      </ElTableColumn>

      <ElTableColumn label="字段" min-width="200">
        <template #default="{ row }">
          <ElSelect
            v-model="row.columns"
            multiple
            placeholder="选择字段"
            size="small"
            style="width: 100%"
          >
            <ElOption
              v-for="field in fields"
              :key="field.name"
              :label="field.name"
              :value="field.name"
            />
          </ElSelect>
        </template>
      </ElTableColumn>

      <ElTableColumn label="唯一" width="80" align="center">
        <template #default="{ row }">
          <ElCheckbox v-model="row.unique" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="操作" width="80" fixed="right" align="center">
        <template #default="{ $index }">
          <ElButton
            size="small"
            type="danger"
            @click="deleteIndex($index)"
          >
            <Trash :size="14" />
          </ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div v-if="localIndexes.length === 0" class="text-center text-gray-400 py-8">
      暂无索引，点击"添加索引"开始创建
    </div>
  </div>
</template>
