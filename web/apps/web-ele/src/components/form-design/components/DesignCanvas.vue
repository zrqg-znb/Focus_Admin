<script setup lang="ts">
import { ref } from 'vue';

import {
  Back,
  Collection,
  Delete,
  Document,
  Download,
  Memo,
  Plus,
  ReadingLamp,
  Right,
  Upload,
} from '@element-plus/icons-vue';
import {
  ElButton,
  ElDialog,
  ElDivider,
  ElForm,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElScrollbar,
  ElTooltip,
} from 'element-plus';
import { storeToRefs } from 'pinia';
import draggable from 'vuedraggable';

import { useFormDesignStore } from '../store/formDesignStore';
import CodeModal from './CodeModal.vue';
import FormItemWrapper from './FormItemWrapper.vue';
import PreviewModal from './PreviewModal.vue';

const props = withDefaults(
  defineProps<{
    toolbars?: string[];
  }>(),
  {
    toolbars: () => [
      'undo',
      'redo',
      'import',
      'preview',
      'clear',
      'json',
      'saveTemplate',
    ],
  },
);

const store = useFormDesignStore();
const { formConf, activeId, isDragging } = storeToRefs(store);
const previewRef = ref();
const codeModalRef = ref();

const importVisible = ref(false);
const importJson = ref('');
const jsonVisible = ref(false);
const saveTemplateVisible = ref(false);
const templateName = ref('');

const handleSelect = (item: any) => store.setActive(item.id);
const handleDelete = (id: string) => store.deleteItem(id);
const handleCanvasClick = () => store.setActive(null);

const handleAdd = (evt: any) => {
  const newIndex = evt.newIndex;
  const newItem = formConf.value.items[newIndex];
  if (newItem) {
    store.setActive(newItem.id);
  }
};

const handleImport = () => {
  importJson.value = '';
  importVisible.value = true;
};

const handleViewJson = () => {
  jsonVisible.value = true;
};

const handleSaveTemplate = () => {
  if (formConf.value.items.length === 0) {
    ElMessage.warning('画布为空，无法保存为模板');
    return;
  }
  templateName.value = '';
  saveTemplateVisible.value = true;
};

const confirmSaveTemplate = () => {
  if (!templateName.value) {
    ElMessage.warning('请输入模板名称');
    return;
  }
  store.addTemplate({
    title: templateName.value,
    icon: 'Document',
    items: JSON.parse(JSON.stringify(formConf.value.items)),
  });
  saveTemplateVisible.value = false;
  ElMessage.success('保存模板成功');
};

const handleGenerateCode = () => {
  codeModalRef.value?.open(formConf.value);
};

const confirmImport = () => {
  try {
    const parsed = JSON.parse(importJson.value);
    if (typeof parsed !== 'object' || !parsed.items) {
      ElMessage.error('JSON 格式不正确，必须包含 items 数组');
      return;
    }
    // 简单的校验通过
    formConf.value = parsed;
    store.setActive(null);
    importVisible.value = false;
    ElMessage.success('导入成功');
  } catch {
    ElMessage.error('JSON 解析失败，请检查格式');
  }
};

const handleClear = () => {
  ElMessageBox.confirm('确定要清空所有组件吗？', '提示', {
    type: 'warning',
  }).then(() => {
    formConf.value.items = [];
    store.setActive(null);
  });
};

const handlePreview = () => {
  previewRef.value?.open();
};

const handleSave = () => {
  ElMessage.success('表单配置已打印到控制台');
};
</script>

<template>
  <div
    class="design-canvas flex h-full flex-col bg-[var(--el-fill-color-light)]"
  >
    <div
      class="canvas-toolbar flex items-center justify-between rounded border-b border-[var(--el-border-color)] bg-[var(--el-bg-color)] px-4 py-2"
    >
      <div class="flex items-center space-x-2">
        <ElTooltip
          content="撤销"
          placement="bottom"
          v-if="toolbars.includes('undo')"
        >
          <ElButton
            size="small"
            link
            :disabled="!store.canUndo"
            @click="store.undo"
          >
            <ElIcon :size="16"><Back /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="重做"
          placement="bottom"
          v-if="toolbars.includes('redo')"
        >
          <ElButton
            size="small"
            link
            :disabled="!store.canRedo"
            @click="store.redo"
          >
            <ElIcon :size="16"><Right /></ElIcon>
          </ElButton>
        </ElTooltip>
      </div>
      <div class="flex items-center space-x-1">
        <ElTooltip
          content="导入JSON"
          placement="bottom"
          v-if="toolbars.includes('import')"
        >
          <ElButton size="small" text @click="handleImport">
            <ElIcon :size="16"><Upload /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="查看JSON"
          placement="bottom"
          v-if="toolbars.includes('json')"
        >
          <ElButton size="small" text @click="handleViewJson">
            <ElIcon :size="16"><Memo /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="保存模板"
          placement="bottom"
          v-if="toolbars.includes('saveTemplate')"
        >
          <ElButton size="small" text @click="handleSaveTemplate">
            <ElIcon :size="16"><Collection /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="生成代码"
          placement="bottom"
          v-if="toolbars.includes('code')"
        >
          <ElButton size="small" text @click="handleGenerateCode">
            <ElIcon :size="16"><Document /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="预览"
          placement="bottom"
          v-if="toolbars.includes('preview')"
        >
          <ElButton size="small" text @click="handlePreview">
            <ElIcon :size="16"><ReadingLamp /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="保存"
          placement="bottom"
          v-if="toolbars.includes('save')"
        >
          <ElButton size="small" text @click="handleSave">
            <ElIcon :size="16"><Download /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip
          content="清空"
          placement="bottom"
          v-if="toolbars.includes('clear')"
        >
          <ElButton size="small" text @click="handleClear">
            <ElIcon :size="16"><Delete /></ElIcon>
          </ElButton>
        </ElTooltip>
      </div>
    </div>

    <ElScrollbar class="canvas-body flex-1" view-class="h-full">
      <div
        class="flex min-h-full justify-center"
        @click.self="handleCanvasClick"
      >
        <div
          class="canvas-wrapper min-h-full w-full rounded-b bg-[var(--el-bg-color)] p-8"
        >
          <ElForm
            :label-width="`${formConf.labelWidth}px`"
            :label-position="formConf.labelPosition"
            :size="formConf.size"
            class="relative h-full"
          >
            <draggable
              v-model="formConf.items"
              group="form-design"
              item-key="id"
              class="canvas-area h-full min-h-[200px]"
              ghost-class="ghost"
              :animation="200"
              @add="handleAdd"
            >
              <template #item="{ element }">
                <FormItemWrapper
                  :schema="element"
                  :active="activeId === element.id"
                  @click="handleSelect(element)"
                  @delete="handleDelete"
                />
              </template>
            </draggable>

            <div
              v-if="formConf.items.length === 0"
              class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
            >
              <div
                class="flex h-[300px] w-[300px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors duration-300"
                :class="[
                  isDragging
                    ? 'border-[var(--el-color-primary)] bg-[var(--el-color-primary-light-9)] text-[var(--el-color-primary)]'
                    : 'border-[var(--el-border-color)] text-[var(--el-text-color-placeholder)]',
                ]"
              >
                <ElIcon :size="40" class="mb-2"><Plus /></ElIcon>
                <span>{{
                  isDragging ? '松手添加组件' : '从左侧拖拽组件到此处'
                }}</span>
              </div>
            </div>
          </ElForm>
        </div>
      </div>
    </ElScrollbar>

    <!-- 预览弹窗 -->
    <PreviewModal ref="previewRef" :conf="formConf" />

    <!-- 代码生成弹窗 -->
    <CodeModal ref="codeModalRef" />

    <!-- 导入弹窗 -->
    <ElDialog
      v-model="importVisible"
      title="导入 JSON"
      width="600px"
      append-to-body
    >
      <div class="mb-2 text-xs text-gray-500">
        请粘贴标准的 JSON 表单配置。注意：导入将覆盖当前画布内容。
      </div>
      <ElInput
        v-model="importJson"
        type="textarea"
        :rows="10"
        placeholder="在此粘贴 JSON 配置..."
      />
      <template #footer>
        <ElButton @click="importVisible = false">取消</ElButton>
        <ElButton type="primary" @click="confirmImport">确定导入</ElButton>
      </template>
    </ElDialog>

    <!-- 查看 JSON 弹窗 -->
    <ElDialog
      v-model="jsonVisible"
      title="查看 JSON"
      width="600px"
      append-to-body
    >
      <ElInput
        :model-value="JSON.stringify(formConf, null, 2)"
        type="textarea"
        :rows="15"
        readonly
      />
      <template #footer>
        <ElButton type="primary" @click="jsonVisible = false">关闭</ElButton>
      </template>
    </ElDialog>

    <!-- 保存模板弹窗 -->
    <ElDialog
      v-model="saveTemplateVisible"
      title="保存为模板"
      width="400px"
      append-to-body
    >
      <div class="mb-2 text-xs text-gray-500">
        请输入模板名称，保存后可在左侧模板库中查看。
      </div>
      <ElInput
        v-model="templateName"
        placeholder="请输入模板名称"
        @keyup.enter="confirmSaveTemplate"
      />
      <template #footer>
        <ElButton @click="saveTemplateVisible = false">取消</ElButton>
        <ElButton type="primary" @click="confirmSaveTemplate">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
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
