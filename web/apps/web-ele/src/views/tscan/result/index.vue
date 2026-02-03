<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listResultsApi, applyShieldApi, listTasksApi } from '#/api/tscan';
import { useColumns } from './data';
import { ElButton, ElTag, ElMessageBox, ElMessage, ElSelect, ElOption, ElDialog, ElInput, ElForm, ElFormItem } from 'element-plus';
import { useRoute } from 'vue-router';
import { listUsersApi } from '#/api/core/user';

const route = useRoute();
const projectId = route.query.projectId as string;
const tasks = ref<any[]>([]);
const currentTaskId = ref('');
const users = ref<any[]>([]);

const shieldVisible = ref(false);
const shieldForm = ref({
  result_ids: [] as string[],
  approver_id: '',
  reason: '',
});

const gridOptions: any = {
  columns: useColumns(),
  proxyConfig: {
    ajax: {
      query: async () => {
        if (!currentTaskId.value) return { items: [] };
        const res = await listResultsApi(currentTaskId.value);
        return { items: res };
      },
    },
  },
};

const [Grid, gridApi] = useVbenVxeGrid({ gridOptions });

onMounted(async () => {
  if (projectId) {
    tasks.value = await listTasksApi(projectId);
    if (tasks.value.length > 0) {
      currentTaskId.value = tasks.value[0].id;
      gridApi.reload();
    }
  }
  const userRes = await listUsersApi();
  users.value = userRes.items || [];
});

function handleTaskChange() {
  gridApi.reload();
}

function handleApplyShield() {
  const selected = gridApi.grid?.getCheckboxRecords();
  if (!selected || selected.length === 0) {
    ElMessage.warning('请选择要屏蔽的缺陷');
    return;
  }
  shieldForm.value.result_ids = selected.map((item: any) => item.id);
  shieldVisible.value = true;
}

async function submitShield() {
  try {
    await applyShieldApi(shieldForm.value);
    ElMessage.success('申请已提交');
    shieldVisible.value = false;
    gridApi.reload();
  } catch (error) {
    ElMessage.error('提交失败');
  }
}

const getSeverityType = (severity: string) => {
  if (severity === 'High') return 'danger';
  if (severity === 'Medium') return 'warning';
  return 'info';
};

const getStatusType = (status: string) => {
  if (status === 'Shielded') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
};
</script>

<template>
  <Page title="扫描结果分析">
    <template #extra>
      <div class="flex items-center gap-4">
        <span>选择任务：</span>
        <ElSelect v-model="currentTaskId" placeholder="请选择扫描任务" @change="handleTaskChange" style="width: 200px">
          <ElOption v-for="task in tasks" :key="task.id" :label="task.sys_create_datetime" :value="task.id" />
        </ElSelect>
        <ElButton type="warning" @click="handleApplyShield">申请屏蔽</ElButton>
      </div>
    </template>

    <Grid>
      <template #severity="{ row }">
        <ElTag :type="getSeverityType(row.severity)">{{ row.severity }}</ElTag>
      </template>
      <template #shield_status="{ row }">
        <ElTag :type="getStatusType(row.shield_status)">{{ row.shield_status }}</ElTag>
      </template>
    </Grid>

    <ElDialog v-model="shieldVisible" title="申请屏蔽" width="500px">
      <ElForm :model="shieldForm" label-width="100px">
        <ElFormItem label="审批人" required>
          <ElSelect v-model="shieldForm.approver_id" placeholder="请选择审批人" filterable class="w-full">
            <ElOption v-for="user in users" :key="user.id" :label="user.name || user.username" :value="user.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="屏蔽理由" required>
          <ElInput v-model="shieldForm.reason" type="textarea" placeholder="请输入理由" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="shieldVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitShield">提交</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
