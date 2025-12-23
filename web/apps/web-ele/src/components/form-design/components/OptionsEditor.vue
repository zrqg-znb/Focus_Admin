<template>
  <el-dialog
    v-model="visible"
    title="数据源编辑"
    width="800px"
    :close-on-click-modal="false"
    append-to-body
  >
    <div class="flex h-[500px] border border-[var(--el-border-color)] rounded">
      <!-- 左侧树形结构 -->
      <div class="w-1/2 border-r border-[var(--el-border-color)] flex flex-col">
        <div class="p-2 border-b border-[var(--el-border-color-lighter)] flex gap-2">
          <el-button type="primary" size="small" @click="addRootNode">添加根节点</el-button>
          <el-button 
            size="small" 
            :disabled="!currentNode" 
            @click="addChildNode"
          >
            添加子节点
          </el-button>
          <el-button 
            type="danger" 
            size="small" 
            :disabled="!currentNode" 
            @click="removeNode"
          >
            删除
          </el-button>
        </div>
        <div class="flex-1 overflow-y-auto p-2">
          <el-tree
            ref="treeRef"
            :data="treeData"
            node-key="id"
            default-expand-all
            draggable
            :allow-drop="allowDrop"
            highlight-current
            :expand-on-click-node="false"
            @node-click="handleNodeClick"
          >
            <template #default="{ data }">
              <span class="custom-tree-node text-sm">
                <span>{{ data.label }}</span>
                <span class="text-[var(--el-text-color-secondary)] ml-2 text-xs" v-if="data.value">({{ data.value }})</span>
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧节点编辑 -->
      <div class="w-1/2 flex flex-col bg-[var(--el-fill-color-light)]">
        <div class="p-4" v-if="currentNode">
          <div class="font-bold text-[var(--el-text-color-primary)] mb-4 border-b pb-2">节点属性</div>
          <el-form label-position="top" size="small">
            <el-form-item label="显示文本 (Label)">
              <el-input v-model="currentNode.label" placeholder="请输入" />
            </el-form-item>
            <el-form-item label="绑定值 (Value)">
              <el-input v-model="currentNode.value" placeholder="请输入" />
            </el-form-item>
          </el-form>
        </div>
        <div v-else class="flex-1 flex items-center justify-center text-[var(--el-text-color-placeholder)] text-sm">
          请在左侧选择一个节点进行编辑
        </div>
      </div>
    </div>
    
    <div class="mt-4">
      <el-collapse>
        <el-collapse-item title="查看 JSON 数据" name="json">
          <el-input
            :model-value="JSON.stringify(treeData, null, 2)"
            type="textarea"
            :rows="6"
            readonly
          />
        </el-collapse-item>
      </el-collapse>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirm">确定</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { 
  ElTree, 
  ElDialog, 
  ElButton, 
  ElForm, 
  ElFormItem, 
  ElInput, 
  ElCollapse, 
  ElCollapseItem 
} from 'element-plus';

const props = defineProps<{
  modelValue: boolean;
  data: any[];
}>();

const emit = defineEmits(['update:modelValue', 'confirm']);

const visible = ref(false);
const treeData = ref<any[]>([]);
const currentNode = ref<any>(null);
const treeRef = ref<InstanceType<typeof ElTree>>();

// 生成唯一ID，用于树组件追踪
const generateId = () => '_' + Math.random().toString(36).substr(2, 9);

// 递归处理数据，确保有 id 和 children
const processData = (items: any[]): any[] => {
  return items.map(item => ({
    ...item,
    id: item.id || generateId(),
    children: item.children ? processData(item.children) : []
  }));
};

// 递归清理数据，移除临时 id
const cleanData = (items: any[]): any[] => {
  return items.map(item => {
    const { id, ...rest } = item;
    const newItem: any = { ...rest };
    if (newItem.children && newItem.children.length > 0) {
      newItem.children = cleanData(newItem.children);
    } else {
      delete newItem.children;
    }
    return newItem;
  });
};

watch(() => props.modelValue, (val) => {
  visible.value = val;
  if (val) {
    // 深拷贝并处理数据
    treeData.value = processData(JSON.parse(JSON.stringify(props.data || [])));
    currentNode.value = null;
  }
});

watch(() => visible.value, (val) => {
  emit('update:modelValue', val);
});

const handleNodeClick = (data: any) => {
  currentNode.value = data;
};

const addRootNode = () => {
  const newNode = {
    id: generateId(),
    label: '新选项',
    value: 'new_option',
    children: []
  };
  treeData.value.push(newNode);
  currentNode.value = newNode;
  nextTick(() => {
    treeRef.value?.setCurrentKey(newNode.id);
  });
};

const addChildNode = () => {
  if (!currentNode.value) return;
  const newNode = {
    id: generateId(),
    label: '新子选项',
    value: 'new_child',
    children: []
  };
  if (!currentNode.value.children) {
    currentNode.value.children = [];
  }
  currentNode.value.children.push(newNode);
  // 自动展开父节点
  /* treeRef.value?.store.nodesMap[currentNode.value.id].expanded = true; */
};

const removeNode = () => {
  if (!currentNode.value) return;
  treeRef.value?.remove(currentNode.value);
  currentNode.value = null;
};

const allowDrop = () => {
  // 可以添加限制逻辑，目前允许任意拖拽
  return true;
};

const handleConfirm = () => {
  const result = cleanData(treeData.value);
  emit('confirm', result);
  visible.value = false;
};
</script>

<style scoped>
:deep(.el-tree-node__content) {
  height: 32px;
}
</style>
