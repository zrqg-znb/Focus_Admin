<script setup lang="ts">
import { ref } from 'vue';
import { 
  ElDialog, ElButton, ElTimeline, ElTimelineItem, 
  ElCard, ElForm, ElFormItem, ElInput, ElRadioGroup, 
  ElRadioButton, ElMessage 
} from 'element-plus';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@vben-core/shadcn-ui';
import { 
  getRiskLogsApi, 
  confirmRiskApi,
  type RiskItem,
  type RiskLog,
  type RiskConfirmPayload
} from '#/api/project-manager/milestone';
import { dayjs } from 'element-plus';

const visible = ref(false);
const loading = ref(false);
const submitting = ref(false);
const currentRisk = ref<RiskItem | null>(null);
const logs = ref<RiskLog[]>([]);
const activeTab = ref('handle');

const handleForm = ref<RiskConfirmPayload>({
  action: 'confirm',
  note: ''
});

const emit = defineEmits(['success']);

/**
 * 打开对话框
 * @param risk 风险项数据
 * @param mode 初始模式：'handle' (处理) 或 'logs' (记录)
 */
function open(risk: RiskItem, mode: 'handle' | 'logs' = 'handle') {
  currentRisk.value = risk;
  visible.value = true;
  // 如果风险已关闭，默认显示日志页
  activeTab.value = risk.status === 'closed' ? 'logs' : mode;
  handleForm.value = {
    action: 'confirm',
    note: ''
  };
  fetchLogs();
}

async function fetchLogs() {
  if (!currentRisk.value) return;
  loading.value = true;
  try {
    logs.value = await getRiskLogsApi(currentRisk.value.id);
  } finally {
    loading.value = false;
  }
}

async function submitHandle() {
  if (!handleForm.value.note) {
    ElMessage.warning('请输入处理备注');
    return;
  }
  
  if (!currentRisk.value) return;

  submitting.value = true;
  try {
    await confirmRiskApi(currentRisk.value.id, handleForm.value);
    ElMessage.success('操作成功');
    visible.value = false;
    emit('success');
  } finally {
    submitting.value = false;
  }
}

function formatTime(time: string) {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss');
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    title="风险处理与记录"
    width="600px"
    append-to-body
    destroy-on-close
  >
    <!-- 风险概览信息 -->
    <div v-if="currentRisk" class="mb-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded border border-gray-100 dark:border-gray-700">
      <div class="flex items-center gap-2 mb-2">
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
          {{ currentRisk.qg_name }}
        </span>
        <span class="text-xs text-gray-500">{{ currentRisk.record_date }}</span>
      </div>
      <div class="text-sm font-medium text-gray-700 dark:text-gray-200">
        {{ currentRisk.description }}
      </div>
    </div>

    <!-- Shadcn Tabs 切换 -->
    <Tabs v-model="activeTab" class="w-full">
      <TabsList class="grid w-full grid-cols-2">
        <TabsTrigger value="handle" :disabled="currentRisk?.status === 'closed'">
          风险处理
        </TabsTrigger>
        <TabsTrigger value="logs">
          处理记录
        </TabsTrigger>
      </TabsList>
      
      <!-- 处理表单内容 -->
      <TabsContent value="handle" class="pt-4">
        <ElForm :model="handleForm" label-position="top">
          <ElFormItem label="处理动作">
            <ElRadioGroup v-model="handleForm.action" class="w-full flex">
              <ElRadioButton label="confirm" class="flex-1">确认知晓 (保持风险)</ElRadioButton>
              <ElRadioButton label="close" class="flex-1">关闭风险 (已解决)</ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem label="处理备注" required>
            <ElInput
              v-model="handleForm.note"
              type="textarea"
              :rows="4"
              placeholder="请输入处理备注，说明当前进展或解决方案..."
            />
          </ElFormItem>
        </ElForm>
        <div class="mt-4 flex justify-end gap-2">
          <ElButton @click="visible = false">取消</ElButton>
          <ElButton type="primary" :loading="submitting" @click="submitHandle">提交处理</ElButton>
        </div>
      </TabsContent>

      <!-- 日志时间线内容 -->
      <TabsContent value="logs" class="pt-4">
        <div class="max-h-[400px] overflow-auto px-1">
          <ElTimeline v-if="logs.length > 0">
            <ElTimelineItem
              v-for="(log, index) in logs"
              :key="index"
              :timestamp="formatTime(log.create_time)"
              placement="top"
            >
              <ElCard shadow="never" class="!border-gray-100 dark:!border-gray-800">
                <div class="flex justify-between items-center mb-2">
                  <span class="font-bold text-sm">{{ log.operator_name }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                    {{ log.action }}
                  </span>
                </div>
                <div class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                  {{ log.note || '无备注' }}
                </div>
              </ElCard>
            </ElTimelineItem>
          </ElTimeline>
          <div v-else class="flex flex-col items-center justify-center py-10 text-gray-400">
            <div class="text-sm">暂无记录</div>
          </div>
        </div>
      </TabsContent>
    </Tabs>
  </ElDialog>
</template>
