<script lang="ts" setup>
import type { ProjectOut } from '#/api/project-manager/project';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElButton, ElMessage, ElTag, ElTooltip } from 'element-plus';

import {
  deleteProjectApi,
  favoriteProjectApi,
  listProjectsApi,
  unfavoriteProjectApi,
} from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

import QGConfigDialog from '../milestone/components/QGConfigDialog.vue';
import { useSearchFormSchema, useZqColumns } from './data';
import Form from './modules/form.vue';
import NewProjectDialog from './modules/NewProjectDialog.vue';

defineOptions({ name: 'ProjectList' });
interface ProjectQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const router = useRouter();

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const createDialogVisible = ref(false);
const configDialogVisible = ref(false);
const currentProjectId = ref('');
const currentProjectName = ref('');

function getBooleanLabel(
  value: boolean,
  trueLabel = '开启',
  falseLabel = '关闭',
) {
  return value ? trueLabel : falseLabel;
}

function getBooleanTagType(value: boolean) {
  return value ? 'success' : 'danger';
}

async function onActionClick(code: string, row: ProjectOut) {
  try {
    if (code === 'edit') {
      formDrawerApi.setData(row).open();
      return;
    }
    if (code === 'delete') {
      await deleteProjectApi(row.id);
      ElMessage.success('删除成功');
      refreshGrid();
      return;
    }
    if (code === 'favorite') {
      if (row.is_favorited) {
        await unfavoriteProjectApi(row.id);
        ElMessage.success('已取消收藏');
      } else {
        await favoriteProjectApi(row.id);
        ElMessage.success('收藏成功');
      }
      refreshGrid();
      return;
    }
    if (code === 'report') {
      router.push(`/project-manager/report/${row.id}`);
      return;
    }
    if (code === 'qg_config') {
      currentProjectId.value = row.id;
      currentProjectName.value = row.name;
      configDialogVisible.value = true;
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('操作失败，请稍后重试');
  }
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: useZqColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ProjectQueryParams) => {
          return await listProjectsApi({
            page: page.currentPage,
            pageSize: page.pageSize,
            ...form,
          });
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  },
  formOptions: {
    schema: useSearchFormSchema(),
    showCollapseButton: false,
    submitOnChange: true,
  },
});

function refreshGrid() {
  gridApi.reload();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="refreshGrid" />

    <div class="flex h-full min-h-0 flex-col">
      <div class="min-h-0 flex-1">
        <Grid class="h-full">
          <template #toolbar-actions>
            <ElButton type="primary" @click="createDialogVisible = true">
              新增项目
            </ElButton>
          </template>

          <template #cell-managers_info="{ row }">
            {{
              (row.managers_info || []).map((item: any) => item.name).join('、')
            }}
          </template>

          <template #cell-is_closed="{ row }">
            <ElTag :type="row.is_closed ? 'info' : 'success'" size="small">
              {{ row.is_closed ? '关闭' : '开启' }}
            </ElTag>
          </template>

          <template #cell-enable_milestone="{ row }">
            <ElTag :type="getBooleanTagType(row.enable_milestone)" size="small">
              {{ getBooleanLabel(row.enable_milestone) }}
            </ElTag>
          </template>

          <template #cell-enable_iteration="{ row }">
            <ElTag :type="getBooleanTagType(row.enable_iteration)" size="small">
              {{ getBooleanLabel(row.enable_iteration) }}
            </ElTag>
          </template>

          <template #cell-enable_quality="{ row }">
            <ElTag :type="getBooleanTagType(row.enable_quality)" size="small">
              {{ getBooleanLabel(row.enable_quality) }}
            </ElTag>
          </template>

          <template #cell-enable_hardware_config="{ row }">
            <ElTag
              :type="getBooleanTagType(row.enable_hardware_config)"
              size="small"
            >
              {{ getBooleanLabel(row.enable_hardware_config) }}
            </ElTag>
          </template>

          <template #cell-actions="{ row }">
            <div
              class="flex flex-nowrap items-center justify-center gap-1 whitespace-nowrap"
            >
              <ElTooltip content="编辑" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="primary"
                  @click="onActionClick('edit', row)"
                >
                  <IconifyIcon icon="ep:edit" />
                </ElButton>
              </ElTooltip>
              <ElTooltip
                :content="row.is_favorited ? '取消收藏' : '收藏'"
                placement="top"
              >
                <ElButton
                  circle
                  link
                  size="small"
                  :type="row.is_favorited ? 'warning' : 'info'"
                  @click="onActionClick('favorite', row)"
                >
                  <IconifyIcon
                    :icon="row.is_favorited ? 'ep:star-filled' : 'ep:star'"
                  />
                </ElButton>
              </ElTooltip>
              <ElTooltip content="查看详细报告" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="primary"
                  @click="onActionClick('report', row)"
                >
                  <IconifyIcon icon="lucide:file-bar-chart-2" />
                </ElButton>
              </ElTooltip>
              <ElTooltip content="QG预警配置" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="info"
                  @click="onActionClick('qg_config', row)"
                >
                  <IconifyIcon icon="lucide:settings" />
                </ElButton>
              </ElTooltip>
              <ElTooltip content="删除" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="danger"
                  @click="onActionClick('delete', row)"
                >
                  <IconifyIcon icon="ep:delete" />
                </ElButton>
              </ElTooltip>
            </div>
          </template>
        </Grid>
      </div>
    </div>

    <NewProjectDialog v-model="createDialogVisible" @created="refreshGrid" />

    <QGConfigDialog
      v-model="configDialogVisible"
      :project-id="currentProjectId"
      :project-name="currentProjectName"
    />
  </Page>
</template>
