<script lang="ts" setup>
import type { Recordable } from '@vben/types';

import type { VbenFormSchema } from '#/adapter/form';
import type { Menu } from '#/api/core/menu';

import { computed, h, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';
import { getPopupContainer } from '@vben/utils';

import { ElMessage } from 'element-plus';

import { useVbenForm, z } from '#/adapter/form';
import {
  checkMenuNameApi,
  checkMenuPathApi,
  createMenuApi,
  getAllMenuTreeApi,
} from '#/api/core/menu';

const emit = defineEmits<{
  success: [menuData?: any];
}>();

const formData = ref<Partial<Menu>>();

/**
 * 处理菜单数据，添加 name 字段用于显示
 */
function processMenuData(menus: any[]): any[] {
  return menus.map((menu) => ({
    ...menu,
    name: menu.meta?.title ? $t(menu.meta.title) : menu.name,
    children: menu.children ? processMenuData(menu.children) : undefined,
  }));
}

/**
 * 包装 API 调用，处理返回的数据
 */
async function getMenuListProcessed() {
  const data = await getAllMenuTreeApi();
  return processMenuData(data);
}

/**
 * 检查菜单名称是否存在
 */
async function isMenuNameExists(name: string) {
  const result = await checkMenuNameApi(name);
  return result.exists;
}

/**
 * 检查菜单路径是否存在
 */
async function isMenuPathExists(path: string) {
  const result = await checkMenuPathApi(path);
  return result.exists;
}

const schema = computed((): VbenFormSchema[] => [
  {
    component: 'ApiTreeSelect',
    componentProps: {
      api: getMenuListProcessed,
      checkStrictly: true,
      class: 'w-full',
      filterTreeNode(input: string, node: Recordable<any>) {
        if (!input || input.length === 0) {
          return true;
        }
        const name: string = node.name ?? '';
        return name.toLowerCase().includes(input.toLowerCase());
      },
      getPopupContainer,
      labelField: 'name', // 使用处理后的 name 字段作为标签
      showSearch: true,
      valueField: 'id',
      childrenField: 'children',
    },
    fieldName: 'parent_id',
    label: $t('menu.parent'),
    renderComponentContent() {
      return {
        title({ label, meta }: { label: string; meta: Recordable<any> }) {
          const coms = [];
          if (!label) return '';
          if (meta?.icon) {
            coms.push(h(IconifyIcon, { class: 'size-4', icon: meta.icon }));
          }
          coms.push(h('span', { class: '' }, label));
          return h('div', { class: 'flex items-center gap-1' }, coms);
        },
      };
    },
  },
  {
    component: 'Input',
    fieldName: 'name',
    label: $t('menu.menuName'),
    rules: z
      .string()
      .min(2, $t('ui.formRules.minLength', [$t('menu.menuName'), 2]))
      .max(30, $t('ui.formRules.maxLength', [$t('menu.menuName'), 30]))
      .refine(
        async (value: string) => {
          return !(await isMenuNameExists(value));
        },
        (value) => ({
          message: $t('ui.formRules.alreadyExists', [
            $t('menu.menuName'),
            value,
          ]),
        }),
      ),
  },
  {
    component: 'Input',
    fieldName: 'path',
    label: $t('menu.path'),
    rules: z
      .string()
      .min(2, $t('ui.formRules.minLength', [$t('menu.path'), 2]))
      .max(100, $t('ui.formRules.maxLength', [$t('menu.path'), 100]))
      .refine(
        (value: string) => {
          return value.startsWith('/');
        },
        $t('ui.formRules.startWith', [$t('menu.path'), '/']),
      )
      .refine(
        async (value: string) => {
          return !(await isMenuPathExists(value));
        },
        (value) => ({
          message: $t('ui.formRules.alreadyExists', [$t('menu.path'), value]),
        }),
      ),
  },
]);

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: schema.value,
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  onConfirm: onSubmit,
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<Partial<Menu>>();
      if (data) {
        formData.value = data;
        formApi.setValues(formData.value);
      } else {
        formApi.resetForm();
      }
    }
  },
});

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    modalApi.lock();
    try {
      const data = await formApi.getValues<Partial<Menu>>();
      const menuData = {
        name: data.name!,
        type: data.type || 'catalog',
        path: data.path!,
        parent_id: data.parent_id,
        order: 0,
      };

      // 创建菜单并获取返回的数据
      const result = await createMenuApi(menuData);
      ElMessage.success($t('ui.actionMessage.createSuccess'));
      modalApi.close();

      // 传递新创建的菜单数据（包括 id 和 parent_id）
      emit('success', result);
    } catch {
      ElMessage.error($t('ui.actionMessage.createError'));
    } finally {
      modalApi.unlock();
    }
  }
}

const getModalTitle = computed(() =>
  $t('ui.actionTitle.create', [$t('menu.name')]),
);
</script>

<template>
  <Modal class="w-full max-w-[500px]" :title="getModalTitle">
    <Form class="mx-4" />
  </Modal>
</template>
