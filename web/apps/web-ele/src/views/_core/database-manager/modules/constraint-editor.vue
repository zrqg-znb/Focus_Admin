<script setup lang="ts">
import { computed } from 'vue';
import {
  ElTable,
  ElTableColumn,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElMessage,
} from 'element-plus';
import { Plus, Trash } from '@vben/icons';

interface ConstraintDefinition {
  name: string;
  type: string;
  definition: string;
  columns?: string[];
  referencedTable?: string;
  referencedColumns?: string[];
}

interface FieldDefinition {
  name: string;
}

interface Props {
  constraints: ConstraintDefinition[];
  fields: FieldDefinition[];
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});
const emit = defineEmits<{
  'update:constraints': [constraints: ConstraintDefinition[]];
}>();

// 约束类型选项
const constraintTypes = [
  { label: 'PRIMARY KEY', value: 'primary' },
  { label: 'FOREIGN KEY', value: 'foreign' },
  { label: 'UNIQUE', value: 'unique' },
  { label: 'CHECK', value: 'check' },
];

const localConstraints = computed({
  get: () => props.constraints,
  set: (value) => emit('update:constraints', value),
});

// 添加约束
function addConstraint() {
  const newConstraint: ConstraintDefinition = {
    name: '',
    type: 'check',
    definition: '',
    columns: [],
  };
  localConstraints.value = [...localConstraints.value, newConstraint];
}

// 删除约束
function deleteConstraint(index: number) {
  localConstraints.value = localConstraints.value.filter((_, i) => i !== index);
  ElMessage.success('约束已删除');
}
</script>

<template>
  <div class="constraint-editor">
    <div class="mb-3 flex justify-between items-center">
      <div class="text-sm font-semibold">约束列表</div>
      <ElButton type="primary" size="small" @click="addConstraint" :disabled="disabled">
        <Plus :size="14" />
        <span class="ml-1">添加约束</span>
      </ElButton>
    </div>

    <ElTable :data="localConstraints" border stripe max-height="400">
      <ElTableColumn label="序号" width="60" align="center">
        <template #default="{ $index }">
          {{ $index + 1 }}
        </template>
      </ElTableColumn>

      <ElTableColumn label="约束名" width="180">
        <template #default="{ row }">
          <ElInput v-model="row.name" placeholder="约束名" size="small" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="约束类型" width="150">
        <template #default="{ row }">
          <ElSelect v-model="row.type" placeholder="类型" size="small">
            <ElOption
              v-for="type in constraintTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </ElSelect>
        </template>
      </ElTableColumn>

      <ElTableColumn label="字段" width="180">
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

      <ElTableColumn label="定义" min-width="200">
        <template #default="{ row }">
          <ElInput
            v-model="row.definition"
            placeholder="约束定义 (如: age > 0)"
            size="small"
          />
        </template>
      </ElTableColumn>

      <ElTableColumn label="引用表" width="150" v-if="false">
        <template #default="{ row }">
          <ElInput
            v-if="row.type === 'foreign'"
            v-model="row.referencedTable"
            placeholder="引用表"
            size="small"
          />
          <span v-else class="text-gray-400 text-xs">-</span>
        </template>
      </ElTableColumn>

      <ElTableColumn label="操作" width="80" fixed="right" align="center">
        <template #default="{ $index }">
          <ElButton
            size="small"
            type="danger"
            @click="deleteConstraint($index)"
          >
            <Trash :size="14" />
          </ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div v-if="localConstraints.length === 0" class="text-center text-gray-400 py-8">
      暂无约束，点击"添加约束"开始创建
    </div>
  </div>
</template>
