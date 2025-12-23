<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  ElTable,
  ElTableColumn,
  ElInput,
  ElSelect,
  ElOption,
  ElInputNumber,
  ElCheckbox,
  ElButton,
  ElMessage,
} from 'element-plus';
import { Plus, ArrowUp, ArrowDown, Trash } from '@vben/icons';

interface FieldDefinition {
  name: string;
  type: string;
  length?: number;
  precision?: number;
  scale?: number;
  nullable: boolean;
  default?: string;
  primaryKey: boolean;
  unique: boolean;
  comment?: string;
}

interface Props {
  fields: FieldDefinition[];
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});
const emit = defineEmits<{
  'update:fields': [fields: FieldDefinition[]];
}>();

// 数据类型选项
const dataTypes = [
  { label: 'VARCHAR', value: 'varchar', hasLength: true, desc: '可变长度字符串' },
  { label: 'CHAR', value: 'char', hasLength: true, desc: '固定长度字符串' },
  { label: 'TEXT', value: 'text', hasLength: false, desc: '长文本' },
  { label: 'INT', value: 'int', hasLength: false, desc: '整数 (-2^31 ~ 2^31-1)' },
  { label: 'INTEGER', value: 'integer', hasLength: false, desc: '整数 (同INT)' },
  { label: 'BIGINT', value: 'bigint', hasLength: false, desc: '大整数 (-2^63 ~ 2^63-1)' },
  { label: 'SMALLINT', value: 'smallint', hasLength: false, desc: '小整数 (-32768 ~ 32767)' },
  { label: 'DECIMAL', value: 'decimal', hasPrecision: true, desc: '精确小数' },
  { label: 'NUMERIC', value: 'numeric', hasPrecision: true, desc: '精确数值 (同DECIMAL)' },
  { label: 'FLOAT', value: 'float', hasLength: false, desc: '单精度浮点数' },
  { label: 'DOUBLE', value: 'double', hasLength: false, desc: '双精度浮点数' },
  { label: 'BOOLEAN', value: 'boolean', hasLength: false, desc: '布尔值 (true/false)' },
  { label: 'DATE', value: 'date', hasLength: false, desc: '日期 (年-月-日)' },
  { label: 'TIME', value: 'time', hasLength: false, desc: '时间 (时:分:秒)' },
  { label: 'TIMESTAMP', value: 'timestamp', hasLength: false, desc: '时间戳 (日期+时间)' },
  { label: 'DATETIME', value: 'datetime', hasLength: false, desc: '日期时间' },
  { label: 'JSON', value: 'json', hasLength: false, desc: 'JSON数据' },
  { label: 'JSONB', value: 'jsonb', hasLength: false, desc: '二进制JSON (PostgreSQL)' },
  { label: 'UUID', value: 'uuid', hasLength: false, desc: '通用唯一标识符' },
];

const localFields = computed({
  get: () => props.fields,
  set: (value) => emit('update:fields', value),
});

// 添加字段
function addField() {
  const newField: FieldDefinition = {
    name: '',
    type: 'varchar',
    length: 255,
    nullable: true,
    primaryKey: false,
    unique: false,
    default: undefined,
    comment: '',
  };
  localFields.value = [...localFields.value, newField];
}

// 删除字段
function deleteField(index: number) {
  localFields.value = localFields.value.filter((_, i) => i !== index);
  ElMessage.success('字段已删除');
}

// 上移字段
function moveUp(index: number) {
  if (index === 0) return;
  const newFields = [...localFields.value];
  const temp = newFields[index - 1];
  newFields[index - 1] = newFields[index];
  newFields[index] = temp;
  localFields.value = newFields;
}

// 下移字段
function moveDown(index: number) {
  if (index === localFields.value.length - 1) return;
  const newFields = [...localFields.value];
  const temp = newFields[index];
  newFields[index] = newFields[index + 1];
  newFields[index + 1] = temp;
  localFields.value = newFields;
}

// 检查类型是否需要长度
function needsLength(type: string) {
  const typeInfo = dataTypes.find(t => t.value === type);
  return typeInfo?.hasLength || false;
}

// 检查类型是否需要精度
function needsPrecision(type: string) {
  const typeInfo = dataTypes.find(t => t.value === type);
  return typeInfo?.hasPrecision || false;
}
</script>

<template>
  <div class="field-editor">
    <div class="mb-3 flex justify-between items-center">
      <div class="text-sm font-semibold">字段列表</div>
      <ElButton type="primary" size="small" @click="addField" :disabled="disabled">
        <Plus :size="14" />
        <span class="ml-1">添加字段</span>
      </ElButton>
    </div>

    <ElTable :data="localFields" border stripe max-height="500">
      <ElTableColumn label="序号" width="60" align="center">
        <template #default="{ $index }">
          {{ $index + 1 }}
        </template>
      </ElTableColumn>

      <ElTableColumn label="字段名" width="150">
        <template #default="{ row }">
          <ElInput v-model="row.name" placeholder="字段名" size="small" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="数据类型" width="150">
        <template #default="{ row }">
          <ElSelect v-model="row.type" placeholder="类型" size="small">
            <ElOption
              v-for="type in dataTypes"
              :key="type.value"
              :label="`${type.label} - ${type.desc}`"
              :value="type.value"
            >
              <div class="flex justify-between items-center">
                <span class="font-medium">{{ type.label }}</span>
                <span class="text-xs text-gray-500 ml-2">{{ type.desc }}</span>
              </div>
            </ElOption>
          </ElSelect>
        </template>
      </ElTableColumn>

      <ElTableColumn label="长度/精度" width="100">
        <template #default="{ row }">
          <ElInputNumber
            v-if="needsLength(row.type)"
            v-model="row.length"
            :min="1"
            :max="65535"
            size="small"
            controls-position="right"
          />
          <ElInputNumber
            v-else-if="needsPrecision(row.type)"
            v-model="row.precision"
            :min="1"
            :max="65"
            size="small"
            controls-position="right"
          />
          <span v-else class="text-gray-400 text-xs">-</span>
        </template>
      </ElTableColumn>

      <ElTableColumn label="小数位" width="80">
        <template #default="{ row }">
          <ElInputNumber
            v-if="needsPrecision(row.type)"
            v-model="row.scale"
            :min="0"
            :max="30"
            size="small"
            controls-position="right"
          />
          <span v-else class="text-gray-400 text-xs">-</span>
        </template>
      </ElTableColumn>

      <ElTableColumn label="可空" width="60" align="center">
        <template #default="{ row }">
          <ElCheckbox v-model="row.nullable" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="默认值" width="120">
        <template #default="{ row }">
          <ElInput v-model="row.default" placeholder="默认值" size="small" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="主键" width="60" align="center">
        <template #default="{ row }">
          <ElCheckbox v-model="row.primaryKey" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="唯一" width="60" align="center">
        <template #default="{ row }">
          <ElCheckbox v-model="row.unique" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="注释" min-width="150">
        <template #default="{ row }">
          <ElInput v-model="row.comment" placeholder="字段注释" size="small" />
        </template>
      </ElTableColumn>

      <ElTableColumn label="操作" width="140" fixed="right" align="center">
        <template #default="{ $index }">
          <div class="flex gap-1 justify-center">
            <ElButton
              size="small"
              :disabled="$index === 0"
              @click="moveUp($index)"
            >
              <ArrowUp :size="14" />
            </ElButton>
            <ElButton
              size="small"
              :disabled="$index === localFields.length - 1"
              @click="moveDown($index)"
            >
              <ArrowDown :size="14" />
            </ElButton>
            <ElButton
              size="small"
              type="danger"
              @click="deleteField($index)"
            >
              <Trash :size="14" />
            </ElButton>
          </div>
        </template>
      </ElTableColumn>
    </ElTable>

    <div v-if="localFields.length === 0" class="text-center text-gray-400 py-8">
      暂无字段，点击"添加字段"开始创建
    </div>
  </div>
</template>

<style scoped>
.field-editor :deep(.el-input__inner),
.field-editor :deep(.el-input-number__inner) {
  text-align: left;
}
</style>
