<script lang="ts" setup>
import type { User } from '#/api/core';

import { ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';
import { $t } from '@vben/locales';

import { ElButton, ElMessage, ElMessageBox, ElTag } from 'element-plus';

import {
  batchDeleteUserApi,
  deleteUserApi,
  getUserListApi,
  resetUserPasswordApi,
} from '#/api/core';
import { UserAvatar } from '#/components/user-avatar';
import { useZqTable } from '#/components/zq-table';

import {
  getGenderOptions,
  getLoginTypeOptions,
  getStatusOptions,
  getUserTypeOptions,
  useColumns,
  useSearchFormSchema,
} from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'SystemUser' });

const ADMIN_USER_ID = 'a0000000-0000-0000-0000-000000000001';
type TagType = 'danger' | 'info' | 'primary' | 'success' | 'warning';

interface UserQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const selectedRows = ref<User[]>([]);

/**
 * 编辑用户
 */
function onEdit(row: User) {
  formDrawerApi.setData(row).open();
}

/**
 * 创建新用户
 */
function onCreate() {
  formDrawerApi.setData({}).open();
}

/**
 * 删除单个用户
 */
function onDelete(row: User) {
  if (row.id === ADMIN_USER_ID) {
    ElMessage.warning($t('user.cannotDeleteAdmin'));
    return;
  }

  ElMessageBox.confirm(
    $t('ui.actionMessage.deleteConfirm', [row.name]),
    $t('common.delete'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
    },
  )
    .then(async () => {
      try {
        await deleteUserApi(row.id);
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
 * 批量删除用户
 */
function onBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning($t('user.selectUsersToDelete'));
    return;
  }

  // 检查是否包含管理员账户
  const hasAdmin = selectedRows.value.some((row) => row.id === ADMIN_USER_ID);
  if (hasAdmin) {
    ElMessage.warning($t('user.cannotDeleteAdmin'));
    return;
  }

  // 确认删除
  const names = selectedRows.value.map((row: User) => row.name).join('、');
  const confirmMessage = $t('user.batchDeleteConfirm', [
    selectedRows.value.length,
    names,
  ]);

  ElMessageBox.confirm(confirmMessage, $t('user.batchDeleteTitle'), {
    confirmButtonText: $t('common.confirm'),
    cancelButtonText: $t('common.cancel'),
    type: 'warning',
  })
    .then(async () => {
      try {
        const ids = selectedRows.value.map((row: User) => row.id);
        await batchDeleteUserApi({ ids });
        ElMessage.success(
          $t('user.deleteSuccess', [selectedRows.value.length]),
        );
        selectedRows.value = [];
        refreshGrid();
      } catch {
        ElMessage.error($t('user.deleteError'));
      }
    })
    .catch(() => {
      // 用户取消了操作
    });
}

/**
 * 重置密码
 */
function onResetPassword(row: User) {
  if (row.id === ADMIN_USER_ID) {
    ElMessage.warning($t('user.cannotResetAdminPassword'));
    return;
  }

  ElMessageBox.confirm(
    $t('user.resetPasswordConfirm', [row.name]),
    $t('user.resetPasswordTitle'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
    },
  )
    .then(async () => {
      try {
        await resetUserPasswordApi(row.id, {
          new_password: 'admin123',
          confirm_password: 'admin123',
        });
        ElMessage.success($t('user.resetPasswordSuccess', [row.name]));
      } catch {
        ElMessage.error($t('user.resetPasswordError'));
      }
    })
    .catch(() => {
      // 用户取消了操作
    });
}

function getOption(
  options: Array<{ label: string; type?: string; value: number | string }>,
  value?: number | string,
) {
  return options.find((item) => item.value === value);
}

function getTagType(type?: string): TagType {
  if (
    type === 'primary' ||
    type === 'success' ||
    type === 'warning' ||
    type === 'danger'
  ) {
    return type;
  }
  return 'info';
}

function onSelectionChange(rows: User[]) {
  selectedRows.value = rows.filter((row) => row.id !== ADMIN_USER_ID);
}

const [Grid, gridApi] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    border: true,
    columns: useColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: UserQueryParams) => {
          const formValues = { ...form };
          const plGroupIds = formValues.pl_group_ids;
          delete formValues.pl_group_ids;
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
            ...(Array.isArray(plGroupIds) && plGroupIds.length > 0
              ? { 'pl_group_ids[]': plGroupIds }
              : {}),
          } as any;
          return await getUserListApi(params);
        },
      },
    },
    stripe: true,
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: true,
      search: true,
      zoom: true,
    },
  },
});

/**
 * 刷新表格
 */
function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="refreshGrid" />

    <Grid class="h-full" @selection-change="onSelectionChange">
      <template #toolbar-actions>
        <ElButton type="primary" @click="onCreate">
          <Plus class="size-5" />
          {{ $t('ui.actionTitle.create', [$t('user.name')]) }}
        </ElButton>
        <ElButton type="danger" plain @click="onBatchDelete">
          {{ $t('user.batchDelete') }}
          {{ selectedRows.length > 0 ? `(${selectedRows.length})` : '' }}
        </ElButton>
      </template>

      <template #avatar="{ row }">
        <div class="flex items-center justify-center">
          <UserAvatar
            :user="row as any"
            :size="34"
            :font-size="16"
            :shadow="false"
          />
        </div>
      </template>

      <template #cell-pl_group_names="{ row }">
        <div class="flex flex-wrap items-center gap-1">
          <ElTag
            v-for="group in row.pl_groups || []"
            :key="group.id"
            size="small"
            :type="group.status ? 'success' : 'info'"
          >
            {{ group.name }}
          </ElTag>
          <span v-if="!row.pl_groups?.length" class="text-muted-foreground">
            -
          </span>
        </div>
      </template>

      <template #cell-user_type="{ row }">
        <ElTag
          size="small"
          :type="
            getTagType(getOption(getUserTypeOptions(), row.user_type)?.type)
          "
        >
          {{ getOption(getUserTypeOptions(), row.user_type)?.label || '-' }}
        </ElTag>
      </template>

      <template #cell-gender="{ row }">
        <ElTag size="small" type="info">
          {{ getOption(getGenderOptions(), row.gender)?.label || '-' }}
        </ElTag>
      </template>

      <template #cell-user_status="{ row }">
        <ElTag
          size="small"
          :type="
            getTagType(getOption(getStatusOptions(), row.user_status)?.type)
          "
        >
          {{ getOption(getStatusOptions(), row.user_status)?.label || '-' }}
        </ElTag>
      </template>

      <template #cell-last_login_type="{ row }">
        <ElTag
          size="small"
          :type="
            getTagType(
              getOption(getLoginTypeOptions(), row.last_login_type)?.type,
            )
          "
        >
          {{
            getOption(getLoginTypeOptions(), row.last_login_type)?.label || '-'
          }}
        </ElTag>
      </template>

      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-2">
          <ElButton link type="primary" @click="onResetPassword(row)">
            {{ $t('user.resetPassword') }}
          </ElButton>
          <ElButton link type="primary" @click="onEdit(row)">
            {{ $t('common.edit') }}
          </ElButton>
          <ElButton
            link
            type="danger"
            :disabled="row.id === ADMIN_USER_ID"
            @click="onDelete(row)"
          >
            {{ $t('common.delete') }}
          </ElButton>
        </div>
      </template>
    </Grid>
  </Page>
</template>
