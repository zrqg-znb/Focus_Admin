<template>
  <!-- 栅格布局渲染 -->
  <el-row v-if="item.type === 'grid' && visible" :gutter="item.props.gutter">
    <el-col
      v-for="(col, index) in item.columns"
      :key="index"
      :span="col.span"
    >
      <PreviewItem 
        v-for="child in col.children" 
        :key="child.id" 
        :item="child" 
        :model-value="modelValue"
      />
    </el-col>
  </el-row>

  <!-- 分割线 -->
  <div v-else-if="item.type === 'divider' && visible" class="py-2">
    <el-divider v-bind="item.props">
      {{ item.label !== '分割线' ? item.label : '' }}
    </el-divider>
  </div>

  <!-- 折叠面板 -->
  <div v-else-if="item.type === 'collapse' && visible" class="mb-4">
    <el-collapse v-bind="item.props" v-model="activeCollapse">
      <el-collapse-item 
        v-for="(subItem, index) in item.items" 
        :key="index" 
        :title="subItem.title" 
        :name="subItem.name"
      >
        <PreviewItem 
          v-for="child in subItem.children" 
          :key="child.id" 
          :item="child" 
          :model-value="modelValue"
        />
      </el-collapse-item>
    </el-collapse>
  </div>

  <!-- 标签页 -->
  <div v-else-if="item.type === 'tabs' && visible" class="mb-4">
    <el-tabs v-bind="item.props" v-model="activeTab">
      <el-tab-pane 
        v-for="(subItem, index) in item.items" 
        :key="index" 
        :label="subItem.label" 
        :name="subItem.name"
      >
        <PreviewItem 
          v-for="child in subItem.children" 
          :key="child.id" 
          :item="child" 
          :model-value="modelValue"
        />
      </el-tab-pane>
    </el-tabs>
  </div>

  <!-- 警告提示 -->
  <div v-else-if="item.type === 'alert' && visible" class="mb-4">
    <el-alert v-bind="item.props" />
  </div>

  <!-- 时间线 -->
  <div v-else-if="item.type === 'timeline' && visible" class="mb-4">
    <el-timeline v-bind="item.props">
      <el-timeline-item 
        v-for="(subItem, index) in item.items" 
        :key="index" 
        :timestamp="subItem.timestamp"
        :type="subItem.type"
        :icon="subItem.icon"
        :color="subItem.color"
      >
        {{ subItem.content }}
      </el-timeline-item>
    </el-timeline>
  </div>

  <!-- 子表单 -->
  <div v-else-if="item.type === 'sub-table' && visible" class="mb-4">
    <div class="mb-2 font-bold text-sm text-gray-700 flex justify-between items-center">
      <span>{{ item.label }}</span>
      <span v-if="item.props.maxRows" class="text-xs text-gray-400 font-normal">
        (最多 {{ item.props.maxRows }} 行)
      </span>
    </div>

    <!-- 表格模式 -->
    <template v-if="!item.props.displayMode || item.props.displayMode === 'table'">
      <el-table 
        :data="displayData" 
        border 
        style="width: 100%"
        :show-summary="item.props.summary"
      >
        <el-table-column type="index" width="50" v-if="item.props.showIndex" align="center">
          <template #default="scope">
            {{ getRealIndex(scope.$index) + 1 }}
          </template>
        </el-table-column>
        
        <el-table-column 
          v-for="col in item.children" 
          :key="col.field" 
          :label="col.label" 
          :width="col.props.columnWidth || col.props.width"
          :min-width="150"
          :align="col.props.columnAlign || 'left'"
          :fixed="col.props.columnFixed"
        >
          <template #default="scope">
             <PreviewItem 
               :item="col" 
               :model-value="scope.row"
             />
          </template>
        </el-table-column>
        
        <el-table-column 
          label="操作" 
          :width="item.props.sortable ? 160 : 100" 
          fixed="right" 
          align="center"
          v-if="item.props.deletable !== false || item.props.copyable || item.props.sortable"
        >
          <template #default="scope">
            <div class="flex items-center justify-center gap-2">
              <template v-if="item.props.sortable">
                <el-button 
                  circle 
                  size="small" 
                  :disabled="getRealIndex(scope.$index) === 0"
                  @click="moveRow(item.field, getRealIndex(scope.$index), -1)"
                >
                  <el-icon><Top /></el-icon>
                </el-button>
                <el-button 
                  circle 
                  size="small"
                  :disabled="getRealIndex(scope.$index) === (modelValue[item.field] || []).length - 1" 
                  @click="moveRow(item.field, getRealIndex(scope.$index), 1)"
                >
                  <el-icon><Bottom /></el-icon>
                </el-button>
              </template>
              
              <el-button 
                type="primary" 
                link 
                v-if="item.props.copyable"
                @click="copyRow(item, getRealIndex(scope.$index))"
              >
                复制
              </el-button>
              
              <el-button 
                type="danger" 
                link 
                v-if="item.props.deletable !== false"
                :disabled="(modelValue[item.field] || []).length <= (item.props.minRows || 0)"
                @click="removeRow(item.field, getRealIndex(scope.$index))"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 卡片模式 -->
    <template v-else-if="item.props.displayMode === 'card'">
      <div class="flex flex-col gap-4">
        <draggable
          :list="displayData"
          item-key="_id"
          handle=".drag-handle"
          :disabled="!item.props.sortable"
          :animation="200"
        >
          <template #item="{ element: row, index }">
            <div class="relative border rounded-lg p-4 bg-gray-50 mb-4 group hover:shadow-sm transition-shadow">
              <div class="flex justify-between items-center mb-4 border-b pb-2">
                <div class="flex items-center gap-2">
                  <el-icon 
                    v-if="item.props.sortable" 
                    class="drag-handle cursor-move text-gray-400 hover:text-blue-500"
                  >
                    <Rank />
                  </el-icon>
                  <span class="font-bold text-gray-600">#{{ getRealIndex(index) + 1 }}</span>
                </div>
                <div class="flex gap-2">
                  <el-button 
                    type="primary" 
                    link 
                    size="small"
                    v-if="item.props.copyable"
                    @click="copyRow(item, getRealIndex(index))"
                  >
                    复制
                  </el-button>
                  <el-button 
                    type="danger" 
                    link 
                    size="small"
                    v-if="item.props.deletable !== false"
                    :disabled="(modelValue[item.field] || []).length <= (item.props.minRows || 0)"
                    @click="removeRow(item.field, getRealIndex(index))"
                  >
                    删除
                  </el-button>
                </div>
              </div>
              
              <el-row :gutter="20">
                <el-col 
                  v-for="col in item.children" 
                  :key="col.field"
                  :span="24" 
                  class="mb-4 last:mb-0"
                >
                  <div class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">{{ col.label }}</span>
                    <PreviewItem 
                      :item="{ ...col, label: '' }" 
                      :model-value="row"
                    />
                  </div>
                </el-col>
              </el-row>
            </div>
          </template>
        </draggable>
      </div>
    </template>

    <!-- 行内模式 -->
    <template v-else-if="item.props.displayMode === 'inline'">
      <div class="flex flex-col gap-4">
         <draggable
          :list="displayData"
          item-key="_id"
          handle=".drag-handle"
          :disabled="!item.props.sortable"
          :animation="200"
        >
          <template #item="{ element: row, index }">
            <div class="flex items-center gap-4 p-4 border rounded-lg bg-white hover:shadow-sm transition-shadow mb-4 last:mb-0">
              <div 
                v-if="item.props.sortable" 
                class="drag-handle cursor-move text-gray-400 hover:text-blue-500 flex-shrink-0"
              >
                <el-icon size="16"><Rank /></el-icon>
              </div>
              <span v-if="item.props.showIndex" class="text-gray-500 w-8 text-center font-medium bg-gray-100 rounded-full h-6 flex items-center justify-center text-xs flex-shrink-0">{{ getRealIndex(index) + 1 }}</span>
              
              <div class="flex-1 grid gap-4 items-center" :style="{ gridTemplateColumns: `repeat(${item.children.length}, 1fr)` }">
                 <div 
                    v-for="col in item.children" 
                    :key="col.field"
                    class="min-w-0"
                 >
                   <div class="text-xs text-gray-500 mb-1 truncate" :title="col.label">{{ col.label }}</div>
                   <PreviewItem 
                      :item="{ ...col, label: '' }" 
                      :model-value="row"
                   />
                 </div>
              </div>

              <div class="flex gap-2 flex-shrink-0 ml-2" v-if="item.props.deletable !== false || item.props.copyable">
                 <el-button 
                    circle
                    size="small"
                    v-if="item.props.copyable"
                    @click="copyRow(item, getRealIndex(index))"
                    title="复制"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                  <el-button 
                    type="danger" 
                    circle
                    size="small"
                    v-if="item.props.deletable !== false"
                    :disabled="(modelValue[item.field] || []).length <= (item.props.minRows || 0)"
                    @click="removeRow(item.field, getRealIndex(index))"
                    title="删除"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
              </div>
            </div>
          </template>
        </draggable>
      </div>
    </template>
    
    <div class="mt-2 flex justify-between items-center" v-if="item.props.addable !== false || hasPagination">
      <div v-if="item.props.addable !== false && (!item.props.maxRows || (modelValue[item.field] || []).length < item.props.maxRows)">
        <el-button type="primary" plain size="small" @click="addRow(item)">
          <el-icon class="mr-1"><Plus /></el-icon>
          {{ item.props.addButtonText || '添加一行' }}
        </el-button>
      </div>
      <div v-else></div>

      <!-- 分页组件 -->
      <el-pagination
        v-if="hasPagination"
        v-model:current-page="currentPage"
        v-model:page-size="item.props.pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="(modelValue[item.field] || []).length"
        layout="total, sizes, prev, pager, next, jumper"
        background
        small
        @current-change="handleCurrentChange"
      />
    </div>
  </div>

  <!-- 普通组件渲染 -->
  <el-form-item 
    v-else-if="visible"
    :label="item.hideLabel ? undefined : item.label" 
    :label-width="item.hideLabel ? '0px' : undefined"
    :prop="item.field"
    :rules="getRules(item)"
  >
    <component
      :is="getComponentMap(item.type)"
      v-model="modelValue[item.field]"
      v-bind="item.props"
      :options="['cascader'].includes(item.type) ? item.options : undefined"
      :data="['tree-select'].includes(item.type) ? item.options : undefined"
      class="w-full"
    >
      <!-- 特殊处理选项 -->
      <template v-if="['select', 'radio', 'checkbox'].includes(item.type)">
        <template v-if="item.type === 'select'">
          <el-option 
            v-for="opt in item.options" 
            :key="opt.value" 
            :label="opt.label" 
            :value="opt.value" 
          />
        </template>
        
        <template v-else-if="item.type === 'radio'">
          <el-radio 
            v-for="opt in item.options" 
            :key="opt.value" 
            :label="opt.value"
          >
            {{ opt.label }}
          </el-radio>
        </template>
        
        <template v-else-if="item.type === 'checkbox'">
          <el-checkbox 
            v-for="opt in item.options" 
            :key="opt.value" 
            :label="opt.value"
          >
            {{ opt.label }}
          </el-checkbox>
        </template>
      </template>
    </component>
  </el-form-item>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue';
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
  ElTable,
  ElTableColumn,
  ElButton,
  ElIcon,
  ElPagination
} from 'element-plus';
import { 
  Plus, 
  Delete, 
  Top, 
  Bottom, 
  Rank,
  CopyDocument
} from '@element-plus/icons-vue';
import draggable from 'vuedraggable';

import DeptSelector from '../../zq-form/dept-selector/dept-selector.vue';
import UserSelector from '../../zq-form/user-selector/user-selector.vue';
import RoleSelector from '../../zq-form/role-selector/role-selector.vue';
import PostSelector from '../../zq-form/post-selector/post-selector.vue';
import CronSelector from '../../zq-form/cron-selector/cron-selector.vue';
import ImageSelector from '../../zq-form/image-selector/image-selector.vue';
import FileSelector from '../../zq-form/file-selector/file-selector.vue';

defineOptions({
  name: 'PreviewItem'
});

const props = defineProps<{
  item: any;
  modelValue: any;
}>();

// 分页逻辑
const currentPage = ref(1);
const pageSize = computed(() => props.item.props.pageSize || 10);
const hasPagination = computed(() => props.item.props.pagination && props.item.type === 'sub-table');

const displayData = computed({
  get: () => {
    const list = props.modelValue[props.item.field] || [];
    if (!hasPagination.value) return list;
    const start = (currentPage.value - 1) * pageSize.value;
    return list.slice(start, start + pageSize.value);
  },
  set: (val) => {
    if (!hasPagination.value) {
       props.modelValue[props.item.field] = val;
       return;
    }
    const list = [...(props.modelValue[props.item.field] || [])];
    const start = (currentPage.value - 1) * pageSize.value;
    list.splice(start, pageSize.value, ...val);
    props.modelValue[props.item.field] = list;
  }
});

const handleCurrentChange = (val: number) => {
  currentPage.value = val;
};

const getRealIndex = (index: number) => {
  if (!hasPagination.value) return index;
  return (currentPage.value - 1) * pageSize.value + index;
};

// 监听数据变化，修正当前页
watchEffect(() => {
    if (!hasPagination.value) return;
    const total = (props.modelValue[props.item.field] || []).length;
    const maxPage = Math.ceil(total / pageSize.value) || 1;
    if (currentPage.value > maxPage) {
        currentPage.value = maxPage;
    }
});

// 子表单操作
const addRow = (item: any) => {
  if (!props.modelValue[item.field]) {
    props.modelValue[item.field] = [];
  }
  // 初始化新行数据
  const newRow: any = { _id: `${Date.now()}_${Math.random()}` };
  if (item.children) {
    item.children.forEach((col: any) => {
      newRow[col.field] = null; // 或者根据类型设置默认值
    });
  }
  props.modelValue[item.field].push(newRow);
};

const removeRow = (field: string, index: number) => {
  if (props.modelValue[field]) {
    props.modelValue[field].splice(index, 1);
  }
};

const copyRow = (item: any, index: number) => {
  const list = props.modelValue[item.field];
  if (list && list[index]) {
    const clone = JSON.parse(JSON.stringify(list[index]));
    clone._id = `${Date.now()}_${Math.random()}`; // 确保唯一键
    list.splice(index + 1, 0, clone);
  }
};

const moveRow = (field: string, index: number, step: number) => {
  const list = props.modelValue[field];
  if (!list) return;
  
  const targetIndex = index + step;
  if (targetIndex >= 0 && targetIndex < list.length) {
    const temp = list[index];
    list[index] = list[targetIndex];
    list[targetIndex] = temp;
  }
};

// 状态管理
const activeCollapse = ref<any>([]);
const activeTab = ref<string>('');

watchEffect(() => {
  if (props.item.type === 'collapse' && props.item.items?.length) {
    if (props.item.props.accordion) {
      activeCollapse.value = props.item.items[0].name;
    } else {
      activeCollapse.value = props.item.items.map((i: any) => i.name);
    }
  } else if (props.item.type === 'tabs' && props.item.items?.length) {
    activeTab.value = props.item.items[0].name;
  }
});

const visible = computed(() => {
  if (!props.item.showCondition) return true;
  try {
    // 使用 new Function 执行表达式，提供 model 变量
    const func = new Function('model', `return ${props.item.showCondition}`);
    return func(props.modelValue);
  } catch (e) {
    console.warn(`Show condition error for field ${props.item.field}:`, e);
    return true;
  }
});

// 组件映射
const COMPONENT_MAP: Record<string, any> = {
  input: ElInput,
  textarea: ElInput,
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

function getRules(item: any) {
  const itemRules: any[] = [];
  
  // 必填校验
  if (item.props.required) {
    const trigger = ['input', 'textarea', 'input-number'].includes(item.type) ? 'blur' : 'change';
    itemRules.push({ required: true, message: `${item.label}不能为空`, trigger });
  }
  
  // 正则校验
  if (item.regList && item.regList.length > 0) {
    item.regList.forEach((reg: any) => {
      if (reg.pattern && reg.message) {
        try {
          // 解析正则字符串，例如 "/^...$/"
          const match = reg.pattern.match(/^\/(.+)\/([gim]*)$/);
          let regex;
          if (match) {
             regex = new RegExp(match[1], match[2]);
          } else {
             // 尝试直接创建（兼容不带斜杠的情况）
             regex = new RegExp(reg.pattern);
          }
          
          itemRules.push({ 
            pattern: regex, 
            message: reg.message, 
            trigger: 'blur' 
          });
        } catch (e) {
          console.error('Invalid regex:', reg.pattern);
        }
      }
    });
  }
  
  return itemRules;
}
</script>
