<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { Permission } from '#/api/core/permission';

import { reactive, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  batchDeletePermissionApi,
  deletePermissionApi,
  getPermissionListApi,
} from '#/api/core/permission';

import { getSearchFormSchema } from '../data';
import AutoGenerateModal from './auto-generate-modal.vue';

interface Props {
  menuId?: string;
  menuName?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  add: [permission?: Permission];
}>();

const selectedRows = ref<Permission[]>([]);
const searchInfo = reactive<{ menu_id?: string }>({});
const currentMenuId = ref<string>();

// 监听 props 变化，更新当前菜单 ID
watch(
  () => props.menuId,
  (newMenuId) => {
    currentMenuId.value = newMenuId;
  },
);

// 初始化自动生成权限 Modal
const [AutoGenerateModalComponent, autoGenerateModalApi] = useVbenModal({
  connectedComponent: AutoGenerateModal,
  destroyOnClose: true,
});

/**
 * 编辑权限
 */
function onEdit(row: Permission) {
  emit('add', row);
}

/**
 * 删除单个权限
 */
function onDelete(row: Permission) {
  ElMessageBox.confirm(
    $t('permission.deleteConfirm', [row.name]),
    $t('common.tips'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
      showClose: false,
    },
  )
    .then(async () => {
      try {
        await deletePermissionApi(row.id);
        ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
        refreshGrid();
      } catch {
        ElMessage.error($t('ui.actionMessage.deleteError'));
      }
    })
    .catch(() => {
      // 用户取消了操作
    });
}

/**
 * 批量删除权限
 */
function onBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning($t('permission.selectToDelete'));
    return;
  }

  const names = selectedRows.value
    .map((row: Permission) => row.name)
    .join('、');

  ElMessageBox.confirm(
    $t('permission.batchDeleteConfirm', [selectedRows.value.length, names]),
    $t('common.tips'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
      showClose: false,
    },
  )
    .then(async () => {
      try {
        const ids = selectedRows.value.map((row: Permission) => row.id);
        await batchDeletePermissionApi({ ids });
        ElMessage.success(
          $t('permission.batchDeleteSuccess', [selectedRows.value.length]),
        );
        selectedRows.value = [];
        refreshGrid();
      } catch {
        ElMessage.error($t('permission.batchDeleteFailed'));
      }
    })
    .catch(() => {
      // 用户取消了操作
    });
}

/**
 * 表格操作按钮的回调函数
 */
function onActionClick({ code, row }: OnActionClickParams<Permission>) {
  switch (code) {
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
  }
}

/**
 * 菜单选择事件
 */
function onMenuSelect(menuId: string | undefined) {
  currentMenuId.value = menuId;
  searchInfo.menu_id = menuId;
  selectedRows.value = [];
  refreshGrid();
}

/**
 * 打开自动生成权限 Modal
 */
function onAutoScan() {
  if (!currentMenuId.value) {
    ElMessage.warning('请先选择菜单');
    return;
  }

  autoGenerateModalApi
    .setData({
      menuId: currentMenuId.value,
      menuName: props.menuName,
    })
    .open();
}

/**
 * 权限生成成功回调
 */
function onAutoGenerateSuccess() {
  refreshGrid();
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: getSearchFormSchema(),
    submitOnChange: true,
  },
  gridEvents: {
    checkboxAll: ({ records }: { records: Permission[] }) => {
      selectedRows.value = records;
    },
    checkboxChange: ({ records }: { records: Permission[] }) => {
      selectedRows.value = records;
    },
  },
  gridOptions: {
    align: 'left',
    columns: [
      {
        type: 'checkbox',
        minWidth: 60,
        align: 'center',
        fixed: 'left',
      },
      {
        field: 'name',
        title: $t('permission.permissionName'),
        minWidth: 150,
      },
      {
        field: 'code',
        title: $t('permission.permissionCode'),
        minWidth: 180,
      },
      {
        field: 'permission_type',
        title: $t('permission.permissionType'),
        minWidth: 80,
        formatter: (params) => {
          const typeMap: Record<number, string> = {
            0: $t('permission.typeLabels.button'),
            1: $t('permission.typeLabels.api'),
            2: $t('permission.typeLabels.data'),
            3: $t('permission.typeLabels.other'),
          };
          return (
            typeMap[params.row.permission_type] ||
            $t('permission.typeLabels.unknown')
          );
        },
      },
      {
        field: 'http_method',
        title: $t('permission.httpMethod'),
        minWidth: 80,
        formatter: (params) => {
          if (params.row.permission_type !== 1) return '';
          const methodMap: Record<number, string> = {
            0: 'GET',
            1: 'POST',
            2: 'PUT',
            3: 'DELETE',
            4: 'PATCH',
            5: 'ALL',
          };
          const method = params.row.http_method as number | undefined;
          return method === undefined
            ? 'UNKNOWN'
            : methodMap[method] || 'UNKNOWN';
        },
      },
      {
        field: 'api_path',
        title: $t('permission.apiPath'),
        minWidth: 220,
      },
      {
        field: 'description',
        title: $t('permission.description'),
        minWidth: 150,
      },
      {
        align: 'right',
        cellRender: {
          attrs: {
            nameField: 'name',
            nameTitle: $t('permission.permissionName'),
            onClick: onActionClick,
          },
          name: 'CellOperation',
          options: ['edit', 'delete'],
        },
        field: 'operation',
        fixed: 'right',
        headerAlign: 'center',
        showOverflow: false,
        title: $t('permission.operation'),
        minWidth: 150,
      },
    ],
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          if (!currentMenuId.value) {
            return { items: [], total: 0 };
          }
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            menu_id: currentMenuId.value,
            ...formValues,
          };
          return await getPermissionListApi(params);
        },
      },
    },
    checkboxConfig: {
      reserve: true,
      trigger: 'default',
    },
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<Permission>,
});

/**
 * 刷新表格
 */
function refreshGrid() {
  gridApi.query();
}
watch(
  () => props.menuId,
  (newMenuId) => {
    if (newMenuId) {
      onMenuSelect(newMenuId);
    }
  },
);

// 暴露公共方法
defineExpose({
  loadPermissions: refreshGrid,
});
</script>

<template>
  <Grid>
    <template #table-title>
      <ElButton type="primary" @click="emit('add')">
        + {{ $t('permission.add') }}
      </ElButton>
      <ElButton type="success" @click="onAutoScan"> 快速添加API权限 </ElButton>
      <ElButton type="danger" plain @click="onBatchDelete">
        {{ $t('permission.batchDelete') }}
        {{ selectedRows.length > 0 ? `(${selectedRows.length})` : '' }}
      </ElButton>
    </template>
  </Grid>

  <!-- 自动生成权限 Modal -->
  <AutoGenerateModalComponent @success="onAutoGenerateSuccess" />
</template>
