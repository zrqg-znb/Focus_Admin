<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  ArrowDown,
  ArrowRight,
  Close,
  Delete,
  Edit,
  Rank,
} from '@element-plus/icons-vue';
import {
  ElButton,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTabs,
} from 'element-plus';
import { storeToRefs } from 'pinia';
import draggable from 'vuedraggable';

import { useFormDesignStore } from '../store/formDesignStore';
import OptionsEditor from './OptionsEditor.vue';

const activeTab = ref('props');
const store = useFormDesignStore();
const { formConf, activeId } = storeToRefs(store);

const showOptionsEditor = ref(false);

const activeSections = ref([
  'basic',
  'text',
  'select',
  'option-style',
  'date',
  'time',
  'number',
  'switch',
  'rate',
  'color',
  'cascader',
  'tree',
  'selector',
  'cron',
  'image',
  'file',
  'alert',
  'timeline',
  'subtable',
  'table-column',
  'grid',
  'collapse',
  'tabs',
  'operation',
  'advanced',
  'validation',
  'options',
]);

const toggleSection = (section: string) => {
  const index = activeSections.value.indexOf(section);
  if (index === -1) {
    activeSections.value.push(section);
  } else {
    activeSections.value.splice(index, 1);
  }
};

const handleOptionsConfirm = (data: any[]) => {
  if (activeItem.value) {
    activeItem.value.options = data;
  }
};

// 获取当前选中的组件对象（支持递归查找）
const activeItem = computed(() => {
  if (!activeId.value) return null;

  function findItem(items: any[]): any {
    for (const item of items) {
      if (item.id === activeId.value) return item;

      // 递归查找 grid
      if (item.columns) {
        for (const col of item.columns) {
          const found = findItem(col.children);
          if (found) return found;
        }
      }

      // 递归查找 collapse / tabs
      if (item.items) {
        for (const subItem of item.items) {
          const found = findItem(subItem.children);
          if (found) return found;
        }
      }

      // 递归查找 sub-table 或其他直接 children
      if (item.children) {
        const found = findItem(item.children);
        if (found) return found;
      }
    }
    return null;
  }

  return findItem(formConf.value.items);
});

// 判断当前组件是否在子表单内
const isInsideSubTable = computed(() => {
  if (!activeId.value) return false;
  let isInside = false;

  function traverse(items: any[], inside: boolean): boolean {
    for (const item of items) {
      if (item.id === activeId.value) {
        isInside = inside;
        return true;
      }

      const childInside = inside || item.type === 'sub-table';

      if (item.columns) {
        for (const col of item.columns) {
          if (traverse(col.children, childInside)) return true;
        }
      }
      if (item.items) {
        for (const subItem of item.items) {
          if (traverse(subItem.children, childInside)) return true;
        }
      }
      if (item.children) {
        if (traverse(item.children, childInside)) return true;
      }
    }
    return false;
  }

  traverse(formConf.value.items, false);
  return isInside;
});

// 检查当前组件是否有该属性
const hasProp = (propName: string) => {
  if (!activeItem.value) return false;
  return (
    activeItem.value.props &&
    Object.prototype.hasOwnProperty.call(activeItem.value.props, propName)
  );
};

// 选项管理
const addOption = () => {
  if (activeItem.value && activeItem.value.options) {
    activeItem.value.options.push({
      label: `选项${activeItem.value.options.length + 1}`,
      value: activeItem.value.options.length + 1,
    });
  }
};

const removeOption = (index: number) => {
  if (activeItem.value && activeItem.value.options) {
    activeItem.value.options.splice(index, 1);
  }
};

// 校验规则相关
const REG_PATTERNS = [
  { label: '自定义', pattern: 'custom', message: '' },
  {
    label: '手机号',
    pattern: String.raw`/^1[3-9]\d{9}$/`,
    message: '手机号格式错误',
  },
  {
    label: '邮箱',
    pattern: String.raw`/^[\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+$/`,
    message: '邮箱格式错误',
  },
  {
    label: '身份证',
    pattern: String.raw`/^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/`,
    message: '身份证格式错误',
  },
  {
    label: 'URL',
    pattern: String.raw`/^((https?|ftp|file):\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/`,
    message: 'URL格式错误',
  },
  { label: '整数', pattern: String.raw`/^-?\d+$/`, message: '请输入整数' },
  {
    label: '数字',
    pattern: String.raw`/^-?\d+(\.\d+)?$/`,
    message: '请输入数字',
  },
];

const LAYOUT_TYPES = new Set(['collapse', 'divider', 'grid', 'tabs']);

const isLayoutComponent = computed(() => {
  if (!activeItem.value) return false;
  return LAYOUT_TYPES.has(activeItem.value.type);
});

const showValidation = computed(() => {
  if (!activeItem.value) return false;
  const type = activeItem.value.type;
  // 排除不需要正则校验的组件
  return (
    !LAYOUT_TYPES.has(type) &&
    !['color', 'rate', 'slider', 'switch'].includes(type)
  );
});

const addRegRule = () => {
  if (!activeItem.value) return;
  if (!activeItem.value.regList) {
    activeItem.value.regList = [];
  }
  activeItem.value.regList.push({ pattern: '', message: '' });
};

const handlePatternChange = (val: string, rule: any) => {
  if (val === 'custom') {
    rule.pattern = '';
    rule.message = '';
    return;
  }
  const pattern = REG_PATTERNS.find((p) => p.pattern === val);
  if (pattern) {
    rule.message = pattern.message;
  }
};
</script>

<template>
  <div
    class="attribute-panel flex h-full w-72 flex-col rounded border-[var(--el-border-color)] bg-[var(--el-bg-color)]"
  >
    <ElTabs v-model="activeTab" class="flex h-full flex-col" stretch>
      <ElTabPane label="组件属性" name="props" class="h-full">
        <ElScrollbar v-if="activeItem" class="h-full">
          <div class="px-4 pb-4">
            <ElForm label-position="top" size="small">
              <!-- 基础属性 -->
              <div
                class="group-title mb-2 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                @click="toggleSection('basic')"
              >
                <span class="font-bold">基础设置</span>
                <ElIcon class="h-4 w-4">
                  <ArrowDown v-if="activeSections.includes('basic')" />
                  <ArrowRight v-else />
                </ElIcon>
              </div>
              <div v-show="activeSections.includes('basic')">
                <ElFormItem label="字段名 (v-model)">
                  <ElInput v-model="activeItem.field" />
                </ElFormItem>

                <ElFormItem label="标题 (Label)">
                  <ElInput v-model="activeItem.label" />
                </ElFormItem>

                <ElFormItem label="隐藏标题">
                  <ElSwitch v-model="activeItem.hideLabel" />
                </ElFormItem>

                <!-- 通用属性 -->
                <ElFormItem
                  label="宽度"
                  v-if="hasProp('width') && activeItem.type !== 'switch'"
                >
                  <ElInput v-model="activeItem.props.width" />
                </ElFormItem>

                <ElFormItem
                  label="占位提示 (Placeholder)"
                  v-if="hasProp('placeholder')"
                >
                  <ElInput v-model="activeItem.props.placeholder" />
                </ElFormItem>
              </div>

              <!-- Input / Textarea 特有属性 -->
              <template v-if="['input', 'textarea'].includes(activeItem.type)">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('text')"
                >
                  <span class="font-bold">文本属性</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('text')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('text')">
                  <ElFormItem label="最大长度">
                    <ElInputNumber
                      v-model="activeItem.props.maxlength"
                      :min="0"
                      controls-position="right"
                      class="w-full"
                    />
                  </ElFormItem>
                  <ElFormItem
                    label="行数"
                    v-if="activeItem.type === 'textarea'"
                  >
                    <ElInputNumber
                      v-model="activeItem.props.rows"
                      :min="1"
                      controls-position="right"
                      class="w-full"
                    />
                  </ElFormItem>
                  <ElFormItem label="显示字数统计">
                    <ElSwitch v-model="activeItem.props.showWordLimit" />
                  </ElFormItem>
                  <ElFormItem label="只读">
                    <ElSwitch v-model="activeItem.props.readonly" />
                  </ElFormItem>
                  <ElFormItem label="密码框" v-if="activeItem.type === 'input'">
                    <ElSwitch v-model="activeItem.props.showPassword" />
                  </ElFormItem>
                </div>
              </template>

              <!-- Select 特有属性 -->
              <template v-if="activeItem.type === 'select'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('select')"
                >
                  <span class="font-bold">选择器属性</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('select')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('select')">
                  <ElFormItem label="可搜索">
                    <ElSwitch v-model="activeItem.props.filterable" />
                  </ElFormItem>
                  <ElFormItem label="多选">
                    <ElSwitch v-model="activeItem.props.multiple" />
                  </ElFormItem>
                  <ElFormItem
                    label="多选折叠 Tag"
                    v-if="activeItem.props.multiple"
                  >
                    <ElSwitch v-model="activeItem.props.collapseTags" />
                  </ElFormItem>
                </div>
              </template>

              <!-- Radio / Checkbox 特有属性 -->
              <template v-if="['radio', 'checkbox'].includes(activeItem.type)">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('option-style')"
                >
                  <span class="font-bold">选项样式</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('option-style')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('option-style')">
                  <ElFormItem label="显示边框">
                    <ElSwitch v-model="activeItem.props.border" />
                  </ElFormItem>
                </div>
              </template>

              <!-- Date 特有属性 -->
              <template v-if="activeItem.type === 'date'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('date')"
                >
                  <span class="font-bold">日期属性</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('date')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('date')">
                  <ElFormItem label="显示类型">
                    <ElSelect v-model="activeItem.props.type">
                      <ElOption label="日期 (date)" value="date" />
                      <ElOption label="周 (week)" value="week" />
                      <ElOption label="月 (month)" value="month" />
                      <ElOption label="年 (year)" value="year" />
                      <ElOption label="日期时间 (datetime)" value="datetime" />
                      <ElOption
                        label="日期范围 (daterange)"
                        value="daterange"
                      />
                      <ElOption
                        label="日期时间范围 (datetimerange)"
                        value="datetimerange"
                      />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="显示格式">
                    <ElInput v-model="activeItem.props.format" />
                  </ElFormItem>
                  <ElFormItem label="值格式">
                    <ElInput v-model="activeItem.props.valueFormat" />
                  </ElFormItem>
                  <template v-if="activeItem.props.type?.includes('range')">
                    <ElFormItem label="分隔符">
                      <ElInput v-model="activeItem.props.rangeSeparator" />
                    </ElFormItem>
                    <ElFormItem label="开始占位">
                      <ElInput v-model="activeItem.props.startPlaceholder" />
                    </ElFormItem>
                    <ElFormItem label="结束占位">
                      <ElInput v-model="activeItem.props.endPlaceholder" />
                    </ElFormItem>
                  </template>
                  <ElFormItem label="可输入">
                    <ElSwitch v-model="activeItem.props.editable" />
                  </ElFormItem>
                </div>
              </template>

              <!-- Time 特有属性 -->
              <template v-if="activeItem.type === 'time'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('time')"
                >
                  <span class="font-bold">时间属性</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('time')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('time')">
                  <ElFormItem label="显示格式">
                    <ElInput v-model="activeItem.props.format" />
                  </ElFormItem>
                  <ElFormItem label="值格式">
                    <ElInput v-model="activeItem.props.valueFormat" />
                  </ElFormItem>
                  <ElFormItem label="箭头控制">
                    <ElSwitch v-model="activeItem.props.arrowControl" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 数字/滑块相关属性 -->
              <template
                v-if="['input-number', 'slider'].includes(activeItem.type)"
              >
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-gray-500 hover:text-blue-500"
                  @click="toggleSection('number')"
                >
                  <span class="font-bold">数值设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('number')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('number')">
                  <div class="flex gap-2">
                    <ElFormItem label="最小值" class="flex-1">
                      <ElInputNumber
                        v-model="activeItem.props.min"
                        controls-position="right"
                        class="w-full"
                      />
                    </ElFormItem>
                    <ElFormItem label="最大值" class="flex-1">
                      <ElInputNumber
                        v-model="activeItem.props.max"
                        controls-position="right"
                        class="w-full"
                      />
                    </ElFormItem>
                  </div>
                  <ElFormItem label="步长">
                    <ElInputNumber
                      v-model="activeItem.props.step"
                      :min="0"
                      controls-position="right"
                    />
                  </ElFormItem>

                  <template v-if="activeItem.type === 'input-number'">
                    <ElFormItem label="精度">
                      <ElInputNumber
                        v-model="activeItem.props.precision"
                        :min="0"
                        controls-position="right"
                      />
                    </ElFormItem>
                    <ElFormItem label="控制按钮">
                      <ElSwitch v-model="activeItem.props.controls" />
                    </ElFormItem>
                    <ElFormItem
                      label="按钮位置"
                      v-if="activeItem.props.controls"
                    >
                      <ElRadioGroup v-model="activeItem.props.controlsPosition">
                        <ElRadioButton label="">默认</ElRadioButton>
                        <ElRadioButton label="right">右侧</ElRadioButton>
                      </ElRadioGroup>
                    </ElFormItem>
                  </template>

                  <template v-if="activeItem.type === 'slider'">
                    <ElFormItem label="显示输入框">
                      <ElSwitch v-model="activeItem.props.showInput" />
                    </ElFormItem>
                    <ElFormItem label="显示间断点">
                      <ElSwitch v-model="activeItem.props.showStops" />
                    </ElFormItem>
                    <ElFormItem label="范围选择">
                      <ElSwitch v-model="activeItem.props.range" />
                    </ElFormItem>
                  </template>
                </div>
              </template>

              <!-- 开关相关属性 -->
              <template v-if="activeItem.type === 'switch'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('switch')"
                >
                  <span class="font-bold">开关设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('switch')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('switch')">
                  <ElFormItem label="组件宽度">
                    <ElInputNumber
                      v-model="activeItem.props.width"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="内联文字">
                    <ElSwitch v-model="activeItem.props.inlinePrompt" />
                  </ElFormItem>
                  <ElFormItem label="开启文案">
                    <ElInput v-model="activeItem.props.activeText" />
                  </ElFormItem>
                  <ElFormItem label="关闭文案">
                    <ElInput v-model="activeItem.props.inactiveText" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 评分相关属性 -->
              <template v-if="activeItem.type === 'rate'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('rate')"
                >
                  <span class="font-bold">评分设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('rate')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('rate')">
                  <ElFormItem label="最大分值">
                    <ElInputNumber
                      v-model="activeItem.props.max"
                      :min="1"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="允许半选">
                    <ElSwitch v-model="activeItem.props.allowHalf" />
                  </ElFormItem>
                  <ElFormItem label="显示分数">
                    <ElSwitch v-model="activeItem.props.showScore" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 颜色相关属性 -->
              <template v-if="activeItem.type === 'color'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('color')"
                >
                  <span class="font-bold">颜色设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('color')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('color')">
                  <ElFormItem label="支持透明度">
                    <ElSwitch v-model="activeItem.props.showAlpha" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 级联选择属性 -->
              <template v-if="activeItem.type === 'cascader'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('cascader')"
                >
                  <span class="font-bold">级联设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('cascader')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('cascader')">
                  <ElFormItem label="分隔符">
                    <ElInput v-model="activeItem.props.separator" />
                  </ElFormItem>
                  <ElFormItem label="显示全路径">
                    <ElSwitch v-model="activeItem.props['show-all-levels']" />
                  </ElFormItem>
                  <ElFormItem label="可搜索">
                    <ElSwitch v-model="activeItem.props.filterable" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 树形选择属性 -->
              <template v-if="activeItem.type === 'tree-select'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('tree')"
                >
                  <span class="font-bold">树形设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('tree')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('tree')">
                  <ElFormItem label="多选">
                    <ElSwitch v-model="activeItem.props.multiple" />
                  </ElFormItem>
                  <ElFormItem label="显示复选框">
                    <ElSwitch v-model="activeItem.props.showCheckbox" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 部门/用户/角色/岗位选择通用属性 -->
              <template
                v-if="
                  [
                    'dept-selector',
                    'user-selector',
                    'role-selector',
                    'post-selector',
                  ].includes(activeItem.type)
                "
              >
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('selector')"
                >
                  <span class="font-bold">选择器设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('selector')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('selector')">
                  <ElFormItem label="多选">
                    <ElSwitch v-model="activeItem.props.multiple" />
                  </ElFormItem>
                  <ElFormItem label="可搜索">
                    <ElSwitch v-model="activeItem.props.filterable" />
                  </ElFormItem>

                  <!-- 用户选择器特有属性 -->
                  <template v-if="activeItem.type === 'user-selector'">
                    <ElFormItem label="显示模式">
                      <ElRadioGroup v-model="activeItem.props.displayMode">
                        <ElRadioButton label="select">下拉框</ElRadioButton>
                        <ElRadioButton label="button">按钮</ElRadioButton>
                      </ElRadioGroup>
                    </ElFormItem>
                  </template>
                </div>
              </template>

              <!-- Cron表达式属性 -->
              <template v-if="activeItem.type === 'cron-selector'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('cron')"
                >
                  <span class="font-bold">Cron设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('cron')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('cron')">
                  <ElFormItem label="隐藏秒">
                    <ElSwitch v-model="activeItem.props.hideSecond" />
                  </ElFormItem>
                  <ElFormItem label="隐藏年">
                    <ElSwitch v-model="activeItem.props.hideYear" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 图片选择属性 -->
              <template v-if="activeItem.type === 'image-selector'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('image')"
                >
                  <span class="font-bold">图片设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('image')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('image')">
                  <ElFormItem label="多选">
                    <ElSwitch v-model="activeItem.props.multiple" />
                  </ElFormItem>
                  <ElFormItem label="最大大小(MB)">
                    <ElInputNumber
                      v-model="activeItem.props.maxSize"
                      :min="0"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="网格列数">
                    <ElInputNumber
                      v-model="activeItem.props.gridColumns"
                      :min="1"
                      :max="12"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="启用裁剪">
                    <ElSwitch v-model="activeItem.props.enableCrop" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 文件选择属性 -->
              <template v-if="activeItem.type === 'file-selector'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('file')"
                >
                  <span class="font-bold">文件设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('file')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('file')">
                  <ElFormItem label="多选">
                    <ElSwitch v-model="activeItem.props.multiple" />
                  </ElFormItem>
                  <ElFormItem
                    label="最大文件数"
                    v-if="activeItem.props.multiple"
                  >
                    <ElInputNumber
                      v-model="activeItem.props.limit"
                      :min="1"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="最大大小(MB)">
                    <ElInputNumber
                      v-model="activeItem.props.maxSize"
                      :min="0"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="接受类型">
                    <ElInput
                      v-model="activeItem.props.accept"
                      placeholder="例: .jpg,.png,image/*"
                    />
                  </ElFormItem>
                  <ElFormItem label="显示模式">
                    <ElSelect v-model="activeItem.props.displayMode">
                      <ElOption label="列表 (List)" value="list" />
                      <ElOption label="气泡 (Popover)" value="popover" />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="显示大小">
                    <ElSwitch v-model="activeItem.props.showSize" />
                  </ElFormItem>
                  <ElFormItem label="显示图标">
                    <ElSwitch v-model="activeItem.props.showIcon" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 警告提示属性 -->
              <template v-if="activeItem.type === 'alert'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('alert')"
                >
                  <span class="font-bold">提示设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('alert')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('alert')">
                  <ElFormItem label="标题">
                    <ElInput v-model="activeItem.props.title" />
                  </ElFormItem>
                  <ElFormItem label="类型">
                    <ElSelect v-model="activeItem.props.type">
                      <ElOption label="成功 (success)" value="success" />
                      <ElOption label="警告 (warning)" value="warning" />
                      <ElOption label="信息 (info)" value="info" />
                      <ElOption label="错误 (error)" value="error" />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="描述">
                    <ElInput
                      v-model="activeItem.props.description"
                      type="textarea"
                      :rows="2"
                    />
                  </ElFormItem>
                  <ElFormItem label="显示图标">
                    <ElSwitch v-model="activeItem.props.showIcon" />
                  </ElFormItem>
                  <ElFormItem label="可关闭">
                    <ElSwitch v-model="activeItem.props.closable" />
                  </ElFormItem>
                  <ElFormItem label="居中">
                    <ElSwitch v-model="activeItem.props.center" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 时间线属性 -->
              <template v-if="activeItem.type === 'timeline'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('timeline')"
                >
                  <span class="font-bold">时间线设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('timeline')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('timeline')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="倒序">
                    <ElSwitch v-model="activeItem.props.reverse" />
                  </ElFormItem>

                  <div
                    class="mb-3 border-b pb-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    基础设置
                  </div>
                  <div
                    class="mb-2 mt-2 flex items-center justify-between border-t pt-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    <span>节点管理</span>
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click="
                        activeItem?.items &&
                        activeItem.items.push({
                          timestamp: '2024-01-01',
                          content: '新节点',
                          type: 'primary',
                        })
                      "
                    >
                      添加
                    </ElButton>
                  </div>

                  <draggable
                    v-model="activeItem.items"
                    item-key="timestamp"
                    handle=".handle"
                    :animation="200"
                  >
                    <template #item="{ element, index }">
                      <div
                        class="mb-2 flex flex-col gap-2 rounded border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] p-2"
                      >
                        <div class="flex items-center justify-between">
                          <ElIcon
                            class="handle w-4 cursor-move text-[var(--el-text-color-secondary)]"
                          >
                            <Rank />
                          </ElIcon>
                          <span class="text-xs font-bold text-gray-500"
                            >节点 {{ index + 1 }}</span
                          >
                          <ElButton
                            type="danger"
                            link
                            size="small"
                            @click="
                              activeItem?.items &&
                              activeItem.items.splice(index, 1)
                            "
                            v-if="activeItem.items.length > 1"
                          >
                            <ElIcon class="w-4"><Delete /></ElIcon>
                          </ElButton>
                        </div>
                        <ElInput
                          v-model="element.content"
                          placeholder="内容"
                          size="small"
                        />
                        <ElInput
                          v-model="element.timestamp"
                          placeholder="时间戳"
                          size="small"
                        />
                        <ElSelect
                          v-model="element.type"
                          placeholder="类型"
                          size="small"
                        >
                          <ElOption label="Primary" value="primary" />
                          <ElOption label="Success" value="success" />
                          <ElOption label="Warning" value="warning" />
                          <ElOption label="Danger" value="danger" />
                          <ElOption label="Info" value="info" />
                        </ElSelect>
                        <el-color-picker
                          v-model="element.color"
                          show-alpha
                          size="small"
                        />
                      </div>
                    </template>
                  </draggable>
                </div>
              </template>

              <!-- 子表单属性 -->
              <template v-if="activeItem.type === 'sub-table'">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('subtable')"
                >
                  <span class="font-bold">子表单设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('subtable')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('subtable')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="显示模式">
                    <ElSelect v-model="activeItem.props.displayMode" placeholder="请选择">
                      <ElOption label="表格模式 (Table)" value="table" />
                      <ElOption label="卡片模式 (Card)" value="card" />
                      <ElOption label="行内模式 (Inline)" value="inline" />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="按钮文案">
                    <ElInput 
                      v-model="activeItem.props.addButtonText" 
                      placeholder="默认: 添加" 
                    />
                  </ElFormItem>
                  
                  <ElFormItem label="显示序号">
                    <ElSwitch v-model="activeItem.props.showIndex" />
                  </ElFormItem>
                  <ElFormItem label="显示合计">
                    <ElSwitch v-model="activeItem.props.summary" />
                  </ElFormItem>
                  <ElFormItem label="允许添加">
                    <ElSwitch v-model="activeItem.props.addable" />
                  </ElFormItem>
                  <ElFormItem label="允许删除">
                    <ElSwitch v-model="activeItem.props.deletable" />
                  </ElFormItem>
                  
                  <div class="mt-2 mb-2 border-t border-[var(--el-border-color-lighter)]"></div>
                  <div class="text-xs font-bold text-[var(--el-text-color-secondary)] mb-2">行控制</div>
                  
                  <div class="flex gap-2">
                    <ElFormItem label="最少行数" class="flex-1">
                      <ElInputNumber 
                        v-model="activeItem.props.minRows" 
                        :min="0" 
                        controls-position="right"
                        class="w-full"
                      />
                    </ElFormItem>
                    <ElFormItem label="最多行数" class="flex-1">
                      <ElInputNumber 
                        v-model="activeItem.props.maxRows" 
                        :min="0" 
                        controls-position="right"
                        class="w-full"
                      />
                    </ElFormItem>
                  </div>
                  
                  <ElFormItem label="允许排序">
                    <ElSwitch v-model="activeItem.props.sortable" />
                  </ElFormItem>
                  <ElFormItem label="允许复制行">
                    <ElSwitch v-model="activeItem.props.copyable" />
                  </ElFormItem>
                  
                  <div class="mt-2 mb-2 border-t border-[var(--el-border-color-lighter)]"></div>
                  <div class="text-xs font-bold text-[var(--el-text-color-secondary)] mb-2">分页设置</div>
                  <ElFormItem label="开启分页">
                    <ElSwitch v-model="activeItem.props.pagination" />
                  </ElFormItem>
                  <ElFormItem label="每页条数" v-if="activeItem.props.pagination">
                    <ElInputNumber 
                      v-model="activeItem.props.pageSize" 
                      :min="1" 
                      :max="100"
                      controls-position="right"
                      class="w-full"
                    />
                  </ElFormItem>
                </div>
              </template>

              <!-- 表格列设置 (仅在子表单内部组件显示) -->
              <template v-if="isInsideSubTable">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('table-column')"
                >
                  <span class="font-bold">表格列设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('table-column')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('table-column')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="列宽度">
                    <ElInput 
                      v-model="activeItem.props.columnWidth" 
                      placeholder="例如: 100px 或 20%"
                    />
                    <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
                      不填则自动分配宽度
                    </div>
                  </ElFormItem>
                  <ElFormItem label="列对齐">
                    <ElSelect v-model="activeItem.props.columnAlign">
                      <ElOption label="左对齐 (left)" value="left" />
                      <ElOption label="居中 (center)" value="center" />
                      <ElOption label="右对齐 (right)" value="right" />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="固定列">
                    <ElSelect v-model="activeItem.props.columnFixed">
                      <ElOption label="不固定" value="" />
                      <ElOption label="固定左侧" value="left" />
                      <ElOption label="固定右侧" value="right" />
                    </ElSelect>
                  </ElFormItem>
                </div>
              </template>

              <!-- 栅格布局属性 -->
              <template v-if="activeItem.type === 'grid' && activeItem.columns">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('grid')"
                >
                  <span class="font-bold">栅格设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('grid')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('grid')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="栅格间隔">
                    <ElInputNumber
                      v-model="activeItem.props.gutter"
                      :min="0"
                      controls-position="right"
                    />
                  </ElFormItem>
                  <ElFormItem label="水平排列">
                    <ElSelect v-model="activeItem.props.justify">
                      <ElOption label="左对齐 (start)" value="start" />
                      <ElOption label="右对齐 (end)" value="end" />
                      <ElOption label="居中 (center)" value="center" />
                      <ElOption
                        label="两侧间隔相等 (space-around)"
                        value="space-around"
                      />
                      <ElOption
                        label="两端对齐 (space-between)"
                        value="space-between"
                      />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="垂直排列">
                    <ElSelect v-model="activeItem.props.align">
                      <ElOption label="顶部对齐 (top)" value="top" />
                      <ElOption label="居中 (middle)" value="middle" />
                      <ElOption label="底部对齐 (bottom)" value="bottom" />
                    </ElSelect>
                  </ElFormItem>

                  <div
                    class="mb-3 border-b pb-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    基础设置
                  </div>
                  <div
                    class="mb-2 mt-2 border-t pt-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    列配置
                  </div>
                  <div
                    v-for="(col, index) in activeItem.columns"
                    :key="index"
                    class="mb-2 flex items-center gap-2"
                  >
                    <span class="w-10 text-xs">列{{ index + 1 }}</span>
                    <ElInputNumber
                      v-model="col.span"
                      :min="1"
                      :max="24"
                      size="small"
                      class="flex-1"
                    />
                    <ElButton
                      type="danger"
                      link
                      size="small"
                      @click="
                        activeItem?.columns &&
                        activeItem.columns.splice(index, 1)
                      "
                      v-if="activeItem.columns.length > 1"
                    >
                      <ElIcon class="w-4"><Delete /></ElIcon>
                    </ElButton>
                  </div>
                  <ElButton
                    type="primary"
                    link
                    size="small"
                    @click="
                      activeItem?.columns &&
                      activeItem.columns.push({ span: 12, children: [] })
                    "
                  >
                    + 添加列
                  </ElButton>
                </div>
              </template>

              <!-- 折叠面板属性 -->
              <template
                v-if="activeItem.type === 'collapse' && activeItem.items"
              >
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('collapse')"
                >
                  <span class="font-bold">面板配置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('collapse')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('collapse')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="手风琴模式">
                    <ElSwitch v-model="activeItem.props.accordion" />
                  </ElFormItem>

                  <div
                    class="mb-3 border-b pb-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    基础设置
                  </div>
                  <div
                    class="mb-2 mt-2 flex items-center justify-between border-t pt-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    <span>子面板管理</span>
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click="
                        activeItem?.items &&
                        activeItem.items.push({
                          title: '新面板',
                          name: `${Date.now()}`,
                          children: [],
                        })
                      "
                    >
                      添加
                    </ElButton>
                  </div>

                  <draggable
                    v-model="activeItem.items"
                    item-key="name"
                    handle=".handle"
                    :animation="200"
                  >
                    <template #item="{ element, index }">
                      <div
                        class="mb-2 flex items-center gap-2 rounded border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] p-2"
                      >
                        <ElIcon
                          class="handle w-4 cursor-move text-[var(--el-text-color-secondary)]"
                        >
                          <Rank />
                        </ElIcon>
                        <div class="flex flex-1 flex-col gap-1">
                          <ElInput
                            v-model="element.title"
                            placeholder="标题"
                            size="small"
                          />
                          <ElInput
                            v-model="element.name"
                            placeholder="唯一标识(Name)"
                            size="small"
                          />
                        </div>
                        <ElButton
                          type="danger"
                          link
                          size="small"
                          @click="
                            activeItem?.items &&
                            activeItem.items.splice(index, 1)
                          "
                          v-if="activeItem.items.length > 1"
                        >
                          <ElIcon class="w-4"><Delete /></ElIcon>
                        </ElButton>
                      </div>
                    </template>
                  </draggable>
                </div>
              </template>

              <!-- 标签页属性 -->
              <template v-if="activeItem.type === 'tabs' && activeItem.items">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('tabs')"
                >
                  <span class="font-bold">标签页配置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('tabs')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div
                  v-show="activeSections.includes('tabs')"
                  class="rounded border border-[var(--el-border-color)] bg-[var(--el-bg-color)] p-2"
                >
                  <ElFormItem label="风格类型">
                    <ElSelect v-model="activeItem.props.type">
                      <ElOption label="默认" value="" />
                      <ElOption label="卡片化" value="card" />
                      <ElOption label="边框卡片" value="border-card" />
                    </ElSelect>
                  </ElFormItem>
                  <ElFormItem label="标签位置">
                    <ElRadioGroup
                      v-model="activeItem.props.tabPosition"
                      size="small"
                    >
                      <ElRadioButton label="top">上</ElRadioButton>
                      <ElRadioButton label="right">右</ElRadioButton>
                      <ElRadioButton label="bottom">下</ElRadioButton>
                      <ElRadioButton label="left">左</ElRadioButton>
                    </ElRadioGroup>
                  </ElFormItem>

                  <div
                    class="mb-3 border-b pb-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    基础设置
                  </div>
                  <div
                    class="mb-2 mt-2 flex items-center justify-between border-t pt-2 font-bold text-[var(--el-text-color-primary)]"
                  >
                    <span>标签项管理</span>
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click="
                        activeItem?.items &&
                        activeItem.items.push({
                          label: '新标签',
                          name: `${Date.now()}`,
                          children: [],
                        })
                      "
                    >
                      添加
                    </ElButton>
                  </div>

                  <draggable
                    v-model="activeItem.items"
                    item-key="name"
                    handle=".handle"
                    :animation="200"
                  >
                    <template #item="{ element, index }">
                      <div
                        class="mb-2 flex items-center gap-2 rounded border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] p-2"
                      >
                        <ElIcon
                          class="handle w-4 cursor-move text-[var(--el-text-color-secondary)]"
                        >
                          <Rank />
                        </ElIcon>
                        <div class="flex flex-1 flex-col gap-1">
                          <ElInput
                            v-model="element.label"
                            placeholder="标签名"
                            size="small"
                          />
                          <ElInput
                            v-model="element.name"
                            placeholder="唯一标识(Name)"
                            size="small"
                          />
                        </div>
                        <ElButton
                          type="danger"
                          link
                          size="small"
                          @click="
                            activeItem?.items &&
                            activeItem.items.splice(index, 1)
                          "
                          v-if="activeItem.items.length > 1"
                        >
                          <ElIcon class="w-4"><Delete /></ElIcon>
                        </ElButton>
                      </div>
                    </template>
                  </draggable>
                </div>
              </template>

              <!-- 操作属性 -->
              <template v-if="!isLayoutComponent">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('operation')"
                >
                  <span class="font-bold">操作属性</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('operation')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('operation')">
                  <ElFormItem label="可清空" v-if="hasProp('clearable')">
                    <ElSwitch v-model="activeItem.props.clearable" />
                  </ElFormItem>
                  <ElFormItem label="禁用" v-if="hasProp('disabled')">
                    <ElSwitch v-model="activeItem.props.disabled" />
                  </ElFormItem>
                  <ElFormItem label="必填">
                    <ElSwitch v-model="activeItem.props.required" />
                  </ElFormItem>
                </div>
              </template>

              <!-- 高级设置 -->
              <div v-if="!isLayoutComponent">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('advanced')"
                >
                  <span class="font-bold">高级设置</span>
                  <ElIcon class="h-4 w-4">
                    <ArrowDown v-if="activeSections.includes('advanced')" />
                    <ArrowRight v-else />
                  </ElIcon>
                </div>
                <div v-show="activeSections.includes('advanced')">
                  <ElFormItem label="显示条件">
                    <ElInput
                      v-model="activeItem.showCondition"
                      type="textarea"
                      :rows="2"
                      placeholder="例: model.field_abc === '1'"
                    />
                    <div
                      class="mt-1 text-xs text-[var(--el-text-color-secondary)]"
                    >
                      使用 model.字段名 引用值。为空时默认显示。
                    </div>
                  </ElFormItem>
                </div>
              </div>

              <!-- 校验规则 (新增) -->
              <div v-if="showValidation" class="mt-4">
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-[15px] text-gray-500 hover:text-blue-500"
                  @click="toggleSection('validation')"
                >
                  <span class="font-bold">正则校验</span>
                  <div class="flex items-center">
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click.stop="addRegRule"
                      class="mr-2"
                      v-if="activeSections.includes('validation')"
                    >
                      新增规则
                    </ElButton>
                    <ElIcon class="h-4 w-4">
                      <ArrowDown v-if="activeSections.includes('validation')" />
                      <ArrowRight v-else />
                    </ElIcon>
                  </div>
                </div>
                <div v-show="activeSections.includes('validation')">
                  <div
                    v-for="(rule, index) in activeItem.regList"
                    :key="index"
                    class="relative mb-4 rounded border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] p-2"
                  >
                    <ElButton
                      type="danger"
                      link
                      size="small"
                      class="absolute right-1 top-1"
                      @click="
                        activeItem?.regList &&
                        activeItem.regList.splice(index, 1)
                      "
                    >
                      <ElIcon class="w-3"><Close /></ElIcon>
                    </ElButton>

                    <ElFormItem label="常用正则" class="mb-1">
                      <ElSelect
                        v-model="rule.pattern"
                        @change="
                          (val: string) => handlePatternChange(val, rule)
                        "
                        placeholder="选择常用正则"
                      >
                        <ElOption
                          v-for="item in REG_PATTERNS"
                          :key="item.pattern"
                          :label="item.label"
                          :value="item.pattern"
                        />
                      </ElSelect>
                    </ElFormItem>

                    <ElFormItem label="正则规则" class="mb-1">
                      <ElInput v-model="rule.pattern" placeholder="/^...$/" />
                    </ElFormItem>

                    <ElFormItem label="错误提示" class="mb-0">
                      <ElInput
                        v-model="rule.message"
                        placeholder="请输入错误提示"
                      />
                    </ElFormItem>
                  </div>
                </div>
              </div>

              <!-- 选项配置 (针对 Select/Radio/Checkbox/Cascader/TreeSelect) -->
              <div
                v-if="
                  [
                    'select',
                    'radio',
                    'checkbox',
                    'cascader',
                    'tree-select',
                  ].includes(activeItem.type)
                "
                class="mt-4"
              >
                <div
                  class="group-title mb-2 mt-4 flex cursor-pointer select-none items-center justify-between pb-2 text-xs text-[var(--el-text-color-regular)] hover:text-[var(--el-color-primary)]"
                  @click="toggleSection('options')"
                >
                  <span class="font-bold">选项配置</span>
                  <div class="flex items-center">
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click.stop="addOption"
                      v-if="
                        ['select', 'radio', 'checkbox'].includes(
                          activeItem.type,
                        ) && activeSections.includes('options')
                      "
                      class="mr-2"
                    >
                      新增选项
                    </ElButton>
                    <ElIcon class="h-4 w-4">
                      <ArrowDown v-if="activeSections.includes('options')" />
                      <ArrowRight v-else />
                    </ElIcon>
                  </div>
                </div>

                <div v-show="activeSections.includes('options')">
                  <!-- 简单列表编辑 (Select/Radio/Checkbox) -->
                  <draggable
                    v-if="
                      ['select', 'radio', 'checkbox'].includes(activeItem.type)
                    "
                    v-model="activeItem.options"
                    item-key="value"
                    handle=".handle"
                    :animation="200"
                  >
                    <template #item="{ element, index }">
                      <div class="mb-2 flex items-center gap-2">
                        <ElIcon
                          class="handle w-4 cursor-move text-[var(--el-text-color-secondary)]"
                        >
                          <Rank />
                        </ElIcon>
                        <ElInput
                          v-model="element.label"
                          placeholder="Label"
                          size="small"
                        />
                        <ElInput
                          v-model="element.value"
                          placeholder="Value"
                          size="small"
                        />
                        <ElButton
                          type="danger"
                          link
                          size="small"
                          @click="removeOption(index)"
                        >
                          <ElIcon class="w-4"><Delete /></ElIcon>
                        </ElButton>
                      </div>
                    </template>
                  </draggable>

                  <!-- 复杂树形编辑 (Cascader/TreeSelect) -->
                  <div v-else class="flex flex-col gap-2">
                    <div
                      class="mb-2 text-xs text-[var(--el-text-color-secondary)]"
                    >
                      该组件支持多层级数据，请点击下方按钮进行编辑。
                    </div>
                    <ElButton
                      type="primary"
                      plain
                      class="w-full"
                      @click="showOptionsEditor = true"
                    >
                      <ElIcon class="mr-1 h-4 w-4"><Edit /></ElIcon>
                      编辑数据源
                    </ElButton>
                  </div>
                </div>
              </div>
            </ElForm>
          </div>
        </ElScrollbar>
        <div
          v-else
          class="flex h-full items-center justify-center p-4 text-sm text-[var(--el-text-color-placeholder)]"
        >
          请先选择一个组件
        </div>
      </ElTabPane>

      <ElTabPane label="表单属性" name="form">
        <ElScrollbar class="h-full">
          <div class="p-4">
            <ElForm label-position="top" size="small">
              <ElFormItem label="标签对齐">
                <ElRadioGroup v-model="formConf.labelPosition">
                  <ElRadioButton label="left">左对齐</ElRadioButton>
                  <ElRadioButton label="right">右对齐</ElRadioButton>
                  <ElRadioButton label="top">顶部对齐</ElRadioButton>
                </ElRadioGroup>
              </ElFormItem>

              <ElFormItem label="标签宽度">
                <ElInputNumber
                  v-model="formConf.labelWidth"
                  :min="0"
                  :step="10"
                />
              </ElFormItem>

              <ElFormItem label="组件尺寸">
                <ElSelect v-model="formConf.size">
                  <ElOption label="默认" value="default" />
                  <ElOption label="大型" value="large" />
                  <ElOption label="小型" value="small" />
                </ElSelect>
              </ElFormItem>
            </ElForm>
          </div>
        </ElScrollbar>
      </ElTabPane>
    </ElTabs>

    <!-- 数据源编辑器弹窗 -->
    <OptionsEditor
      v-if="activeItem"
      v-model="showOptionsEditor"
      :data="activeItem.options || []"
      @confirm="handleOptionsConfirm"
    />
  </div>
</template>

<style scoped>
:deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}
</style>
