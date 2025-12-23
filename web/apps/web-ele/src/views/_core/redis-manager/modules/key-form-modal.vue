<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElTag,
} from 'element-plus';

import {
  createRedisKeyApi,
  getRedisKeyDetailApi,
  updateRedisKeyApi,
} from '#/api/core/redis-manager';

interface Props {
  visible: boolean;
  dbIndex: number;
  mode: 'create' | 'edit';
  editingKey?: string;
}

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 表单数据
const formData = reactive({
  key: '',
  type: 'string' as 'string' | 'list' | 'set' | 'zset' | 'hash',
  value: '',
  ttl: -1,
});

// 复杂类型的值
const listValue = ref<string[]>(['']);
const setValue = ref<string[]>(['']);
const zsetValue = ref<Array<{ member: string; score: number }>>([
  { member: '', score: 0 },
]);
const hashValue = ref<Array<{ field: string; value: string }>>([
  { field: '', value: '' },
]);

const loading = ref(false);
const formRef = ref();

// 类型选项
const typeOptions = [
  { label: 'String', value: 'string' },
  { label: 'List', value: 'list' },
  { label: 'Set', value: 'set' },
  { label: 'ZSet', value: 'zset' },
  { label: 'Hash', value: 'hash' },
];

// 表单规则
const rules = {
  key: [{ required: true, message: '请输入键名', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  value: [{ required: true, message: '请输入值', trigger: 'blur' }],
};

// 对话框标题
const dialogTitle = computed(() => {
  return props.mode === 'create' ? '新增键' : '编辑键';
});

// 加载键详情（编辑模式）
async function loadKeyDetail() {
  if (props.mode !== 'edit' || !props.editingKey) return;

  try {
    loading.value = true;
    const detail = await getRedisKeyDetailApi(props.dbIndex, props.editingKey);

    formData.key = detail.key;
    formData.type = detail.type;
    formData.ttl = detail.ttl;

    // 根据类型设置值
    if (detail.type === 'string') {
      formData.value = detail.value;
    } else if (detail.type === 'list') {
      listValue.value = detail.value || [''];
    } else if (detail.type === 'set') {
      setValue.value = detail.value || [''];
    } else if (detail.type === 'zset') {
      zsetValue.value = detail.value || [{ member: '', score: 0 }];
    } else if (detail.type === 'hash') {
      hashValue.value = Object.entries(detail.value || {}).map(
        ([field, value]) => ({
          field,
          value: value as string,
        }),
      );
      if (hashValue.value.length === 0) {
        hashValue.value = [{ field: '', value: '' }];
      }
    }
  } catch (error) {
    console.error('Failed to load key detail:', error);
    ElMessage.error('加载键详情失败');
  } finally {
    loading.value = false;
  }
}

// 重置表单
function resetForm() {
  formData.key = '';
  formData.type = 'string';
  formData.value = '';
  formData.ttl = -1;
  listValue.value = [''];
  setValue.value = [''];
  zsetValue.value = [{ member: '', score: 0 }];
  hashValue.value = [{ field: '', value: '' }];
  formRef.value?.clearValidate();
}

// 添加列表项
function addListItem() {
  listValue.value.push('');
}

// 删除列表项
function removeListItem(index: number) {
  if (listValue.value.length > 1) {
    listValue.value.splice(index, 1);
  }
}

// 添加集合成员
function addSetMember() {
  setValue.value.push('');
}

// 删除集合成员
function removeSetMember(index: number) {
  if (setValue.value.length > 1) {
    setValue.value.splice(index, 1);
  }
}

// 添加有序集合成员
function addZSetMember() {
  zsetValue.value.push({ member: '', score: 0 });
}

// 删除有序集合成员
function removeZSetMember(index: number) {
  if (zsetValue.value.length > 1) {
    zsetValue.value.splice(index, 1);
  }
}

// 添加哈希字段
function addHashField() {
  hashValue.value.push({ field: '', value: '' });
}

// 删除哈希字段
function removeHashField(index: number) {
  if (hashValue.value.length > 1) {
    hashValue.value.splice(index, 1);
  }
}

// 获取提交的值
function getSubmitValue() {
  if (formData.type === 'string') {
    return formData.value;
  } else if (formData.type === 'list') {
    return listValue.value.filter((v) => v.trim() !== '');
  } else if (formData.type === 'set') {
    return setValue.value.filter((v) => v.trim() !== '');
  } else if (formData.type === 'zset') {
    return zsetValue.value.filter((v) => v.member.trim() !== '');
  } else if (formData.type === 'hash') {
    const result: Record<string, string> = {};
    for (const item of hashValue.value) {
      if (item.field.trim() !== '') {
        result[item.field] = item.value;
      }
    }
    return result;
  }
  return formData.value;
}

// 提交表单
async function handleSubmit() {
  try {
    await formRef.value?.validate();

    loading.value = true;

    const value = getSubmitValue();

    if (props.mode === 'create') {
      await createRedisKeyApi(props.dbIndex, {
        key: formData.key,
        type: formData.type,
        value,
        ttl: formData.ttl,
      });
      ElMessage.success('创建成功');
    } else {
      await updateRedisKeyApi(props.dbIndex, formData.key, {
        value,
        ttl: formData.ttl,
      });
      ElMessage.success('更新成功');
    }

    emit('success');
    handleClose();
  } catch (error: any) {
    if (error !== false) {
      console.error('Failed to submit:', error);
      ElMessage.error(props.mode === 'create' ? '创建失败' : '更新失败');
    }
  } finally {
    loading.value = false;
  }
}

// 关闭对话框
function handleClose() {
  emit('update:visible', false);
  resetForm();
}

// 监听对话框打开
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      if (props.mode === 'edit') {
        loadKeyDetail();
      } else {
        resetForm();
      }
    }
  },
);
</script>

<template>
  <ElDialog
    :model-value="visible"
    :title="dialogTitle"
    width="600px"
    @close="handleClose"
  >
    <ElForm
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="80px"
    >
      <ElFormItem label="键名" prop="key">
        <ElInput
          v-model="formData.key"
          placeholder="请输入键名"
          :disabled="mode === 'edit'"
        />
      </ElFormItem>

      <ElFormItem label="类型" prop="type">
        <ElSelect
          v-model="formData.type"
          placeholder="请选择类型"
          :disabled="mode === 'edit'"
          style="width: 100%"
        >
          <ElOption
            v-for="option in typeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </ElSelect>
      </ElFormItem>

      <!-- String 类型 -->
      <ElFormItem v-if="formData.type === 'string'" label="值" prop="value">
        <ElInput
          v-model="formData.value"
          type="textarea"
          :rows="4"
          placeholder="请输入值"
        />
      </ElFormItem>

      <!-- List 类型 -->
      <ElFormItem v-if="formData.type === 'list'" label="列表项">
        <div class="w-full space-y-2">
          <div
            v-for="(item, index) in listValue"
            :key="index"
            class="flex gap-2"
          >
            <ElInput
              v-model="listValue[index]"
              placeholder="请输入列表项"
            />
            <ElButton
              v-if="listValue.length > 1"
              type="danger"
              @click="removeListItem(index)"
            >
              删除
            </ElButton>
          </div>
          <ElButton type="primary" @click="addListItem">添加项</ElButton>
        </div>
      </ElFormItem>

      <!-- Set 类型 -->
      <ElFormItem v-if="formData.type === 'set'" label="集合成员">
        <div class="w-full space-y-2">
          <div
            v-for="(item, index) in setValue"
            :key="index"
            class="flex gap-2"
          >
            <ElInput
              v-model="setValue[index]"
              placeholder="请输入成员"
            />
            <ElButton
              v-if="setValue.length > 1"
              type="danger"
              @click="removeSetMember(index)"
            >
              删除
            </ElButton>
          </div>
          <ElButton type="primary" @click="addSetMember">添加成员</ElButton>
        </div>
      </ElFormItem>

      <!-- ZSet 类型 -->
      <ElFormItem v-if="formData.type === 'zset'" label="有序集合">
        <div class="w-full space-y-2">
          <div
            v-for="(item, index) in zsetValue"
            :key="index"
            class="flex gap-2"
          >
            <ElInput
              v-model="zsetValue[index].member"
              placeholder="成员"
              style="flex: 2"
            />
            <ElInputNumber
              v-model="zsetValue[index].score"
              placeholder="分数"
              style="flex: 1"
            />
            <ElButton
              v-if="zsetValue.length > 1"
              type="danger"
              @click="removeZSetMember(index)"
            >
              删除
            </ElButton>
          </div>
          <ElButton type="primary" @click="addZSetMember">添加成员</ElButton>
        </div>
      </ElFormItem>

      <!-- Hash 类型 -->
      <ElFormItem v-if="formData.type === 'hash'" label="哈希字段">
        <div class="w-full space-y-2">
          <div
            v-for="(item, index) in hashValue"
            :key="index"
            class="flex gap-2"
          >
            <ElInput
              v-model="hashValue[index].field"
              placeholder="字段名"
              style="flex: 1"
            />
            <ElInput
              v-model="hashValue[index].value"
              placeholder="字段值"
              style="flex: 2"
            />
            <ElButton
              v-if="hashValue.length > 1"
              type="danger"
              @click="removeHashField(index)"
            >
              删除
            </ElButton>
          </div>
          <ElButton type="primary" @click="addHashField">添加字段</ElButton>
        </div>
      </ElFormItem>

      <ElFormItem label="过期时间">
        <div class="flex items-center gap-2">
          <ElInputNumber
            v-model="formData.ttl"
            :min="-1"
            placeholder="秒"
            style="flex: 1"
          />
          <ElTag size="small" type="info">
            -1表示永不过期
          </ElTag>
        </div>
      </ElFormItem>
    </ElForm>

    <template #footer>
      <ElButton @click="handleClose">取消</ElButton>
      <ElButton type="primary" :loading="loading" @click="handleSubmit">
        {{ mode === 'create' ? '创建' : '更新' }}
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
/* 自定义样式 */
</style>
