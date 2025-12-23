<template>
  <el-dialog
    v-model="visible"
    title="生成代码"
    width="800px"
    append-to-body
    destroy-on-close
  >
    <div class="relative">
      <el-input
        v-model="code"
        type="textarea"
        :rows="20"
        readonly
        class="font-mono text-xs"
      />
      <el-button 
        type="primary" 
        size="small" 
        class="absolute top-2 right-2" 
        @click="handleCopy"
      >
        复制
      </el-button>
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElDialog, ElInput, ElButton, ElMessage } from 'element-plus';

const visible = ref(false);
const code = ref('');

const open = (formConf: any) => {
  code.value = generateVueCode(formConf);
  visible.value = true;
};

const handleCopy = () => {
  navigator.clipboard.writeText(code.value);
  ElMessage.success('代码已复制到剪贴板');
};

// 代码生成逻辑
function generateVueCode(conf: any) {
  const { template, script } = generateParts(conf);
  
  return `<template>
  <div class="form-container p-4">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="${conf.labelWidth}px"
      label-position="${conf.labelPosition}"
      size="${conf.size}"
    >
${template}
      <el-form-item>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';

${script}
<\/script>
`;
}

function generateParts(conf: any) {
  let template = '';
  const fields: string[] = [];
  const rules: string[] = [];
  
  // 递归生成模板
  function traverse(items: any[], indent = 6) {
    let html = '';
    const space = ' '.repeat(indent);
    
    items.forEach(item => {
      // 生成显隐控制
      let vIf = '';
      if (item.showCondition) {
        // 替换 model. 为 formData.
        const condition = item.showCondition.replace(/model\./g, 'formData.');
        vIf = ` v-if="${condition}"`;
      }
      
      if (item.type === 'grid') {
        html += `${space}<el-row :gutter="${item.props.gutter}"${vIf}>\n`;
        item.columns.forEach((col: any) => {
          html += `${space}  <el-col :span="${col.span}">\n`;
          html += traverse(col.children, indent + 4);
          html += `${space}  </el-col>\n`;
        });
        html += `${space}</el-row>\n`;
      } else if (item.type === 'divider') {
        // 分割线
        const props = Object.entries(item.props)
          .map(([key, val]) => {
             if (val === 'solid' || val === 'horizontal' || val === 'center') return ''; // 默认值不输出
             return `${key}="${val}"`;
          })
          .filter(Boolean)
          .join(' ');
          
        const content = item.label !== '分割线' ? item.label : '';
        if (content) {
          html += `${space}<el-divider ${props}${vIf}>${content}</el-divider>\n`;
        } else {
          html += `${space}<el-divider ${props}${vIf} />\n`;
        }
      } else if (item.type === 'collapse') {
        // 折叠面板
        const accordion = item.props.accordion ? ' accordion' : '';
        html += `${space}<el-collapse model-value="1"${accordion}${vIf}>\n`;
        item.items.forEach((subItem: any) => {
          html += `${space}  <el-collapse-item title="${subItem.title}" name="${subItem.name}">\n`;
          html += traverse(subItem.children, indent + 4);
          html += `${space}  </el-collapse-item>\n`;
        });
        html += `${space}</el-collapse>\n`;
      } else if (item.type === 'tabs') {
        // 标签页
        const type = item.props.type ? ` type="${item.props.type}"` : '';
        const tabPosition = item.props.tabPosition !== 'top' ? ` tab-position="${item.props.tabPosition}"` : '';
        html += `${space}<el-tabs model-value="1"${type}${tabPosition}${vIf}>\n`;
        item.items.forEach((subItem: any) => {
          html += `${space}  <el-tab-pane label="${subItem.label}" name="${subItem.name}">\n`;
          html += traverse(subItem.children, indent + 4);
          html += `${space}  </el-tab-pane>\n`;
        });
        html += `${space}</el-tabs>\n`;
      } else {
        // 收集字段和规则
        const defaultVal = getItemDefaultValue(item);
        fields.push(`${item.field}: ${JSON.stringify(defaultVal)}`);
        
        const itemRules = [];
        if (item.props.required) {
          const trigger = ['input', 'textarea', 'input-number'].includes(item.type) ? 'blur' : 'change';
          itemRules.push(`{ required: true, message: '${item.label}不能为空', trigger: '${trigger}' }`);
        }
        
        if (item.regList && item.regList.length > 0) {
          item.regList.forEach((reg: any) => {
            if (reg.pattern && reg.message) {
              // 直接使用用户输入的正则字符串，假设用户输入的是合法的正则字面量或字符串
              // 如果是字符串形式 "/^...$/"，我们直接作为正则字面量输出
              // 简单判断：如果是以 / 开头和结尾，视为字面量，否则作为字符串处理（不太常见）
              // 为了保险，我们假设用户输入的是如 "/^...$/" 格式
              itemRules.push(`{ pattern: ${reg.pattern}, message: '${reg.message}', trigger: 'blur' }`);
            }
          });
        }
        
        if (itemRules.length > 0) {
          rules.push(`${item.field}: [${itemRules.join(', ')}]`);
        }
        
        // 生成组件 HTML
        // 将 v-if 加在 el-form-item 上
        html += `${space}<el-form-item label="${item.label}" prop="${item.field}"${vIf}>\n`;
        html += `${space}  ${generateComponentTag(item)}\n`;
        html += `${space}</el-form-item>\n`;
      }
    });
    return html;
  }
  
  template = traverse(conf.items);
  
  // 生成 script
  const script = `
const formRef = ref();
const formData = reactive({
  ${fields.join(',\n  ')}
});

const rules = reactive({
  ${rules.join(',\n  ')}
});

const handleSubmit = async () => {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
    console.log('submit!', formData);
    ElMessage.success('提交成功');
  } catch (error) {
    console.log('error submit!', error);
  }
};

const handleReset = () => {
  if (!formRef.value) return;
  formRef.value.resetFields();
};
`;

  return { template, script };
}

function getItemDefaultValue(item: any) {
  if (item.type === 'checkbox') return [];
  if (['input-number', 'slider', 'rate'].includes(item.type)) return 0;
  if (item.type === 'switch') return false;
  return null;
}

function generateComponentTag(item: any) {
  // 默认值为 true 的属性列表，如果值为 false 需要显式输出
  const defaultsTrue = ['editable', 'controls'];
  
  const props = Object.entries(item.props)
    .filter(([key, val]) => {
      if (key === 'required') return false; // 已处理
      if (val === null || val === undefined) return false;
      if (val === '' && key !== 'activeText' && key !== 'inactiveText') return false; // 空字符串通常不输出，除了开关文案
      
      // 如果值是 false，且默认不是 true，则忽略（即默认 false 的属性不输出）
      if (val === false && !defaultsTrue.includes(key)) return false;
      
      // 如果值是 true，且默认是 true，则忽略（即默认 true 的属性不输出）
      if (val === true && defaultsTrue.includes(key)) return false;
      
      return true;
    })
    .map(([key, val]) => {
       if (val === true) return key;
       if (val === false) return `:${key}="false"`;
       if (typeof val === 'string') return `${key}="${val}"`;
       return `:${key}="${val}"`;
    })
    .join(' ');
    
  const tagMap: Record<string, string> = {
    input: 'el-input',
    textarea: 'el-input',
    select: 'el-select',
    radio: 'el-radio-group',
    checkbox: 'el-checkbox-group',
    date: 'el-date-picker',
    'input-number': 'el-input-number',
    time: 'el-time-picker',
    switch: 'el-switch',
    slider: 'el-slider',
    rate: 'el-rate',
    color: 'el-color-picker'
  };
  
  const tagName = tagMap[item.type] || 'el-input';
  let content = '';
  let extraProps = '';
  
  if (item.type === 'textarea') {
    extraProps = ' type="textarea"';
  }
  
  // 处理选项子组件
  if (['select', 'radio', 'checkbox'].includes(item.type) && item.options) {
    if (item.type === 'select') {
      content = `\n        ${item.options.map((opt: any) => 
        `<el-option label="${opt.label}" :value="${typeof opt.value === 'string' ? `'${opt.value}'` : opt.value}" />`
      ).join('\n        ')}\n      `;
    } else if (item.type === 'radio') {
      content = `\n        ${item.options.map((opt: any) => 
        `<el-radio :label="${typeof opt.value === 'string' ? `'${opt.value}'` : opt.value}">${opt.label}</el-radio>`
      ).join('\n        ')}\n      `;
    } else if (item.type === 'checkbox') {
      content = `\n        ${item.options.map((opt: any) => 
        `<el-checkbox :label="${typeof opt.value === 'string' ? `'${opt.value}'` : opt.value}">${opt.label}</el-checkbox>`
      ).join('\n        ')}\n      `;
    }
  }
  
  if (content) {
    return `<${tagName} v-model="formData.${item.field}" ${props}${extraProps}>${content}</${tagName}>`;
  } else {
    return `<${tagName} v-model="formData.${item.field}" ${props}${extraProps} />`;
  }
}

defineExpose({ open });
</script>
