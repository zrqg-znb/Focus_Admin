<script lang="ts" setup>
import type { ComplianceBranch, ComplianceRecord } from '#/api/compliance';

import { ref } from 'vue';

import {
  ElButton,
  ElDialog,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { updateBranchStatus } from '#/api/compliance';

const props = defineProps<{
  record: ComplianceRecord | null;
}>();

const visible = defineModel<boolean>({ default: false });
const emit = defineEmits(['submit']);

const statusMap: Record<number, string> = {
  0: '待处理',
  1: '无风险',
  2: '已修复',
};

const statusTypeMap: Record<number, string> = {
  0: 'danger',
  1: 'info',
  2: 'success',
};

// Local state for edits
const editingRows = ref<Record<string, { remark: string; status: number }>>({});

const initEdit = (branch: ComplianceBranch) => {
  editingRows.value[branch.id] = {
    status: branch.status,
    remark: '',
  };
};

const handleUpdate = async (
  branch: ComplianceBranch,
  status: number,
  remark: string,
) => {
  try {
    await updateBranchStatus(branch.id, { status, remark });
    ElMessage.success(`分支 ${branch.branch_name} 更新成功`);
    // Update local object to reflect change immediately in UI (though parent reload will also help)
    branch.status = status;
    emit('submit'); // Trigger parent reload
  } catch (error) {
    // error handled by interceptor
  }
};

const handleSave = async (branch: ComplianceBranch) => {
  const edit = editingRows.value[branch.id];
  if (edit) {
    await handleUpdate(branch, edit.status, edit.remark);
    // Clear remark after save
    edit.remark = '';
  }
};

const handleOpen = () => {
  editingRows.value = {};
  if (props.record?.branches) {
    props.record.branches.forEach((b) => initEdit(b));
  }
};
</script>

<template>
  <ElDialog
    v-model="visible"
    append-to-body
    title="分支风险处理"
    width="900px"
    @open="handleOpen"
  >
    <div class="flex flex-col gap-4">
      <div v-if="record" class="mb-2 text-sm text-gray-600">
        <p><strong>ChangeId:</strong> {{ record.change_id }}</p>
        <p><strong>Title:</strong> {{ record.title }}</p>
      </div>

      <ElTable :data="record?.branches || []" border stripe>
        <ElTableColumn label="分支名称" prop="branch_name" width="150" />
        <ElTableColumn label="当前状态" width="100">
          <template #default="{ row }">
            <ElTag :type="statusTypeMap[row.status]">{{
              statusMap[row.status]
            }}</ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn label="处理状态" width="140">
          <template #default="{ row }">
            <div v-if="editingRows[row.id]">
              <ElSelect v-model="editingRows[row.id].status" size="small">
                <ElOption
                  v-for="(label, val) in statusMap"
                  :key="val"
                  :label="label"
                  :value="Number(val)"
                />
              </ElSelect>
            </div>
          </template>
        </ElTableColumn>

        <ElTableColumn label="备注" min-width="200">
          <template #default="{ row }">
            <div v-if="editingRows[row.id]">
              <ElInput
                v-model="editingRows[row.id].remark"
                placeholder="添加备注"
                size="small"
              />
            </div>
          </template>
        </ElTableColumn>

        <ElTableColumn fixed="right" label="操作" width="100">
          <template #default="{ row }">
            <ElButton size="small" type="primary" @click="handleSave(row)"
              >保存</ElButton
            >
          </template>
        </ElTableColumn>
      </ElTable>

      <div v-if="record?.remark" class="mt-2 border-t pt-4">
        <h4 class="mb-2 font-bold text-gray-700">整体备注/历史记录</h4>
        <pre
          class="whitespace-pre-wrap rounded bg-gray-50 p-2 text-xs text-gray-600"
          >{{ record.remark }}</pre
        >
      </div>

      <div class="mt-2 border-t pt-4">
        <h4 class="mb-2 font-bold text-gray-700">分支备注详情</h4>
        <div v-for="branch in record?.branches" :key="branch.id" class="mb-2">
          <div v-if="branch.remark">
            <span class="text-xs font-bold">{{ branch.branch_name }}:</span>
            <pre
              class="mt-1 whitespace-pre-wrap rounded bg-gray-50 p-2 text-xs text-gray-600"
              >{{ branch.remark }}</pre
            >
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <ElButton @click="visible = false">关闭</ElButton>
    </template>
  </ElDialog>
</template>
