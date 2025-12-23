<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElButton,
  ElMessage,
  ElTabs,
  ElTabPane,
} from 'element-plus';
import { Save, Eye } from '@vben/icons';
import FieldEditor from './field-editor.vue';
import IndexEditor from './index-editor.vue';
import ConstraintEditor from './constraint-editor.vue';
import { executeDDLApi } from '#/api/core/database-manager';

interface Props {
  visible: boolean;
  dbName: string;
  database: string;
  schema?: string;
  dbType: string;
}

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'success', tableName: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

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
  autoIncrement?: boolean;
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

// 表单数据
const tableName = ref('');
const tableComment = ref('');
const fields = ref<FieldDefinition[]>([
  {
    name: 'id',
    type: 'integer',
    nullable: false,
    primaryKey: true,
    unique: false,
    autoIncrement: true,
    comment: '主键ID',
  },
]);
const indexes = ref<IndexDefinition[]>([]);
const constraints = ref<ConstraintDefinition[]>([]);

// SQL预览
const sqlPreviewVisible = ref(false);
const generatedSQL = ref('');

// Loading状态
const loading = ref(false);

// 表单验证
const formValid = computed(() => {
  return tableName.value.trim() !== '' && fields.value.length > 0;
});

// 生成CREATE TABLE SQL
function generateCreateTableSQL(): string {
  const sqlLines: string[] = [];
  const { dbType } = props;
  
  // CREATE TABLE语句开始
  const fullTableName = props.schema 
    ? `"${props.schema}"."${tableName.value}"`
    : `"${tableName.value}"`;
  
  sqlLines.push(`CREATE TABLE ${fullTableName} (`);
  
  // 字段定义
  const fieldDefs: string[] = [];
  const primaryKeys: string[] = [];
  
  fields.value.forEach((field) => {
    let fieldDef = `  "${field.name}" ${field.type.toUpperCase()}`;
    
    // 长度/精度
    if (field.length) {
      fieldDef += `(${field.length})`;
    } else if (field.precision) {
      fieldDef += `(${field.precision}${field.scale ? `,${field.scale}` : ''})`;
    }
    
    // 自增（根据数据库类型）
    if (field.autoIncrement) {
      if (dbType === 'PostgreSQL') {
        fieldDef = `  "${field.name}" SERIAL`;
      } else if (dbType === 'MySQL') {
        fieldDef += ' AUTO_INCREMENT';
      } else if (dbType === 'SQL Server') {
        fieldDef += ' IDENTITY(1,1)';
      }
    }
    
    // NOT NULL
    if (!field.nullable) {
      fieldDef += ' NOT NULL';
    }
    
    // DEFAULT
    if (field.default) {
      fieldDef += ` DEFAULT ${field.default}`;
    }
    
    // UNIQUE
    if (field.unique && !field.primaryKey) {
      fieldDef += ' UNIQUE';
    }
    
    // 注释（MySQL支持）
    if (field.comment && dbType === 'MySQL') {
      fieldDef += ` COMMENT '${field.comment}'`;
    }
    
    fieldDefs.push(fieldDef);
    
    // 收集主键
    if (field.primaryKey) {
      primaryKeys.push(`"${field.name}"`);
    }
  });
  
  // 添加字段定义
  sqlLines.push(...fieldDefs.map((def, idx) => 
    idx < fieldDefs.length - 1 || primaryKeys.length > 0 || constraints.value.length > 0 
      ? def + ',' 
      : def
  ));
  
  // 主键约束
  if (primaryKeys.length > 0) {
    const pkConstraint = `  PRIMARY KEY (${primaryKeys.join(', ')})`;
    sqlLines.push(
      constraints.value.length > 0 ? pkConstraint + ',' : pkConstraint
    );
  }
  
  // 其他约束
  constraints.value.forEach((constraint, idx) => {
    let constraintDef = `  CONSTRAINT "${constraint.name}"`;
    
    if (constraint.type === 'unique') {
      constraintDef += ` UNIQUE (${constraint.columns?.map(c => `"${c}"`).join(', ')})`;
    } else if (constraint.type === 'check') {
      constraintDef += ` CHECK (${constraint.definition})`;
    } else if (constraint.type === 'foreign key') {
      constraintDef += ` FOREIGN KEY (${constraint.columns?.map(c => `"${c}"`).join(', ')})`;
      constraintDef += ` REFERENCES "${constraint.referencedTable}" (${constraint.referencedColumns?.map(c => `"${c}"`).join(', ')})`;
    }
    
    if (idx < constraints.value.length - 1) {
      constraintDef += ',';
    }
    
    sqlLines.push(constraintDef);
  });
  
  sqlLines.push(');');
  
  // 表注释（PostgreSQL）
  if (tableComment.value && dbType === 'PostgreSQL') {
    sqlLines.push('');
    sqlLines.push(`COMMENT ON TABLE ${fullTableName} IS '${tableComment.value}';`);
  }
  
  // 列注释（PostgreSQL）
  if (dbType === 'PostgreSQL') {
    fields.value.forEach((field) => {
      if (field.comment) {
        sqlLines.push(`COMMENT ON COLUMN ${fullTableName}."${field.name}" IS '${field.comment}';`);
      }
    });
  }
  
  // 索引
  indexes.value.forEach((index) => {
    sqlLines.push('');
    const indexType = index.unique ? 'UNIQUE INDEX' : 'INDEX';
    const indexMethod = index.type.toUpperCase();
    sqlLines.push(
      `CREATE ${indexType} "${index.name}" ON ${fullTableName} USING ${indexMethod} (${index.columns.map(c => `"${c}"`).join(', ')});`
    );
  });
  
  return sqlLines.join('\n');
}

// 预览SQL
function handlePreviewSQL() {
  if (!formValid.value) {
    ElMessage.warning('请填写表名并至少添加一个字段');
    return;
  }
  
  generatedSQL.value = generateCreateTableSQL();
  sqlPreviewVisible.value = true;
}

// 创建表
async function handleCreate() {
  if (!formValid.value) {
    ElMessage.warning('请填写表名并至少添加一个字段');
    return;
  }
  
  try {
    loading.value = true;
    
    // 生成SQL
    const sql = generateCreateTableSQL();
    
    // 调用API执行DDL
    const result = await executeDDLApi(props.dbName, {
      sql,
      database: props.database,
      schema_name: props.schema,
    });
    
    if (result.success) {
      ElMessage.success('表创建成功');
      emit('update:visible', false);
      emit('success', tableName.value);
    } else {
      ElMessage.error(result.message || '创建表失败');
    }
  } catch (error: any) {
    console.error('创建表失败:', error);
    ElMessage.error(error.message || '创建表失败');
  } finally {
    loading.value = false;
  }
}

// 重置表单
function resetForm() {
  tableName.value = '';
  tableComment.value = '';
  fields.value = [
    {
      name: 'id',
      type: 'integer',
      nullable: false,
      primaryKey: true,
      unique: false,
      autoIncrement: true,
      comment: '主键ID',
    },
  ];
  indexes.value = [];
  constraints.value = [];
}

// 关闭对话框
function handleClose() {
  emit('update:visible', false);
  // 延迟重置，避免关闭动画时看到数据变化
  setTimeout(resetForm, 300);
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    title="创建新表"
    width="900px"
    :before-close="handleClose"
    @update:model-value="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <!-- 基本信息 -->
      <ElForm label-width="80px">
        <ElFormItem label="数据库" required>
          <ElInput :model-value="database" disabled />
        </ElFormItem>
        <ElFormItem v-if="schema" label="Schema">
          <ElInput :model-value="schema" disabled />
        </ElFormItem>
        <ElFormItem label="表名" required>
          <ElInput
            v-model="tableName"
            placeholder="请输入表名"
            clearable
          />
        </ElFormItem>
        <ElFormItem label="表注释">
          <ElInput
            v-model="tableComment"
            type="textarea"
            :rows="2"
            placeholder="请输入表注释（可选）"
          />
        </ElFormItem>
      </ElForm>

      <!-- 字段/索引/约束 -->
      <div class="border rounded p-3">
        <ElTabs>
          <ElTabPane label="字段管理">
            <FieldEditor v-model:fields="fields" />
          </ElTabPane>
          <ElTabPane label="索引管理">
            <IndexEditor v-model:indexes="indexes" :fields="fields" />
          </ElTabPane>
          <ElTabPane label="约束管理">
            <ConstraintEditor v-model:constraints="constraints" :fields="fields" />
          </ElTabPane>
        </ElTabs>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between items-center w-full">
        <div class="text-sm text-gray-500">
          数据库类型: {{ dbType }}
        </div>
        <div class="flex gap-2">
          <ElButton @click="handleClose" :disabled="loading">取消</ElButton>
          <ElButton @click="handlePreviewSQL" :disabled="loading">
            <Eye :size="14" />
            <span class="ml-1">预览SQL</span>
          </ElButton>
          <ElButton type="primary" @click="handleCreate" :disabled="!formValid || loading" :loading="loading">
            <Save :size="14" />
            <span class="ml-1">创建表</span>
          </ElButton>
        </div>
      </div>
    </template>

    <!-- SQL预览对话框 -->
    <ElDialog
      v-model="sqlPreviewVisible"
      title="CREATE TABLE SQL预览"
      width="800px"
      append-to-body
    >
      <div class="sql-preview">
        <pre class="bg-gray-50 p-4 rounded text-sm overflow-auto max-h-96">{{ generatedSQL }}</pre>
      </div>
      <template #footer>
        <ElButton @click="sqlPreviewVisible = false">关闭</ElButton>
        <ElButton type="primary" @click="handleCreate">
          执行创建
        </ElButton>
      </template>
    </ElDialog>
  </ElDialog>
</template>

<style scoped>
.sql-preview pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  line-height: 1.6;
}
</style>
