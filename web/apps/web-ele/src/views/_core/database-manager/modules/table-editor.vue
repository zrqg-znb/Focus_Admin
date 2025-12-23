<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import {
  ElCard,
  ElTabs,
  ElTabPane,
  ElForm,
  ElFormItem,
  ElInput,
  ElButton,
  ElMessage,
  ElMessageBox,
  ElDialog,
} from 'element-plus';
import { Save, RotateCw, Eye } from '@vben/icons';
import FieldEditor from './field-editor.vue';
import IndexEditor from './index-editor.vue';
import ConstraintEditor from './constraint-editor.vue';
import { getTableStructureApi, executeDDLApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';
import type { TableStructure } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

// 字段定义
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

interface IndexDefinition {
  name: string;
  type: string;
  columns: string[];
  unique: boolean;
}

interface ConstraintDefinition {
  name: string;
  type: string;
  definition: string;
  columns?: string[];
  referencedTable?: string;
  referencedColumns?: string[];
}

// 表编辑数据
const loading = ref(false);
const saving = ref(false);
const tableName = ref('');
const tableComment = ref('');
const fields = ref<FieldDefinition[]>([]);
const indexes = ref<IndexDefinition[]>([]);
const constraints = ref<ConstraintDefinition[]>([]);
const originalData = ref<any>(null);

// 是否有修改
const hasChanges = computed(() => {
  if (!originalData.value) return false;
  return (
    tableName.value !== originalData.value.tableName ||
    tableComment.value !== originalData.value.tableComment ||
    JSON.stringify(fields.value) !== JSON.stringify(originalData.value.fields) ||
    JSON.stringify(indexes.value) !== JSON.stringify(originalData.value.indexes) ||
    JSON.stringify(constraints.value) !== JSON.stringify(originalData.value.constraints)
  );
});

// SQL预览
const sqlPreviewVisible = ref(false);
const generatedSQL = ref('');

// 加载表结构
async function loadTableStructure() {
  if (!props.node.meta?.dbName || !props.node.meta?.table) {
    return;
  }

  loading.value = true;
  try {
    const data = await getTableStructureApi(
      props.node.meta.dbName,
      props.node.meta.table,
      props.node.meta.database,
      props.node.meta.schema,
    );

    // 转换为编辑格式
    tableName.value = data.table_info.table_name;
    tableComment.value = data.table_info.description || '';
    
    fields.value = data.columns.map((col) => ({
      name: col.column_name,
      type: col.data_type.toLowerCase(),
      length: col.character_maximum_length,
      precision: col.numeric_precision,
      scale: col.numeric_scale,
      nullable: col.is_nullable,
      default: col.column_default,
      primaryKey: col.is_primary_key,
      unique: col.is_unique,
      comment: col.description,
    }));

    // 转换索引
    indexes.value = data.indexes.map((idx) => ({
      name: idx.index_name,
      type: idx.index_type?.toLowerCase() || 'btree',
      columns: idx.columns?.split(', ') || [],
      unique: idx.is_unique,
    }));

    // 转换约束
    constraints.value = data.constraints.map((con) => ({
      name: con.constraint_name,
      type: con.constraint_type?.toLowerCase() || 'check',
      definition: con.definition || '',
      columns: con.columns?.split(', ') || [],
    }));

    // 保存原始数据用于比较
    originalData.value = {
      tableName: tableName.value,
      tableComment: tableComment.value,
      fields: JSON.parse(JSON.stringify(fields.value)),
      indexes: JSON.parse(JSON.stringify(indexes.value)),
      constraints: JSON.parse(JSON.stringify(constraints.value)),
    };
  } catch (error) {
    console.error('Failed to load table structure:', error);
    ElMessage.error('加载表结构失败');
  } finally {
    loading.value = false;
  }
}

// 重置
function handleReset() {
  if (!originalData.value) return;
  
  ElMessageBox.confirm('确定要重置所有修改吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    tableName.value = originalData.value.tableName;
    tableComment.value = originalData.value.tableComment;
    fields.value = JSON.parse(JSON.stringify(originalData.value.fields));
    indexes.value = JSON.parse(JSON.stringify(originalData.value.indexes));
    constraints.value = JSON.parse(JSON.stringify(originalData.value.constraints));
    ElMessage.success('已重置');
  }).catch(() => {
    // 取消
  });
}

// 生成SQL
function generateSQL() {
  const sqlStatements: string[] = [];

  // 表名修改
  if (tableName.value !== originalData.value.tableName) {
    sqlStatements.push(
      `ALTER TABLE ${originalData.value.tableName} RENAME TO ${tableName.value};`
    );
  }

  // 表注释修改
  if (tableComment.value !== originalData.value.tableComment) {
    sqlStatements.push(
      `COMMENT ON TABLE ${tableName.value} IS '${tableComment.value}';`
    );
  }

  // 字段修改
  const originalFields = originalData.value.fields;
  const currentFields = fields.value;

  // 新增字段
  currentFields.forEach((field: FieldDefinition) => {
    const originalField = originalFields.find((f: FieldDefinition) => f.name === field.name);
    
    if (!originalField) {
      // 新增字段
      let fieldDef = `${field.name} ${field.type.toUpperCase()}`;
      if (field.length) fieldDef += `(${field.length})`;
      if (field.precision) fieldDef += `(${field.precision}${field.scale ? `,${field.scale}` : ''})`;
      if (!field.nullable) fieldDef += ' NOT NULL';
      if (field.default) fieldDef += ` DEFAULT ${field.default}`;
      if (field.comment) fieldDef += ` COMMENT '${field.comment}'`;
      
      sqlStatements.push(
        `ALTER TABLE ${tableName.value} ADD COLUMN ${fieldDef};`
      );
    } else {
      // 检查字段是否有修改
      const changes: string[] = [];
      
      // 类型修改
      if (field.type !== originalField.type || 
          field.length !== originalField.length ||
          field.precision !== originalField.precision ||
          field.scale !== originalField.scale) {
        let typeDef = field.type.toUpperCase();
        if (field.length) typeDef += `(${field.length})`;
        if (field.precision) typeDef += `(${field.precision}${field.scale ? `,${field.scale}` : ''})`;
        changes.push(`ALTER COLUMN ${field.name} TYPE ${typeDef}`);
      }
      
      // 可空性修改
      if (field.nullable !== originalField.nullable) {
        if (field.nullable) {
          changes.push(`ALTER COLUMN ${field.name} DROP NOT NULL`);
        } else {
          changes.push(`ALTER COLUMN ${field.name} SET NOT NULL`);
        }
      }
      
      // 默认值修改
      if (field.default !== originalField.default) {
        if (field.default) {
          changes.push(`ALTER COLUMN ${field.name} SET DEFAULT ${field.default}`);
        } else {
          changes.push(`ALTER COLUMN ${field.name} DROP DEFAULT`);
        }
      }
      
      // 注释修改
      if (field.comment !== originalField.comment) {
        sqlStatements.push(
          `COMMENT ON COLUMN ${tableName.value}.${field.name} IS '${field.comment || ''}';`
        );
      }
      
      // 应用字段修改
      if (changes.length > 0) {
        changes.forEach(change => {
          sqlStatements.push(`ALTER TABLE ${tableName.value} ${change};`);
        });
      }
    }
  });

  // 删除字段
  originalFields.forEach((field: FieldDefinition) => {
    const exists = currentFields.find(f => f.name === field.name);
    if (!exists) {
      sqlStatements.push(
        `ALTER TABLE ${tableName.value} DROP COLUMN ${field.name};`
      );
    }
  });

  return sqlStatements.join('\n\n');
}

// 预览SQL
function handlePreviewSQL() {
  generatedSQL.value = generateSQL();
  if (!generatedSQL.value) {
    ElMessage.info('没有检测到任何修改');
    return;
  }
  sqlPreviewVisible.value = true;
}

// 保存更改
async function handleSave() {
  if (!hasChanges.value) {
    ElMessage.info('没有检测到任何修改');
    return;
  }

  try {
    await ElMessageBox.confirm('确定要保存这些修改吗？', '确认保存', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });

    saving.value = true;

    // 生成SQL
    const sql = generateSQL();
    if (!sql) {
      ElMessage.warning('没有生成任何SQL语句');
      return;
    }

    // 检查必要的meta信息
    if (!props.node.meta?.dbName) {
      ElMessage.error('缺少数据库配置信息');
      return;
    }

    // 执行DDL
    const result = await executeDDLApi(props.node.meta.dbName, {
      sql,
      database: props.node.meta.database,
      schema_name: props.node.meta.schema,
    });

    if (result.success) {
      ElMessage.success('保存成功');
      // 重新加载表结构
      await loadTableStructure();
    } else {
      ElMessage.error(result.message || '保存失败');
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('保存失败:', error);
      ElMessage.error(error.message || '保存失败');
    }
  } finally {
    saving.value = false;
  }
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    loadTableStructure();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full flex flex-col gap-3">
    <!-- 基本信息 -->
    <ElCard shadow="never" v-loading="loading">
      <template #header>
        <div class="font-semibold">基本信息</div>
      </template>
      <ElForm label-width="80px">
        <ElFormItem label="表名">
          <ElInput v-model="tableName" placeholder="表名" :disabled="loading" />
        </ElFormItem>
        <ElFormItem label="Schema">
          <ElInput :model-value="node.meta?.schema" disabled />
        </ElFormItem>
        <ElFormItem label="注释">
          <ElInput
            v-model="tableComment"
            type="textarea"
            :rows="2"
            placeholder="表注释"
            :disabled="loading"
          />
        </ElFormItem>
      </ElForm>
    </ElCard>

    <!-- 字段/索引/约束 -->
    <ElCard shadow="never" class="flex-1" :body-style="{ padding: '12px', height: '100%' }" v-loading="loading">
      <ElTabs>
        <ElTabPane label="字段管理">
          <FieldEditor v-model:fields="fields" :disabled="loading" />
        </ElTabPane>
        <ElTabPane label="索引管理">
          <IndexEditor v-model:indexes="indexes" :fields="fields" :disabled="loading" />
        </ElTabPane>
        <ElTabPane label="约束管理">
          <ConstraintEditor v-model:constraints="constraints" :fields="fields" :disabled="loading" />
        </ElTabPane>
      </ElTabs>
    </ElCard>

    <!-- 操作按钮 -->
    <div class="flex justify-between items-center">
      <div class="text-sm text-gray-500">
        <span v-if="hasChanges" class="text-orange-500">● 有未保存的修改</span>
        <span v-else class="text-green-500">● 无修改</span>
      </div>
      <div class="flex gap-2">
        <ElButton @click="handleReset" :disabled="!hasChanges || saving">
          <RotateCw :size="14" />
          <span class="ml-1">重置</span>
        </ElButton>
        <ElButton @click="handlePreviewSQL" :disabled="!hasChanges || saving">
          <Eye :size="14" />
          <span class="ml-1">预览SQL</span>
        </ElButton>
        <ElButton type="primary" @click="handleSave" :disabled="!hasChanges || saving" :loading="saving">
          <Save :size="14" />
          <span class="ml-1">保存更改</span>
        </ElButton>
      </div>
    </div>

    <!-- SQL预览对话框 -->
    <ElDialog
      v-model="sqlPreviewVisible"
      title="SQL预览"
      width="800px"
    >
      <div class="sql-preview">
        <pre class="bg-gray-50 p-4 rounded text-sm overflow-auto max-h-96">{{ generatedSQL }}</pre>
      </div>
      <template #footer>
        <ElButton @click="sqlPreviewVisible = false">关闭</ElButton>
        <ElButton type="primary" @click="handleSave">
          执行SQL
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.sql-preview pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  line-height: 1.6;
}
</style>
