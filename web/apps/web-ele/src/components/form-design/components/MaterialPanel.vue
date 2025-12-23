<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  ArrowDown,
  ArrowRight,
  Avatar,
  Calendar,
  CaretBottom,
  Check,
  CircleCheck,
  Clock,
  Connection,
  Document,
  Edit,
  Files,
  Folder,
  Grid,
  List,
  MagicStick,
  Minus,
  More,
  Odometer,
  OfficeBuilding,
  Open,
  Operation,
  Paperclip,
  Picture,
  Star,
  Suitcase,
  User,
  Warning,
  Watch,
} from '@element-plus/icons-vue';
import { ElIcon, ElMessageBox, ElScrollbar, ElTabPane, ElTabs, ElTree } from 'element-plus';
import { storeToRefs } from 'pinia';
import draggable from 'vuedraggable';

import { useFormDesignStore } from '../store/formDesignStore';

const store = useFormDesignStore();
const { formConf, templates } = storeToRefs(store);
// 直接使用 store 中的 cloneComponent 方法
const cloneComponent = store.cloneComponent;

const getTemplateIcon = (iconName: any | string) => {
  if (typeof iconName !== 'string') return iconName;
  const map: any = { User, Edit, Document };
  return map[iconName] || Document;
};

const onDragStart = () => store.setDragging(true);
const onDragEnd = () => store.setDragging(false);

const activeTab = ref('library');
const activeGroups = ref(['basic', 'advanced', 'layout']);

const getAllComponents = () => [
  ...basicComponents,
  ...advancedComponents,
  ...layoutComponents,
];

const transformToTree = (items: any[]) => {
  return items.map((item) => {
    const compDef = getAllComponents().find((c) => c.type === item.type);
    const node: any = {
      id: item.id,
      label: item.label || (compDef ? compDef.label : item.type),
      icon: compDef ? compDef.icon : null,
      children: [],
    };

    if (item.columns) {
      item.columns.forEach((col: any, index: number) => {
        node.children.push({
          id: `${item.id}_col_${index}`,
          label: `栅格 ${index + 1}`,
          children: transformToTree(col.children || []),
          isVirtual: true,
          parentId: item.id,
        });
      });
    } else if (item.items) {
      // Collapse / Tabs
      item.items.forEach((subItem: any, index: number) => {
        node.children.push({
          id: `${item.id}_item_${index}`,
          label:
            subItem.title ||
            subItem.label ||
            subItem.name ||
            `面板 ${index + 1}`,
          children: transformToTree(subItem.children || []),
          isVirtual: true,
          parentId: item.id,
        });
      });
    } else if (item.children) {
      // SubTable
      node.children = transformToTree(item.children);
    }

    return node;
  });
};

const outlineData = computed(() => transformToTree(formConf.value.items));

const handleNodeClick = (data: any) => {
  if (data.isVirtual && data.parentId) {
    store.setActive(data.parentId);
  } else if (!data.isVirtual) {
    store.setActive(data.id);
  }
};

const toggleGroup = (group: string) => {
  const index = activeGroups.value.indexOf(group);
  if (index === -1) {
    activeGroups.value.push(group);
  } else {
    activeGroups.value.splice(index, 1);
  }
};

const applyTemplate = (tpl: any) => {
  ElMessageBox.confirm('应用模板将覆盖当前画布内容，是否继续？', '提示', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).then(() => {
    // 使用 cloneComponent 为模板项生成新的 ID
    const newItems = tpl.items.map((item: any) => store.cloneComponent(item));
    formConf.value.items = newItems;
    store.setActive(null);
  });
};

const basicComponents = [
  {
    type: 'input',
    label: '单行文本',
    icon: Edit,
    props: {
      placeholder: '请输入',
      clearable: true,
      width: '100%',
      readonly: false,
      disabled: false,
      maxlength: null,
      showWordLimit: false,
      showPassword: false,
    },
  },
  {
    type: 'textarea',
    label: '多行文本',
    icon: Document,
    props: {
      type: 'textarea',
      placeholder: '请输入',
      rows: 3,
      width: '100%',
      readonly: false,
      disabled: false,
      maxlength: null,
      showWordLimit: false,
    },
  },
  {
    type: 'select',
    label: '下拉选择',
    icon: List,
    props: {
      placeholder: '请选择',
      clearable: true,
      width: '100%',
      disabled: false,
      filterable: false,
      multiple: false,
      collapseTags: false,
    },
    options: [
      { label: '选项1', value: 1 },
      { label: '选项2', value: 2 },
    ],
  },
  {
    type: 'cascader',
    label: '级联选择',
    icon: Connection,
    props: {
      placeholder: '请选择',
      clearable: true,
      disabled: false,
      separator: '/',
      filterable: false,
      width: '100%',
    },
    options: [
      {
        label: '选项1',
        value: 1,
        children: [
          { label: '子选项1', value: 11, children: [] },
          { label: '子选项2', value: 12, children: [] },
        ],
      },
      { label: '选项2', value: 2, children: [] },
    ],
  },
  {
    type: 'tree-select',
    label: '树形选择',
    icon: Folder,
    props: {
      placeholder: '请选择',
      clearable: true,
      disabled: false,
      multiple: false,
      showCheckbox: false,
      width: '100%',
    },
    options: [
      {
        label: '选项1',
        value: 1,
        children: [
          { label: '子选项1', value: 11, children: [] },
          { label: '子选项2', value: 12, children: [] },
        ],
      },
      { label: '选项2', value: 2, children: [] },
    ],
  },
  {
    type: 'radio',
    label: '单选框',
    icon: CircleCheck,
    props: {
      disabled: false,
      border: false,
    },
    options: [
      { label: '选项1', value: 1 },
      { label: '选项2', value: 2 },
    ],
  },
  {
    type: 'checkbox',
    label: '多选框',
    icon: Check,
    props: {
      disabled: false,
      border: false,
    },
    options: [
      { label: '选项1', value: 1 },
      { label: '选项2', value: 2 },
    ],
  },
  {
    type: 'date',
    label: '日期选择',
    icon: Calendar,
    props: {
      placeholder: '选择日期',
      type: 'date',
      format: 'YYYY-MM-DD',
      valueFormat: 'YYYY-MM-DD',
      width: '100%',
      disabled: false,
      rangeSeparator: '-',
      startPlaceholder: '开始日期',
      endPlaceholder: '结束日期',
      editable: true,
    },
  },
  {
    type: 'input-number',
    label: '计数器',
    icon: Odometer,
    props: {
      min: 0,
      max: 100,
      step: 1,
      width: '100%',
      disabled: false,
      precision: 0,
      controls: true,
      controlsPosition: '', // default or right
    },
  },
  {
    type: 'time',
    label: '时间选择',
    icon: Clock,
    props: {
      placeholder: '选择时间',
      format: 'HH:mm:ss',
      valueFormat: 'HH:mm:ss',
      width: '100%',
      disabled: false,
      arrowControl: false,
    },
  },
  {
    type: 'switch',
    label: '开关',
    icon: Open,
    props: {
      activeText: '',
      inactiveText: '',
      disabled: false,
      width: 40,
      inlinePrompt: false,
    },
  },
  {
    type: 'slider',
    label: '滑块',
    icon: Operation,
    props: {
      min: 0,
      max: 100,
      step: 1,
      width: '100%',
      disabled: false,
      range: false,
      showStops: false,
      showInput: false,
    },
  },
  {
    type: 'alert',
    label: '警告提示',
    icon: Warning,
    props: {
      title: '提示标题',
      type: 'info',
      description: '',
      showIcon: true,
      closable: false,
      center: false,
    },
  },
  {
    type: 'timeline',
    label: '时间线',
    icon: More,
    props: {
      reverse: false,
    },
    items: [
      { timestamp: '2024-01-01', content: '节点1', type: 'primary', icon: '' },
      { timestamp: '2024-01-02', content: '节点2', type: 'success', icon: '' },
      { timestamp: '2024-01-03', content: '节点3', type: 'warning', icon: '' },
    ],
  },
  {
    type: 'rate',
    label: '评分',
    icon: Star,
    props: {
      max: 5,
      disabled: false,
      allowHalf: false,
      showScore: false,
    },
  },
  {
    type: 'color',
    label: '颜色选择',
    icon: MagicStick,
    props: {
      disabled: false,
      showAlpha: false,
    },
  },
];

const advancedComponents: any[] = [
  {
    type: 'dept-selector',
    label: '部门选择',
    icon: OfficeBuilding,
    props: {
      placeholder: '请选择部门',
      multiple: false,
      clearable: true,
      disabled: false,
      filterable: true,
    },
  },
  {
    type: 'user-selector',
    label: '用户选择',
    icon: User,
    props: {
      placeholder: '请选择用户',
      multiple: false,
      clearable: true,
      disabled: false,
      filterable: true,
      displayMode: 'select',
    },
  },
  {
    type: 'role-selector',
    label: '角色选择',
    icon: Avatar,
    props: {
      placeholder: '请选择角色',
      multiple: false,
      clearable: true,
      disabled: false,
      filterable: true,
    },
  },
  {
    type: 'post-selector',
    label: '岗位选择',
    icon: Suitcase,
    props: {
      placeholder: '请选择岗位',
      multiple: false,
      clearable: true,
      disabled: false,
      filterable: true,
    },
  },
  {
    type: 'cron-selector',
    label: 'Cron表达式',
    icon: Watch,
    props: {
      placeholder: 'Cron表达式',
      disabled: false,
      hideSecond: true,
      hideYear: true,
    },
  },
  {
    type: 'image-selector',
    label: '图片选择',
    icon: Picture,
    props: {
      placeholder: '请选择图片',
      multiple: false,
      disabled: false,
      clearable: true,
      maxSize: 10,
      gridColumns: 4,
      enableCrop: false,
    },
  },
  {
    type: 'file-selector',
    label: '文件选择',
    icon: Paperclip,
    props: {
      placeholder: '请选择文件',
      multiple: false,
      disabled: false,
      clearable: true,
      maxSize: 100,
      showIcon: true,
      showSize: true,
      displayMode: 'popover',
    },
  },
  {
    type: 'sub-table',
    label: '子表单',
    icon: Grid,
    children: [],
    props: {
      showIndex: true,
      summary: false,
      addable: true,
      deletable: true,
    },
  },
];

const layoutComponents = [
  {
    type: 'grid',
    label: '栅格布局',
    icon: Grid,
    columns: [
      { span: 12, children: [] },
      { span: 12, children: [] },
    ],
    props: {
      gutter: 0,
      justify: 'start',
      align: 'top',
    },
  },
  {
    type: 'divider',
    label: '分割线',
    icon: Minus,
    props: {
      contentPosition: 'center',
      borderStyle: 'solid',
      direction: 'horizontal',
    },
  },
  {
    type: 'collapse',
    label: '折叠面板',
    icon: CaretBottom,
    props: {
      accordion: false,
    },
    items: [
      { title: '面板1', name: '1', children: [] },
      { title: '面板2', name: '2', children: [] },
    ],
  },
  {
    type: 'tabs',
    label: '标签页',
    icon: Files,
    props: {
      type: '', // card, border-card
      tabPosition: 'top',
    },
    items: [
      { label: '标签1', name: '1', children: [] },
      { label: '标签2', name: '2', children: [] },
    ],
  },
];
</script>

<template>
  <div
    class="material-panel flex h-full flex-col rounded border-[var(--el-border-color)] bg-[var(--el-bg-color)]"
  >
    <ElTabs v-model="activeTab" class="flex h-full flex-col" stretch>
      <ElTabPane label="组件库" name="library" class="h-full">
        <ElScrollbar class="h-full">
          <div class="px-4 pb-4">
            <div class="component-group mb-4">
              <div
                class="group-title mb-2 flex cursor-pointer select-none items-center justify-between text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                @click="toggleGroup('basic')"
              >
                <span class="font-bold">基础组件</span>
                <ElIcon class="h-4 w-4">
                  <ArrowDown v-if="activeGroups.includes('basic')" />
                  <ArrowRight v-else />
                </ElIcon>
              </div>
              <div v-show="activeGroups.includes('basic')">
                <draggable
                  v-model="basicComponents"
                  :group="{ name: 'form-design', pull: 'clone', put: false }"
                  :sort="false"
                  :clone="cloneComponent"
                  item-key="type"
                  class="grid grid-cols-2 gap-2"
                  @start="onDragStart"
                  @end="onDragEnd"
                >
                  <template #item="{ element }">
                    <div
                      class="component-item flex cursor-move flex-col items-center justify-center rounded border border-[var(--el-border-color)] bg-[var(--el-fill-color-light)] p-2 transition-colors hover:border-[var(--el-color-primary)] hover:text-[var(--el-color-primary)]"
                    >
                      <ElIcon class="mb-1 text-lg" :size="18">
                        <component :is="element.icon" />
                      </ElIcon>
                      <span class="text-xs">{{ element.label }}</span>
                    </div>
                  </template>
                </draggable>
              </div>
            </div>

            <div class="component-group mb-4">
              <div
                class="group-title mb-2 flex cursor-pointer select-none items-center justify-between text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                @click="toggleGroup('advanced')"
              >
                <span class="font-bold">高级组件</span>
                <ElIcon class="h-4 w-4">
                  <ArrowDown v-if="activeGroups.includes('advanced')" />
                  <ArrowRight v-else />
                </ElIcon>
              </div>
              <div v-show="activeGroups.includes('advanced')">
                <div
                  v-if="advancedComponents.length === 0"
                  class="rounded bg-[var(--el-fill-color-light)] py-2 text-center text-xs text-[var(--el-text-color-placeholder)]"
                >
                  暂无组件
                </div>
                <draggable
                  v-else
                  v-model="advancedComponents"
                  :group="{ name: 'form-design', pull: 'clone', put: false }"
                  :sort="false"
                  :clone="cloneComponent"
                  item-key="type"
                  class="grid grid-cols-2 gap-2"
                  @start="onDragStart"
                  @end="onDragEnd"
                >
                  <template #item="{ element }">
                    <div
                      class="component-item flex cursor-move flex-col items-center justify-center rounded border border-[var(--el-border-color)] bg-[var(--el-fill-color-light)] p-2 transition-colors hover:border-[var(--el-color-primary)] hover:text-[var(--el-color-primary)]"
                    >
                      <ElIcon class="mb-1 text-lg" :size="18">
                        <component :is="element.icon" />
                      </ElIcon>
                      <span class="text-xs">{{ element.label }}</span>
                    </div>
                  </template>
                </draggable>
              </div>
            </div>

            <div class="component-group">
              <div
                class="group-title mb-2 flex cursor-pointer select-none items-center justify-between text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                @click="toggleGroup('layout')"
              >
                <span class="font-bold">布局组件</span>
                <ElIcon class="h-4 w-4">
                  <ArrowDown v-if="activeGroups.includes('layout')" />
                  <ArrowRight v-else />
                </ElIcon>
              </div>
              <div v-show="activeGroups.includes('layout')">
                <draggable
                  v-model="layoutComponents"
                  :group="{ name: 'form-design', pull: 'clone', put: false }"
                  :sort="false"
                  :clone="cloneComponent"
                  item-key="type"
                  class="grid grid-cols-2 gap-2"
                  @start="onDragStart"
                  @end="onDragEnd"
                >
                  <template #item="{ element }">
                    <div
                      class="component-item flex cursor-move flex-col items-center justify-center rounded border border-[var(--el-border-color)] bg-[var(--el-fill-color-light)] p-2 transition-colors hover:border-[var(--el-color-primary)] hover:text-[var(--el-color-primary)]"
                    >
                      <ElIcon class="mb-1 text-lg" :size="18">
                        <component :is="element.icon" />
                      </ElIcon>
                      <span class="text-xs">{{ element.label }}</span>
                    </div>
                  </template>
                </draggable>
              </div>
            </div>
          </div>
        </ElScrollbar>
      </ElTabPane>

      <ElTabPane label="大纲" name="outline" class="h-full">
        <ElScrollbar class="h-full">
          <div>
            <ElTree
              :data="outlineData"
              node-key="id"
              default-expand-all
              highlight-current
              :expand-on-click-node="false"
              @node-click="handleNodeClick"
            >
              <template #default="{ node, data }">
                <div class="flex items-center text-xs">
                  <ElIcon class="mr-1" v-if="data.icon">
                    <component :is="data.icon" />
                  </ElIcon>
                  <span
                    :class="{
                      'text-[var(--el-text-color-placeholder)]': data.isVirtual,
                    }"
                    >{{ node.label }}</span
                  >
                </div>
              </template>
            </ElTree>
          </div>
        </ElScrollbar>
      </ElTabPane>

      <ElTabPane label="模板" name="template" class="h-full">
        <ElScrollbar class="h-full">
          <div class="grid grid-cols-2 gap-4 p-4">
            <div
              v-for="(tpl, index) in templates"
              :key="index"
              class="flex cursor-pointer flex-col items-center justify-center rounded border border-[var(--el-border-color)] bg-[var(--el-fill-color-light)] p-4 transition-all hover:border-[var(--el-color-primary)] hover:shadow-sm"
              @click="applyTemplate(tpl)"
            >
              <ElIcon :size="24" class="mb-2 text-[var(--el-text-color-secondary)]">
                <component :is="getTemplateIcon(tpl.icon)" />
              </ElIcon>
              <span class="text-xs text-[var(--el-text-color-regular)]">{{
                tpl.title
              }}</span>
            </div>
          </div>
        </ElScrollbar>
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<style scoped>
:deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}
</style>

