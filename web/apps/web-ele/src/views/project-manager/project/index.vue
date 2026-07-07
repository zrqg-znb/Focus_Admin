<script lang="ts" setup>
import type {
  ProjectOut,
  ProjectVehicleLinkItem,
} from '#/api/project-manager/project';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip,
} from 'element-plus';

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
const vehicleLinkDialogVisible = ref(false);
const vehicleLinkDialogTitle = ref('');
const vehicleLinkDialogRows = ref<ProjectVehicleLinkItem[]>([]);

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

function normalizeVehicleLinks(value: unknown) {
  if (!value) return [];
  if (typeof value === 'string') {
    const url = value.trim();
    return url ? [{ chip_name: '', url }] : [];
  }
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === 'string') {
        return { chip_name: '', url: item.trim() };
      }
      if (!item || typeof item !== 'object') {
        return { chip_name: '', url: '' };
      }
      return {
        chip_name: String(item.chip_name || '').trim(),
        url: String(item.url || '').trim(),
      };
    })
    .filter((item) => item.url);
}

function normalizeExternalUrl(url: string) {
  const text = String(url || '').trim();
  if (!text) return '';
  return /^https?:\/\//i.test(text) ? text : `https://${text}`;
}

function openVehicleLinkDialog(title: string, value: unknown) {
  const rows = normalizeVehicleLinks(value);
  if (rows.length === 0) return;
  vehicleLinkDialogTitle.value = title;
  vehicleLinkDialogRows.value = rows;
  vehicleLinkDialogVisible.value = true;
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

          <template #cell-power_info_link="{ row }">
            <ElButton
              v-if="normalizeVehicleLinks(row.power_info_link).length > 0"
              link
              size="small"
              type="primary"
              @click="
                openVehicleLinkDialog('用电信息表链接', row.power_info_link)
              "
            >
              已配置 {{ normalizeVehicleLinks(row.power_info_link).length }} 条
            </ElButton>
            <ElTag v-else size="small" type="info">未配置</ElTag>
          </template>

          <template #cell-hardware_software_interface_doc="{ row }">
            <ElButton
              v-if="
                normalizeVehicleLinks(row.hardware_software_interface_doc)
                  .length > 0
              "
              link
              size="small"
              type="primary"
              @click="
                openVehicleLinkDialog(
                  '软硬件接口文档',
                  row.hardware_software_interface_doc,
                )
              "
            >
              已配置
              {{
                normalizeVehicleLinks(row.hardware_software_interface_doc)
                  .length
              }}
              条
            </ElButton>
            <ElTag v-else size="small" type="info">未配置</ElTag>
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

    <ElDialog
      v-model="vehicleLinkDialogVisible"
      :title="vehicleLinkDialogTitle"
      width="720px"
      append-to-body
    >
      <!-- 当前行字段明细展示，数据量小且不分页，按 zq-table 例外使用 Element Plus 表格。 -->
      <ElTable
        v-if="vehicleLinkDialogRows.length > 0"
        :data="vehicleLinkDialogRows"
        border
        stripe
      >
        <ElTableColumn label="芯片配置名" min-width="180" prop="chip_name">
          <template #default="{ row }">
            {{ row.chip_name || '未填写' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="URL" min-width="360" prop="url">
          <template #default="{ row }">
            <a
              class="text-primary break-all hover:underline"
              :href="normalizeExternalUrl(row.url)"
              rel="noopener noreferrer"
              target="_blank"
            >
              {{ row.url }}
            </a>
          </template>
        </ElTableColumn>
      </ElTable>
      <ElEmpty v-else description="暂无配置" />
    </ElDialog>
  </Page>
</template>
