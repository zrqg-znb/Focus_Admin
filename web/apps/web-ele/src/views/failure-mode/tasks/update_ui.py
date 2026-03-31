import re
with open('/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-ele/src/views/failure-mode/tasks/detail.vue', 'r') as f:
    content = f.read()

# Remove the 'overview' tab entirely
content = re.sub(
    r'<ElTabPane label="概览" name="overview">[\s\S]*?</ElTabPane>',
    '',
    content
)

# We want to replace the top section with a more modern one.
# First, find the imports and add ElSteps, ElStep, ElIcon, ElTooltip if needed.
# Let's just use ElSteps, ElStep.
content = content.replace(
    '  ElTag,\n} from \'element-plus\';',
    '  ElTag,\n  ElSteps,\n  ElStep,\n  ElDivider,\n} from \'element-plus\';'
)

# Now, we will add a computed property for the steps
steps_computed = """
const activeStep = computed(() => {
  const status = currentTask.value?.status;
  if (status === 'CREATED') return 0;
  if (status === 'PROCESSING') return 1;
  if (status === 'REVIEWING') return 2;
  if (status === 'CLOSED') return 3;
  return 0;
});
"""

# Inject activeStep after activeTab
content = content.replace("const activeTab = ref('workbench');", "const activeTab = ref('workbench');\n" + steps_computed)

# Redesign the top container
top_container_pattern = r'<div class="rounded-xl bg-white p-5 shadow-sm">[\s\S]*?</ElDescriptions>\s*</div>'

modern_top = """<div class="rounded-xl bg-white p-6 shadow-sm">
        <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-4">
              <ElButton plain @click="handleBack" size="small">返回</ElButton>
              <span class="text-xl font-bold text-gray-900">
                {{ currentTask?.name || '任务详情' }}
              </span>
              <ElTag
                v-if="currentTask"
                :type="getTaskStatusTagType(currentTask.status)"
                effect="light"
                round
              >
                {{
                  FM_TASK_STATUS_LABEL_MAP[currentTask.status] ||
                  currentTask.status
                }}
              </ElTag>
            </div>
            
            <div class="grid grid-cols-2 md:grid-cols-3 gap-y-3 gap-x-8 text-sm text-gray-600 mb-6">
              <div class="flex items-center">
                <span class="text-gray-400 w-20">任务编号：</span>
                <span class="font-medium text-gray-900">{{ currentTask?.task_no || '-' }}</span>
              </div>
              <div class="flex items-center">
                <span class="text-gray-400 w-20">任务类型：</span>
                <span class="font-medium text-gray-900">{{ currentTask ? (FM_TASK_TYPE_LABEL_MAP[currentTask.task_type] || currentTask.task_type) : '-' }}</span>
              </div>
              <div class="flex items-center">
                <span class="text-gray-400 w-20">产品：</span>
                <span class="font-medium text-gray-900">{{ currentTask?.product_name || '-' }}</span>
              </div>
              <div class="flex items-center">
                <span class="text-gray-400 w-20">子系统：</span>
                <span class="font-medium text-gray-900">{{ currentTask?.subsystem || '-' }}</span>
              </div>
              <div class="flex items-center">
                <span class="text-gray-400 w-20">创建人：</span>
                <span class="font-medium text-gray-900">{{ currentTask?.creator_info?.name || currentTask?.creator_info?.username || '-' }}</span>
              </div>
              <div class="flex items-center">
                <span class="text-gray-400 w-20">责任人：</span>
                <span class="font-medium text-gray-900">{{ currentTask?.assignee_info?.name || currentTask?.assignee_info?.username || '-' }}</span>
              </div>
            </div>

            <ElSteps :active="activeStep" align-center finish-status="success" class="max-w-3xl">
              <ElStep title="已创建" :description="currentTask?.sys_create_datetime || '-'" />
              <ElStep title="梳理/修订中" :description="currentTask?.accepted_at || '-'" />
              <ElStep title="评审中" :description="currentTask?.submitted_at || '-'" />
              <ElStep title="已关闭" :description="currentTask?.closed_at || '-'" />
            </ElSteps>
          </div>

          <div class="flex flex-col gap-3 min-w-[140px]">
            <ElButton
              v-if="canAccept"
              type="primary"
              :loading="actionLoading"
              @click="handleAcceptTask"
              class="w-full"
            >
              接收任务
            </ElButton>
            <ElButton
              v-if="canEdit"
              type="primary"
              plain
              @click="handleManageFailureModes"
              class="w-full !ml-0"
            >
              管理绑定
            </ElButton>
            <ElButton
              v-if="canEdit"
              type="success"
              plain
              @click="handleQuickCreateFailureMode"
              class="w-full !ml-0"
            >
              快速新增模式
            </ElButton>
            <ElButton
              v-if="canSubmit"
              type="success"
              :loading="actionLoading"
              @click="handleSubmitTask"
              class="w-full !ml-0"
            >
              提交评审
            </ElButton>
            <ElButton
              v-if="canClose"
              type="success"
              :loading="actionLoading"
              @click="handleCloseTask"
              class="w-full !ml-0"
            >
              评审关闭
            </ElButton>
          </div>
        </div>
      </div>"""

content = re.sub(top_container_pattern, modern_top, content)

# Remove taskTimelineSummary as we use ElSteps now
content = re.sub(r'const taskTimelineSummary = computed\(\(\) => \{[\s\S]*?\}\);\n', '', content)

# Redesign review tab slightly to be full height without the review input
review_tab_replacement = """<ElTabPane label="评审归档" name="review">
            <div class="grid grid-rows-[auto_1fr] h-full min-h-0 gap-4">
              <div class="rounded-xl border border-gray-100 bg-gray-50/50 p-5">
                <div class="mb-4 flex items-center justify-between">
                  <div class="text-base font-semibold text-gray-800">评审附件</div>
                  <div class="text-sm text-gray-500">上传相关评审会议纪要、专家意见等附件资料</div>
                </div>
                <div class="rounded-lg bg-white p-4 shadow-sm">
                  <FileSelector
                    v-model="reviewForm.review_attachment_ids"
                    :disabled="isClosed"
                    display-mode="list"
                    multiple
                    placeholder="点击或拖拽上传评审附件"
                  />
                </div>
              </div>

              <div class="flex flex-col min-h-0 rounded-xl border border-gray-100 bg-white p-2 shadow-sm">
                <div class="px-3 pb-3 pt-2 text-base font-semibold text-gray-800">
                  当前生效基线预览
                </div>
                <div class="flex-1 min-h-0">
                  <BaselineGrid />
                </div>
              </div>
            </div>
          </ElTabPane>"""

content = re.sub(r'<ElTabPane label="评审归档" name="review">[\s\S]*?</ElTabPane>', review_tab_replacement, content)


with open('/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-ele/src/views/failure-mode/tasks/detail.vue', 'w') as f:
    f.write(content)

