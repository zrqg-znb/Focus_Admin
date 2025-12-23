<script lang="ts" setup>
import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import {
  batchCreatePermissionsFromRoutesApi,
  getAllRoutesApi,
} from '#/api/core/permission';

import RouteSelector from './route-selector.vue';

interface RouteItem {
  path: string;
  method: string;
  operation_id: string;
  summary: string;
  // 编辑字段
  name?: string;
  code?: string;
  permission_type?: number;
  http_method?: number;
  is_active?: boolean;
  selected?: boolean;
}

const emit = defineEmits<{
  success: [];
}>();

const loading = ref(false);
const allRoutes = ref<RouteItem[]>([]);
const currentMenuId = ref<string>('');
const currentMenuName = ref<string>('');
const routeSelectorRef = ref<InstanceType<typeof RouteSelector>>();

// HTTP 方法映射
const methodMap: Record<string, { code: number; name: string }> = {
  GET: { name: 'read', code: 0 },
  POST: { name: 'create', code: 1 },
  PUT: { name: 'update', code: 2 },
  DELETE: { name: 'delete', code: 3 },
  PATCH: { name: 'part_update', code: 4 },
};

// 提交
async function onSubmit() {
  if (!currentMenuId.value) {
    ElMessage.warning('请先选择菜单');
    return;
  }

  // 检查重复
  const checkResult = routeSelectorRef.value?.checkDuplicates();
  if (checkResult?.hasError) {
    ElMessage.error(checkResult.message);
    return;
  }

  const selectedRoutes = allRoutes.value.filter((r) => r.selected);
  if (selectedRoutes.length === 0) {
    ElMessage.warning('请选择至少一个路由');
    return;
  }

  modalApi.lock();

  try {
    const result = await batchCreatePermissionsFromRoutesApi({
      menu_id: currentMenuId.value,
      routes: selectedRoutes.map((route) => ({
        path: route.path,
        method: route.method,
        name: route.name,
        code: route.code,
        summary: route.summary,
        permission_type: route.permission_type,
        http_method: route.http_method,
        is_active: route.is_active,
      })),
    });

    ElMessage.success(
      `成功创建 ${result.created} 个权限${result.skipped > 0 ? `，跳过 ${result.skipped} 个` : ''}`,
    );

    if (result.failed > 0) {
      ElMessage.warning(
        `${result.failed} 个权限创建失败：${result.errors.join('; ')}`,
      );
    }

    modalApi.close();
    emit('success');
  } catch {
    ElMessage.error('创建权限失败');
  } finally {
    modalApi.lock(false);
  }
}

// 初始化路由数据
async function initRoutes() {
  loading.value = true;
  try {
    const routes = await getAllRoutesApi();
    allRoutes.value = routes.map((route) => {
      const methodInfo = methodMap[route.method] || {
        name: route.method,
        code: 0,
      };
      return {
        ...route,
        name: `${route.summary || route.operation_id}`,
        code: `${route.path.split('/')[3]}:${methodInfo.name.toLowerCase()}`,
        permission_type: 1,
        http_method: methodInfo.code,
        is_active: true,
        selected: false,
      };
    });
  } catch {
    ElMessage.error('获取路由列表失败');
  } finally {
    loading.value = false;
  }
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    await onSubmit();
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<{ menuId: string; menuName: string }>();
      if (data) {
        currentMenuId.value = data.menuId;
        currentMenuName.value = data.menuName;
        allRoutes.value = [];
        initRoutes();
      }
    }
  },
});
</script>

<template>
  <Modal title="自动生成API权限" fullscreen>
    <div class="auto-generate-container">
      <!-- 路由选择器 -->
      <RouteSelector
        ref="routeSelectorRef"
        :routes="allRoutes"
        :loading="loading"
        @update:routes="(routes) => (allRoutes = routes)"
      />
    </div>

    <template #prepend-footer>
      <div class="flex-auto"></div>
    </template>
  </Modal>
</template>

<style scoped lang="scss">
.auto-generate-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
