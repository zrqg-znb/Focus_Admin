<template>
  <div
    class="form-item-wrapper relative p-2 border border-dashed border-[var(--el-border-color)] hover:bg-[var(--el-color-primary-light-9)] hover:border-[var(--el-color-primary)] group mb-2 cursor-move"
    :class="{ 'is-active ring-2 ring-[var(--el-color-primary)] bg-[var(--el-color-primary-light-9)]': active }"
    @click.stop="handleSelect"
  >
    <!-- 栅格布局渲染 -->
    <div v-if="schema.type === 'grid'" class="grid-layout">
      <el-row :gutter="schema.props.gutter" class="h-full min-h-[60px]">
        <el-col
          v-for="(col, index) in schema.columns"
          :key="index"
          :span="col.span"
          class="border border-dashed border-[var(--el-border-color)] min-h-[60px] p-2"
        >
          <draggable
            v-model="col.children"
            group="form-design"
            item-key="id"
            class="h-full min-h-[50px]"
            ghost-class="ghost"
            :animation="200"
            @add="handleAdd"
          >
            <template #item="{ element }">
              <FormItemWrapper
                :schema="element"
                :active="store.activeId === element.id"
                @delete="handleDelete"
              />
            </template>
          </draggable>
        </el-col>
      </el-row>
    </div>

    <!-- 分割线 -->
    <div v-else-if="schema.type === 'divider'" class="py-2">
      <el-divider
        v-bind="schema.props"
      >
        {{ schema.label !== '分割线' ? schema.label : '' }}
      </el-divider>
    </div>

    <!-- 折叠面板 -->
    <div v-else-if="schema.type === 'collapse'" class="mb-2">
      <el-collapse
        v-bind="schema.props"
        v-model="activeCollapse"
        class="border border-dashed border-[var(--el-border-color)] p-1"
      >
        <el-collapse-item
          v-for="(item, index) in schema.items"
          :key="index"
          :title="item.title"
          :name="item.name"
        >
          <div class="p-2 min-h-[50px]">
            <draggable
              v-model="item.children"
              group="form-design"
              item-key="id"
              class="min-h-[50px]"
              ghost-class="ghost"
              :animation="200"
              @add="handleAdd"
            >
              <template #item="{ element }">
                <FormItemWrapper
                  :schema="element"
                  :active="store.activeId === element.id"
                  @delete="handleDelete"
                />
              </template>
            </draggable>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 标签页 -->
    <div v-else-if="schema.type === 'tabs'" class="mb-2">
      <el-tabs
        v-bind="schema.props"
        v-model="activeTab"
        class="border border-dashed border-[var(--el-border-color)] p-1"
      >
        <el-tab-pane
          v-for="(item, index) in schema.items"
          :key="index"
          :label="item.label"
          :name="item.name"
        >
          <div class="p-2 min-h-[50px]">
            <draggable
              v-model="item.children"
              group="form-design"
              item-key="id"
              class="min-h-[50px]"
              ghost-class="ghost"
              :animation="200"
              @add="handleAdd"
            >
              <template #item="{ element }">
                <FormItemWrapper
                  :schema="element"
                  :active="store.activeId === element.id"
                  @delete="handleDelete"
                />
              </template>
            </draggable>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 警告提示 -->
    <div v-else-if="schema.type === 'alert'" class="py-2">
       <el-alert v-bind="schema.props as any" />
    </div>

    <!-- 时间线 -->
    <div v-else-if="schema.type === 'timeline'" class="p-2">
       <el-timeline v-bind="schema.props">
         <el-timeline-item
           v-for="(item, index) in schema.items"
           :key="index"
           :timestamp="item.timestamp"
           :type="item.type as any"
           :icon="item.icon"
           :color="item.color"
         >
           {{ item.content }}
         </el-timeline-item>
       </el-timeline>
    </div>

    <!-- 子表单 -->
    <div v-else-if="schema.type === 'sub-table'" class="mb-2">
      <div class="p-2 bg-[var(--el-fill-color-light)] border border-dashed border-[var(--el-border-color)] rounded">
        <div class="text-sm font-bold text-[var(--el-text-color-primary)] mb-2 flex justify-between">
          <span>子表单: {{ schema.label }}</span>
          <span class="text-xs font-normal text-[var(--el-text-color-placeholder)]">拖拽组件至下方添加列</span>
        </div>

        <!-- 水平拖拽区域，模拟列 -->
        <draggable
          v-model="schema.children"
          group="form-design"
          item-key="id"
          class="flex flex-row gap-2 overflow-x-auto min-h-[100px] p-2 bg-[var(--el-bg-color)] border border-[var(--el-border-color)] rounded items-start"
          ghost-class="ghost"
          :animation="200"
          @add="handleAdd"
        >
          <template #item="{ element }">
            <div class="min-w-[180px] border border-[var(--el-border-color-lighter)] rounded bg-[var(--el-fill-color-light)]">
               <FormItemWrapper
                  :schema="element"
                  :active="store.activeId === element.id"
                  @delete="handleDelete"
                />
            </div>
          </template>
        </draggable>
      </div>
    </div>

    <!-- 普通组件渲染 -->
    <el-form-item
      v-else
      :label="schema.hideLabel ? undefined : schema.label"
      :label-width="schema.hideLabel ? '0px' : undefined"
      :required="schema.props.required"
      :prop="schema.field"
      :class="{ 'pointer-events-none': !interactive }"
    >
      <!-- 动态组件渲染 -->
      <component
        :is="getComponentMap(schema.type)"
        v-bind="schema.props"
        v-model="dummyValue"
        :options="['cascader'].includes(schema.type) ? schema.options : undefined"
        :data="['tree-select'].includes(schema.type) ? schema.options : undefined"
        :style="{ width: schema.type !== 'switch' && schema.props.width ? schema.props.width : undefined }"
      >
        <!-- 特殊处理 Select/Radio/Checkbox 的选项 -->
        <template v-if="['select', 'radio', 'checkbox'].includes(schema.type)">
          <template v-if="schema.type === 'select'">
            <el-option
              v-for="opt in schema.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </template>

          <template v-else-if="schema.type === 'radio'">
            <el-radio
              v-for="opt in schema.options"
              :key="opt.value"
              :label="opt.value"
            >
              {{ opt.label }}
            </el-radio>
          </template>

          <template v-else-if="schema.type === 'checkbox'">
            <el-checkbox
              v-for="opt in schema.options"
              :key="opt.value"
              :label="opt.value"
            >
              {{ opt.label }}
            </el-checkbox>
          </template>
        </template>
      </component>
    </el-form-item>

    <!-- 操作按钮（选中或悬停时显示） -->
    <div
      class="action-bar absolute bottom-0 right-0 z-20 translate-y-1/1 items-center bg-[var(--el-color-primary-light-9)] backdrop-blur-sm rounded shadow-sm"
      :class="active ? 'flex' : 'hidden group-hover:flex'"
    >
      <div class="p-1 rounded cursor-pointer flex items-center justify-center text-[var(--el-color-primary)] hover:text-[var(--el-color-primary-dark-2)] hover:bg-[var(--el-color-primary-light-8)] transition-all" title="复制" @click.stop="handleCopy">
        <el-icon :size="14"><CopyDocument /></el-icon>
      </div>
      <div class="p-1 rounded cursor-pointer flex items-center justify-center text-[var(--el-color-danger)] hover:text-[var(--el-color-danger-dark-2)] hover:bg-[var(--el-color-danger-light-8)] transition-all" title="删除" @click.stop="handleDeleteSelf">
        <el-icon :size="14"><Delete /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue';
import {
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElRadioGroup,
  ElRadio,
  ElCheckboxGroup,
  ElCheckbox,
  ElDatePicker,
  ElInputNumber,
  ElTimePicker,
  ElSwitch,
  ElSlider,
  ElRate,
  ElColorPicker,
  ElRow,
  ElCol,
  ElDivider,
  ElCollapse,
  ElCollapseItem,
  ElTabs,
  ElTabPane,
  ElCascader,
  ElTreeSelect,
  ElAlert,
  ElTimeline,
  ElTimelineItem,
  ElIcon
} from 'element-plus';
import { CopyDocument, Delete } from '@element-plus/icons-vue';
import draggable from 'vuedraggable';
import type { FormItemSchema } from '../store/formDesignStore';
import { useFormDesignStore } from '../store/formDesignStore';

import DeptSelector from '../../zq-form/dept-selector/dept-selector.vue';
import UserSelector from '../../zq-form/user-selector/user-selector.vue';
import RoleSelector from '../../zq-form/role-selector/role-selector.vue';
import PostSelector from '../../zq-form/post-selector/post-selector.vue';
import CronSelector from '../../zq-form/cron-selector/cron-selector.vue';
import ImageSelector from '../../zq-form/image-selector/image-selector.vue';
import FileSelector from '../../zq-form/file-selector/file-selector.vue';

defineOptions({
  name: 'FormItemWrapper'
});

const props = withDefaults(defineProps<{
  schema: FormItemSchema;
  active: boolean;
  interactive?: boolean;
}>(), {
  interactive: true
});

const emit = defineEmits(['delete']);
const store = useFormDesignStore();
const dummyValue = ref(null); // 仅用于展示，不需要真实绑定数据

// 布局组件状态管理
const activeCollapse = ref<any>([]);
const activeTab = ref<string>('');

watchEffect(() => {
  const items = props.schema.items || [];
  if (props.schema.type === 'collapse' && items.length > 0) {
    // 设计模式下，默认展开所有，方便拖拽
    // 如果是手风琴模式，则只能展开一个，默认第一个
    if (props.schema.props.accordion) {
      // 如果当前没选中，或者选中的不在 items 里，重置为第一个
      const current = activeCollapse.value;
      const firstItem = items[0];
      if (firstItem) {
        const first = firstItem.name;
        if (!current || (Array.isArray(current) && current.length === 0)) {
           activeCollapse.value = first;
        }
      }
    } else {
      // 非手风琴模式，全展开
      activeCollapse.value = items.map((i: any) => i.name);
    }
  } else if (props.schema.type === 'tabs' && items.length > 0) {
    // 如果没有选中的标签，默认选中第一个
    if (!activeTab.value || !items.find((i: any) => i.name === activeTab.value)) {
      const firstItem = items[0];
      if (firstItem) {
        activeTab.value = firstItem.name || '';
      }
    }
  }
});

const handleSelect = () => {
  store.setActive(props.schema.id);
};

const handleCopy = () => {
  store.copyItem(props.schema.id);
};

const handleDeleteSelf = () => {
  // 调用 store 的递归删除
  store.deleteItem(props.schema.id);
};

const handleDelete = (id: string) => {
  store.deleteItem(id);
};

const handleAdd = (_evt: any) => {
  // 可以在这里处理新增组件的选中逻辑
  // 这里的 evt.item 是 DOM 元素，evt.newIndex 是索引
  // 我们需要获取对应的数据对象来 setActive
  // 由于 draggable v-model 绑定的是 col.children
  // 我们可以尝试获取刚刚添加的 item
  // 但在这里比较难直接获取到数据对象，除非去 col.children[newIndex] 找
  // 暂时忽略，用户手动点击选中即可
};

// 组件映射表
const COMPONENT_MAP: Record<string, any> = {
  input: ElInput,
  textarea: ElInput, // Element Plus 中 input type="textarea"
  select: ElSelect,
  radio: ElRadioGroup,
  checkbox: ElCheckboxGroup,
  date: ElDatePicker,
  'input-number': ElInputNumber,
  time: ElTimePicker,
  switch: ElSwitch,
  slider: ElSlider,
  rate: ElRate,
  color: ElColorPicker,
  cascader: ElCascader,
  'tree-select': ElTreeSelect,
  'dept-selector': DeptSelector,
  'user-selector': UserSelector,
  'role-selector': RoleSelector,
  'post-selector': PostSelector,
  'cron-selector': CronSelector,
  'image-selector': ImageSelector,
  'file-selector': FileSelector
};

function getComponentMap(type: string) {
  return COMPONENT_MAP[type] || ElInput;
}
</script>

<style scoped>
/* 让所有表单组件不可交互，只做展示 */
.pointer-events-none :deep(*) {
  pointer-events: none !important;
}
.ghost {
  border-top: 2px solid var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  height: 4px;
  overflow: hidden;
  position: relative;
}
.ghost::after {
  content: '';
  display: block;
  background: var(--el-bg-color);
}
</style>
