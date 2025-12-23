<script lang="ts" setup>
import { computed, ref, watch, onMounted } from 'vue';
import { ElButton, ElTooltip, ElMessage } from 'element-plus';
import { $t } from '@vben/locales';
import type { JsonEditorProps, JsonEditorEmits, JsonValidationResult } from './types';

defineOptions({
  name: 'JsonEditor',
  inheritAttrs: false,
});

interface Props extends JsonEditorProps {}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  disabled: false,
  mode: 'simple',
  indent: 4,
  placeholder: () => '输入或粘贴 JSON',
  lineNumbers: true,
  minHeight: 400,
  maxHeight: 500,
  autoFormat: true,
  highlightSyntax: true,
  showFormatButton: true,
  showValidation: true,
});

const emit = defineEmits<JsonEditorEmits>();

// 编辑器内容
const content = ref('');
const textareaRef = ref<HTMLTextAreaElement>();
const lineNumbersRef = ref<HTMLDivElement>();

// 验证结果
const validationResult = ref<JsonValidationResult>({ valid: true });
const isFormatting = ref(false);

// 初始化内容
onMounted(() => {
  if (props.modelValue) {
    const initialValue = typeof props.modelValue === 'string' 
      ? props.modelValue 
      : JSON.stringify(props.modelValue, null, props.indent);
    content.value = initialValue;
    validateJson(initialValue);
  }
  syncLineNumbers();
});

// 监听 modelValue 变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== undefined) {
    const stringValue = typeof newValue === 'string' 
      ? newValue 
      : JSON.stringify(newValue, null, props.indent);
    if (stringValue !== content.value) {
      content.value = stringValue;
      validateJson(stringValue);
      syncLineNumbers();
    }
  }
});

/**
 * 验证 JSON 的有效性
 */
function validateJson(jsonString: string): JsonValidationResult {
  try {
    if (!jsonString.trim()) {
      validationResult.value = { valid: true };
      return { valid: true };
    }
    JSON.parse(jsonString);
    validationResult.value = { valid: true };
    emit('valid');
    return { valid: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '格式错误';
    validationResult.value = { valid: false, error: errorMessage };
    emit('invalid', errorMessage);
    return { valid: false, error: errorMessage };
  }
}

/**
 * 格式化 JSON
 */
function formatJson() {
  if (!content.value.trim()) {
    ElMessage.warning($t('common.jsonEditor.emptyContent'));
    return;
  }

  try {
    isFormatting.value = true;
    const parsed = JSON.parse(content.value);
    const formatted = JSON.stringify(parsed, null, props.indent);
    content.value = formatted;
    validateJson(formatted);
    syncLineNumbers();
    ElMessage.success($t('common.jsonEditor.formatSuccess'));
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : $t('common.jsonEditor.invalidJson');
    ElMessage.error($t('common.jsonEditor.formatFailed', [errorMessage]));
  } finally {
    isFormatting.value = false;
  }
}

/**
 * 压缩 JSON
 */
function compressJson() {
  if (!content.value.trim()) {
    ElMessage.warning($t('common.jsonEditor.emptyContent'));
    return;
  }

  try {
    const parsed = JSON.parse(content.value);
    const compressed = JSON.stringify(parsed);
    content.value = compressed;
    validateJson(compressed);
    syncLineNumbers();
    ElMessage.success($t('common.jsonEditor.compressSuccess'));
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : $t('common.jsonEditor.invalidJson');
    ElMessage.error($t('common.jsonEditor.compressFailed', [errorMessage]));
  }
}

/**
 * 复制到剪贴板
 */
function copyToClipboard() {
  if (!content.value) {
    ElMessage.warning($t('common.jsonEditor.noContent'));
    return;
  }

  navigator.clipboard.writeText(content.value).then(() => {
    ElMessage.success($t('common.jsonEditor.copiedSuccess'));
  }).catch(() => {
    ElMessage.error($t('common.jsonEditor.copyFailed'));
  });
}

/**
 * 清空内容
 */
function clearContent() {
  content.value = '';
  validationResult.value = { valid: true };
  emit('update:modelValue', '');
  emit('change', '');
}

/**
 * 同步行号
 */
function syncLineNumbers() {
  if (!lineNumbersRef.value || !textareaRef.value) return;
  
  const lines = content.value.split('\n').length;
  const lineNumbersHtml = Array.from({ length: lines }, (_, i) => i + 1).join('<br>');
  lineNumbersRef.value.innerHTML = lineNumbersHtml;
}

/**
 * 处理输入事件
 */
function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  content.value = target.value;
  syncLineNumbers();
  validateJson(content.value);
  emit('update:modelValue', content.value);
  emit('change', content.value);
}

/**
 * 处理滚动事件
 */
function handleScroll(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  if (lineNumbersRef.value) {
    lineNumbersRef.value.scrollTop = target.scrollTop;
    lineNumbersRef.value.scrollLeft = target.scrollLeft;
  }
}

/**
 * 处理按键事件
 */
function handleKeydown(event: KeyboardEvent) {
  // Ctrl/Cmd + Shift + F 格式化
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'F') {
    event.preventDefault();
    formatJson();
  }
}

/**
 * 获取行号容器样式
 */
const lineNumbersStyle = computed(() => ({
  minHeight: `${props.minHeight}px`,
  maxHeight: `${props.maxHeight}px`,
}));

/**
 * 获取编辑器容器样式
 */
const editorStyle = computed(() => ({
  minHeight: `${props.minHeight}px`,
  maxHeight: `${props.maxHeight}px`,
}));

/**
 * 获取验证状态类
 */
const validationClass = computed(() => {
  if (!props.showValidation) return '';
  return validationResult.value.valid ? 'is-valid' : 'is-invalid';
});

/**
 * 获取验证错误信息
 */
const errorMessage = computed(() => {
  return validationResult.value.error || '';
});

// 暴露方法
defineExpose({
  formatJson,
  compressJson,
  copyToClipboard,
  clearContent,
  validateJson,
  getContent: () => content.value,
  getParsedJson: () => JSON.parse(content.value),
});
</script>

<template>
  <!-- 简洁模式 -->
  <div v-if="mode === 'simple'" class="json-editor-simple" :class="{ 'is-disabled': disabled, 'is-readonly': readonly }">
    <div class="json-editor-simple-wrapper">
      <textarea
        ref="textareaRef"
        class="json-textarea-simple"
        :value="content"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        spellcheck="false"
        @input="handleInput"
        @keydown="handleKeydown"
      />
      <pre v-if="highlightSyntax" class="json-highlight-simple" aria-hidden="true"><code v-html="highlightJsonSyntax(content)" /></pre>
    </div>
  </div>

  <!-- 完整模式 -->
  <div v-else class="json-editor" :class="[validationClass, { 'is-readonly': readonly, 'is-disabled': disabled }]">
    <!-- 工具栏 -->
    <div class="json-editor-toolbar">
      <div class="toolbar-left">
        <span v-if="showValidation" class="status-indicator" :class="{ 'is-valid': validationResult.valid }">
          {{ validationResult.valid ? $t('common.jsonEditor.valid') : $t('common.jsonEditor.invalid') }}
        </span>
        <span v-if="!validationResult.valid && errorMessage" class="error-message">
          {{ errorMessage }}
        </span>
      </div>

      <div class="toolbar-right">
        <ElTooltip :content="`${$t('common.jsonEditor.format')} (Ctrl+Shift+F)`">
          <ElButton
            v-if="showFormatButton"
            link
            type="primary"
            size="small"
            :disabled="disabled || readonly || isFormatting"
            @click="formatJson"
          >
            {{ $t('common.jsonEditor.format') }}
          </ElButton>
        </ElTooltip>

        <ElTooltip :content="$t('common.jsonEditor.compress')">
          <ElButton
            link
            type="primary"
            size="small"
            :disabled="disabled || readonly"
            @click="compressJson"
          >
            {{ $t('common.jsonEditor.compress') }}
          </ElButton>
        </ElTooltip>

        <ElTooltip :content="$t('common.jsonEditor.copy')">
          <ElButton
            link
            type="primary"
            size="small"
            :disabled="disabled"
            @click="copyToClipboard"
          >
            {{ $t('common.jsonEditor.copy') }}
          </ElButton>
        </ElTooltip>

        <ElTooltip :content="$t('common.jsonEditor.clear')">
          <ElButton
            link
            type="danger"
            size="small"
            :disabled="disabled || readonly"
            @click="clearContent"
          >
            {{ $t('common.jsonEditor.clear') }}
          </ElButton>
        </ElTooltip>
      </div>
    </div>

    <!-- 编辑器容器 -->
    <div class="json-editor-container" :style="editorStyle">
      <!-- 行号 -->
      <div
        v-if="lineNumbers"
        ref="lineNumbersRef"
        class="line-numbers"
        :style="lineNumbersStyle"
      />

      <!-- 文本区域 -->
      <textarea
        ref="textareaRef"
        class="json-textarea"
        :value="content"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        :style="editorStyle"
        spellcheck="false"
        @input="handleInput"
        @scroll="handleScroll"
        @keydown="handleKeydown"
      />

      <!-- 语法高亮层（仅用于视觉效果） -->
      <pre
        v-if="highlightSyntax"
        class="json-highlight"
        :style="editorStyle"
        aria-hidden="true"
      ><code v-html="highlightJsonSyntax(content)" /></pre>
    </div>

    <!-- 统计信息 -->
    <div v-if="showValidation" class="json-editor-footer">
      <span class="stats">
        {{ $t('common.jsonEditor.stats', [content.split('\n').length, content.length]) }}
      </span>
    </div>
  </div>
</template>

<script lang="ts">
/**
 * JSON 语法高亮函数
 */
function highlightJsonSyntax(text: string): string {
  if (!text) return '';

  return text
    // 转义 HTML 特殊字符
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 高亮字符串
    .replace(/("(?:\\.|[^"\\])*"(?=\s*[,:}\]]))/g, '<span class="json-string">$1</span>')
    // 高亮数字
    .replace(/(?<=[:\[\s,])(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)\b/g, '<span class="json-number">$1</span>')
    // 高亮布尔值
    .replace(/\b(true|false)\b/g, '<span class="json-boolean">$1</span>')
    // 高亮 null
    .replace(/\bnull\b/g, '<span class="json-null">$1</span>')
    // 高亮冒号和逗号
    .replace(/([:])/g, '<span class="json-colon">$1</span>')
    .replace(/([,])/g, '<span class="json-comma">$1</span>')
    // 高亮括号
    .replace(/([{}[\]])/g, '<span class="json-bracket">$1</span>');
}
</script>

<style lang="scss" scoped>
.json-editor {
  width: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  background-color: hsl(var(--background));
  overflow: hidden;
  transition: all 0.2s ease;

  &.is-invalid {
    border-color: hsl(var(--destructive));

    .json-textarea,
    .json-highlight {
      border-color: hsl(var(--destructive));
    }
  }

  &.is-valid {
    border-color: hsl(var(--primary));
  }

  &.is-readonly {
    background-color: hsl(var(--background-deep) / 0.5);
  }

  &.is-disabled {
    opacity: 0.6;
    cursor: not-allowed;

    .json-textarea {
      cursor: not-allowed;
    }
  }
}

.json-editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(90deg, hsl(var(--background)) 0%, hsl(var(--background-deep) / 0.3) 100%);
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
  gap: 12px;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;

    :deep(.el-button) {
      font-size: 12px;
      padding: 4px 8px;
    }
  }

  .status-indicator {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 4px;
    background-color: hsl(var(--background-deep));
    color: hsl(var(--muted-foreground));
    white-space: nowrap;
    transition: all 0.2s ease;

    &.is-valid {
      color: hsl(var(--primary));
      background-color: hsl(var(--primary) / 0.1);
    }
  }

  .error-message {
    font-size: 12px;
    color: hsl(var(--destructive));
    margin-left: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.json-editor-container {
  position: relative;
  display: flex;
  overflow: hidden;
  flex: 1;
  border-bottom: 1px solid hsl(var(--border));
}

.line-numbers {
  position: relative;
  background-color: hsl(var(--background-deep) / 0.5);
  border-right: 1px solid hsl(var(--border));
  padding: 8px 12px;
  text-align: right;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: hsl(var(--muted-foreground));
  user-select: none;
  overflow: hidden;
  flex-shrink: 0;
  width: 50px;

  br {
    display: block;
    height: 1.6em;
  }
}

.json-textarea {
  flex: 1;
  padding: 8px 12px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  border: none;
  outline: none;
  resize: none;
  background-color: transparent;
  color: hsl(var(--foreground));
  caret-color: hsl(var(--primary));
  tab-size: 2;
  -moz-tab-size: 2;
  word-wrap: break-word;
  white-space: pre;

  &::placeholder {
    color: hsl(var(--muted-foreground) / 0.5);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  &:read-only {
    cursor: default;
  }
}

.json-highlight {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 8px 12px;
  border: none;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: transparent;
  background-color: transparent;
  overflow: hidden;
  pointer-events: none;
  tab-size: 2;
  -moz-tab-size: 2;
  word-wrap: break-word;
  white-space: pre;

  code {
    color: transparent;
    display: block;
  }

  :deep(.json-string) {
    color: hsl(var(--primary));
  }

  :deep(.json-number) {
    color: hsl(var(--accent));
  }

  :deep(.json-boolean) {
    color: hsl(var(--chart-2));
  }

  :deep(.json-null) {
    color: hsl(var(--muted-foreground));
    font-weight: 600;
  }

  :deep(.json-colon) {
    color: hsl(var(--foreground));
  }

  :deep(.json-comma) {
    color: hsl(var(--foreground));
  }

  :deep(.json-bracket) {
    color: hsl(var(--muted-foreground));
    font-weight: 600;
  }
}

.json-editor-footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px;
  background-color: hsl(var(--background-deep) / 0.3);
  border-top: 1px solid hsl(var(--border));
  flex-shrink: 0;

  .stats {
    font-size: 12px;
    color: hsl(var(--muted-foreground));
  }
}

/* ============= 简洁模式样式 ============= */
.json-editor-simple {
  position: relative;
  width: 100%;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  background-color: hsl(var(--background));
  transition: all 0.2s ease;

  &:hover {
    border-color: hsl(var(--primary) / 0.5);
  }

  &:focus-within {
    border-color: hsl(var(--primary));
    box-shadow: 0 0 0 2px hsl(var(--primary) / 0.1);
  }

  &.is-readonly {
    background-color: hsl(var(--background-deep) / 0.5);
    cursor: default;
  }

  &.is-disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background-color: hsl(var(--background-deep));
  }
}

.json-editor-simple-wrapper {
  position: relative;
  width: 100%;
  min-height: 40px;
  overflow: hidden;
}

.json-textarea-simple {
  position: relative;
  z-index: 2;
  width: 100%;
  padding: 8px 12px;
  border: none;
  outline: none;
  resize: none;
  background-color: transparent;
  color: hsl(var(--foreground));
  caret-color: hsl(var(--primary));
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  tab-size: 2;
  -moz-tab-size: 2;
  word-wrap: break-word;
  white-space: pre-wrap;
  word-break: break-all;

  &::placeholder {
    color: hsl(var(--muted-foreground) / 0.5);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  &:read-only {
    cursor: default;
  }
}

.json-highlight-simple {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  margin: 0;
  padding: 8px 12px;
  border: none;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  color: transparent;
  background-color: transparent;
  overflow: hidden;
  pointer-events: none;
  tab-size: 2;
  -moz-tab-size: 2;
  word-wrap: break-word;
  white-space: pre-wrap;
  word-break: break-all;

  code {
    color: transparent;
    display: inline;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  :deep(.json-string) {
    color: hsl(var(--primary));
  }

  :deep(.json-number) {
    color: hsl(var(--accent));
  }

  :deep(.json-boolean) {
    color: hsl(var(--chart-2));
  }

  :deep(.json-null) {
    color: hsl(var(--muted-foreground));
    font-weight: 600;
  }

  :deep(.json-colon) {
    color: hsl(var(--foreground));
  }

  :deep(.json-comma) {
    color: hsl(var(--foreground));
  }

  :deep(.json-bracket) {
    color: hsl(var(--muted-foreground));
    font-weight: 600;
  }
}
</style>

