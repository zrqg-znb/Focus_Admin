<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PostComplianceStat } from '#/api/compliance';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElMessage, ElStatistic, ElUpload } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getPostStats, getUploadTemplate, uploadComplianceData } from '#/api/compliance';

import { useOverviewColumns, useOverviewSearchFormSchema } from './data';

const router = useRouter();

const summary = ref({
  total_risks: 0,
  unresolved_risks: 0,
  total_branch_risks: 0,
  unresolved_branch_risks: 0,
  affected_users: 0,
});

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useOverviewSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useOverviewColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: false },
    proxyConfig: {
      ajax: {
        query: async (_, formValues) => {
          const data = await getPostStats();

          summary.value = {
            total_risks: data.total_risks,
            unresolved_risks: data.unresolved_risks,
            total_branch_risks: data.total_branch_risks,
            unresolved_branch_risks: data.unresolved_branch_risks,
            affected_users: data.affected_users,
          };

          let items = data.items;
          if (formValues.post_name) {
            items = items.filter((item) =>
              item.post_name.includes(formValues.post_name),
            );
          }
          return items;
        },
      },
    },
    toolbarConfig: {
      refresh: { code: 'query' },
      search: true,
      zoom: true,
      slots: { buttons: 'toolbar_buttons' },
    },
  } as VxeTableGridOptions<PostComplianceStat>,
});

const handleViewDetail = (row: PostComplianceStat) => {
  router.push({
    path: '/compliance/detail',
    query: { postId: row.post_id, postName: row.post_name },
  });
};

const handleUploadSuccess = (msg?: string) => {
  ElMessage.success(msg || '上传成功');
  gridApi.query();
};

const handleUploadError = (msg?: string) => {
  ElMessage.error(msg || '上传失败');
};

const beforeUpload = async (file: File) => {
  try {
    const res = await uploadComplianceData(file);
    if (res.code === 200) {
      handleUploadSuccess(res.msg);
    } else {
      handleUploadError(res.msg);
    }
  } catch (e: any) {
    handleUploadError(e?.response?.data?.msg || e?.message);
  }
  return false;
};

const downloadTemplate = async () => {
  try {
    const blob = await getUploadTemplate();
    const url = window.URL.createObjectURL(new Blob([blob as any]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'compliance_template.xlsx');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e) {
    ElMessage.error('下载模板失败');
  }
};
</script>

<template>
  <Page title="合规风险概览" auto-content-height>
    <div class="flex h-full flex-col gap-4">
      <div class="grid shrink-0 grid-cols-5 gap-4">
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="Change总数" :value="summary.total_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理Change"
            :value="summary.unresolved_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="分支风险总数" :value="summary.total_branch_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理分支风险"
            :value="summary.unresolved_branch_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="涉及用户" :value="summary.affected_users" />
        </ElCard>
      </div>

      <div class="min-h-0 flex-1 overflow-hidden">
        <Grid>
          <template #toolbar_buttons>
            <div class="flex gap-2">
              <ElButton @click="downloadTemplate">下载模板</ElButton>
              <ElUpload
                action="#"
                :show-file-list="false"
                :before-upload="beforeUpload"
                accept=".xlsx,.csv"
              >
                <ElButton type="primary">批量上传</ElButton>
              </ElUpload>
            </div>
          </template>

          <template #unresolved="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_count > 0 }"
            >
              {{ row.unresolved_count }}
            </span>
          </template>
          
          <template #unresolved_branch="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_branch_count > 0 }"
            >
              {{ row.unresolved_branch_count }}
            </span>
          </template>

          <template #action="{ row }">
            <ElButton type="primary" link @click="handleViewDetail(row)">
              查看详情
            </ElButton>
          </template>
        </Grid>
      </div>
    </div>
  </Page>
</template>
