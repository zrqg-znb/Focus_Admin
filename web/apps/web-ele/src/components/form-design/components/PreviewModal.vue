<template>
  <el-dialog
    v-model="visible"
    title="表单预览"
    width="800px"
    destroy-on-close
    append-to-body
  >
    <el-form
      ref="formRef"
      :model="formData"
      :label-width="conf.labelWidth + 'px'"
      :label-position="conf.labelPosition"
      :size="conf.size"
    >
      <PreviewItem 
        v-for="item in conf.items" 
        :key="item.id" 
        :item="item" 
        :model-value="formData"
      />
    </el-form>

    <div class="bg-gray-50 p-4 rounded mt-4">
      <div class="text-sm font-bold mb-2 text-gray-600">实时数据 (v-model):</div>
      <pre class="text-xs text-gray-500 overflow-auto">{{ formData }}</pre>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">验证提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import { 
  ElDialog, 
  ElForm, 
  ElButton, 
  ElMessage
} from 'element-plus';
import PreviewItem from './PreviewItem.vue';

const props = defineProps<{
  conf: any;
}>();

const visible = ref(false);
const formData = reactive<any>({});
const formRef = ref();

// 递归初始化数据
function initFormData(items: any[]) {
  items.forEach((item: any) => {
    if (item.type === 'grid') {
      item.columns.forEach((col: any) => {
        initFormData(col.children);
      });
    } else {
      // 初始化数据
      if (item.type === 'checkbox') {
         formData[item.field] = [];
      } else if (['input-number', 'slider', 'rate'].includes(item.type)) {
         formData[item.field] = 0;
      } else if (item.type === 'switch') {
         formData[item.field] = false;
      } else if (item.type === 'sub-table') {
         formData[item.field] = [];
         // 处理最小行数
         const min = item.props.minRows || 0;
         if (min > 0) {
           for (let i = 0; i < min; i++) {
             const newRow: any = { _id: `${Date.now()}_${Math.random()}` };
             if (item.children) {
               item.children.forEach((col: any) => {
                 newRow[col.field] = null;
               });
             }
             formData[item.field].push(newRow);
           }
         }
      } else {
         formData[item.field] = null;
      }
    }
  });
}

// 初始化数据
watch(() => props.conf, (newConf) => {
  if (!newConf || !newConf.items) return;
  
  // 重置
  for (const key in formData) delete formData[key];
  
  initFormData(newConf.items);
}, { deep: true });

const open = () => {
  visible.value = true;
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
    ElMessage.success('验证通过，数据已打印在控制台');
    console.log('表单提交数据:', formData);
  } catch (e) {
    ElMessage.error('表单验证失败');
  }
};

defineExpose({ open });
</script>
