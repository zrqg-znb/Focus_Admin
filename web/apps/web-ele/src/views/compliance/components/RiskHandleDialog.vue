<script lang="ts" setup>
import type { ComplianceRecord } from '#/api/compliance';

import { ref, computed } from 'vue';
import { ElButton, ElDialog, ElInput, ElRadioGroup, ElRadioButton, ElForm, ElFormItem, ElTimeline, ElTimelineItem, ElTag } from 'element-plus';

const props = defineProps<{
  record: ComplianceRecord | null;
}>();

const visible = defineModel<boolean>({ default: false });
const emit = defineEmits(['submit']);

const form = ref({
  status: 0,
  remark: '',
});

const statusMap: Record<number, string> = {
  0: '待处理',
  1: '无风险',
  2: '已修复',
};

const handleOpen = () => {
  if (props.record) {
    form.value.status = props.record.status;
    form.value.remark = '';
  }
};

const handleSubmit = () => {
  emit('submit', {
    ...props.record,
    status: form.value.status,
  }, form.value.remark);
  visible.value = false;
};

// Parse remarks log
const logs = computed(() => {
  if (!props.record?.remark) return [];
  // Split by newline and filter empty
  return props.record.remark.split('\n').filter(line => line.trim());
});
</script>

<template>
  <ElDialog
    v-model="visible"
    title="风险处理"
    width="600px"
    @open="handleOpen"
    append-to-body
  >
    <div class="flex flex-col gap-4">
      <div v-if="record" class="text-sm text-gray-600 mb-2">
        <p><strong>ChangeId:</strong> {{ record.change_id }}</p>
        <p><strong>Title:</strong> {{ record.title }}</p>
      </div>

      <ElForm layout="vertical">
        <ElFormItem label="处理状态">
          <ElRadioGroup v-model="form.status">
            <ElRadioButton :label="0">待处理</ElRadioButton>
            <ElRadioButton :label="1">无风险</ElRadioButton>
            <ElRadioButton :label="2">已修复</ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="处理备注">
          <ElInput
            v-model="form.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入处理备注（必填）"
          />
        </ElFormItem>
      </ElForm>

      <div v-if="logs.length > 0" class="border-t pt-4 mt-2">
        <h4 class="mb-3 font-bold text-gray-700">处理记录</h4>
        <ElTimeline>
          <ElTimelineItem
            v-for="(log, index) in logs"
            :key="index"
            :timestamp="log.match(/^\[(.*?)\]/)?.[1] || ''"
            placement="top"
          >
            {{ log.replace(/^\[.*?\]\s*/, '') }}
          </ElTimelineItem>
        </ElTimeline>
      </div>
    </div>
    
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" @click="handleSubmit" :disabled="!form.remark">确认提交</ElButton>
    </template>
  </ElDialog>
</template>
