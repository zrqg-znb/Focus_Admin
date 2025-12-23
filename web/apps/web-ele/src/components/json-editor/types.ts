/**
 * JSON Editor Props and Types
 */
export interface JsonEditorProps {
  /**
   * JSON 字符串或对象
   */
  modelValue?: string | Record<string, any>;

  /**
   * 是否只读
   * @default false
   */
  readonly?: boolean;

  /**
   * 是否禁用
   * @default false
   */
  disabled?: boolean;

  /**
   * 编辑器模式: 'full' 或 'simple'
   * - full: 完整功能的 JSON 编辑器（有工具栏、行号、页脚等）
   * - simple: 简洁模式，外观类似 ElInput，仅有彩色高亮
   * @default 'full'
   */
  mode?: 'full' | 'simple';

  /**
   * 缩进空格数
   * @default 2
   */
  indent?: number;

  /**
   * 占位符文本
   * @default 使用 i18n 的 'jsonEditor.placeholder'
   */
  placeholder?: string;

  /**
   * 是否启用行号
   * @default true
   */
  lineNumbers?: boolean;

  /**
   * 最小高度（像素）
   * @default 200
   */
  minHeight?: number;

  /**
   * 最大高度（像素）
   * @default 600
   */
  maxHeight?: number;

  /**
   * 是否启用自动格式化
   * @default true
   */
  autoFormat?: boolean;

  /**
   * 是否启用语法高亮
   * @default true
   */
  highlightSyntax?: boolean;

  /**
   * 是否显示格式化按钮
   * @default true
   */
  showFormatButton?: boolean;

  /**
   * 是否显示校验结果
   * @default true
   */
  showValidation?: boolean;
}

export interface JsonEditorEmits {
  /**
   * 当内容变化时触发
   */
  'update:modelValue': [value: string];

  /**
   * 当内容变化时触发
   */
  change: [value: string];

  /**
   * 当 JSON 有效时触发
   */
  valid: [];

  /**
   * 当 JSON 无效时触发
   */
  invalid: [error: string];
}

export interface JsonValidationResult {
  valid: boolean;
  error?: string;
}

