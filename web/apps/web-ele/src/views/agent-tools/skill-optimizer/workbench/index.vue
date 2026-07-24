<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script setup lang="ts">
/* eslint-disable unicorn/empty-brace-spaces, unicorn/no-nested-ternary, unicorn/prefer-array-some, vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline */
import type {
  Evaluation,
  Iteration,
  Provider,
  Scenario,
  Skill,
  SkillRun,
} from '#/api/agent-tools/skill-optimizer';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
  ElDivider,
  ElEmpty,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElProgress,
  ElSelect,
  ElStep,
  ElSteps,
  ElTag,
  ElUpload,
} from 'element-plus';

import {
  cancelRunApi,
  createRunApi,
  downloadRunApi,
  getRunApi,
  listIterationsApi,
  listProvidersApi,
  listSkillsApi,
  regenerateRunConfigApi,
  saveRunConfigApi,
  startRunApi,
  uploadSkillApi,
} from '#/api/agent-tools/skill-optimizer';

defineOptions({ name: 'SkillOptimizerWorkbench' });
const route = useRoute();
const providers = ref<Provider[]>([]);
const skills = ref<Skill[]>([]);
const currentRun = ref<SkillRun>();
const iterations = ref<Iteration[]>([]);
const selectedSkillId = ref('');
const selectedProviderId = ref('');
const maxRounds = ref(5);
const uploading = ref(false);
const working = ref(false);
const activeNames = ref(['scenarios', 'evaluations']);
const scenarios = ref<Scenario[]>([]);
const evaluations = ref<Evaluation[]>([]);
let pollTimer: ReturnType<typeof setInterval> | undefined;
const isTerminal = computed(() =>
  ['cancelled', 'completed', 'failed'].includes(currentRun.value?.status || ''),
);
const progress = computed(() => {
  if (!currentRun.value) return 0;
  if (currentRun.value.status === 'completed') return 100;
  return Math.min(
    (iterations.value.length * 100) /
      Math.max(currentRun.value.max_rounds + 1, 1),
    95,
  );
});
const currentStep = computed(() =>
  currentRun.value
    ? currentRun.value.status === 'draft'
      ? 1
      : isTerminal.value
        ? 3
        : 2
    : 0,
);

async function loadOptions() {
  providers.value = await listProvidersApi();
  const result = await listSkillsApi({ page: 1, pageSize: 100 });
  skills.value = result.items;
  if (!selectedSkillId.value) selectedSkillId.value = skills.value[0]?.id || '';
  if (!selectedProviderId.value)
    selectedProviderId.value = providers.value[0]?.id || '';
}
async function refreshRun() {
  if (!currentRun.value) return;
  currentRun.value = await getRunApi(currentRun.value.id);
  scenarios.value = currentRun.value.scenarios || [];
  evaluations.value = currentRun.value.evaluations || [];
  iterations.value = await listIterationsApi(currentRun.value.id);
  if (isTerminal.value && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = undefined;
  }
}
async function createAndGenerate() {
  if (!selectedSkillId.value || !selectedProviderId.value)
    return ElMessage.warning('请先上传技能包并选择模型档案');
  working.value = true;
  try {
    currentRun.value = await createRunApi({
      skill_id: selectedSkillId.value,
      provider_id: selectedProviderId.value,
      max_rounds: maxRounds.value,
    });
    currentRun.value = await regenerateRunConfigApi(currentRun.value.id);
    scenarios.value = currentRun.value.scenarios;
    evaluations.value = currentRun.value.evaluations;
    ElMessage.success('已生成测试配置，请复核后启动');
  } catch {
  } finally {
    working.value = false;
  }
}
async function regenerate() {
  if (!currentRun.value) return;
  working.value = true;
  try {
    currentRun.value = await regenerateRunConfigApi(currentRun.value.id);
    scenarios.value = currentRun.value.scenarios;
    evaluations.value = currentRun.value.evaluations;
  } catch {
  } finally {
    working.value = false;
  }
}
function addScenario() {
  scenarios.value.push({ id: Date.now(), name: '新场景', input: '' });
}
function addEvaluation() {
  evaluations.value.push({
    id: Date.now(),
    name: '新标准',
    question: '',
    pass_condition: '',
  });
}
async function start() {
  if (!currentRun.value) return;
  if (scenarios.value.length === 0 || evaluations.value.length === 0)
    return ElMessage.warning('至少需要一个场景和一个评估标准');
  working.value = true;
  try {
    await saveRunConfigApi(currentRun.value.id, {
      scenarios: scenarios.value,
      evaluations: evaluations.value,
    });
    currentRun.value = await startRunApi(currentRun.value.id);
    await refreshRun();
    pollTimer = setInterval(() => {
      refreshRun().catch(() => undefined);
    }, 3000);
  } catch {
  } finally {
    working.value = false;
  }
}
async function cancel() {
  if (!currentRun.value) return;
  try {
    currentRun.value = await cancelRunApi(currentRun.value.id);
    ElMessage.info('已请求停止，当前轮完成后生效');
  } catch {}
}
async function upload(file: File) {
  uploading.value = true;
  try {
    const skill = await uploadSkillApi(file);
    skills.value.unshift(skill);
    selectedSkillId.value = skill.id;
    ElMessage.success('技能包上传成功');
  } catch {
  } finally {
    uploading.value = false;
  }
  return false;
}
async function download() {
  if (!currentRun.value) return;
  try {
    const blob = await downloadRunApi(currentRun.value.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentRun.value.skill_name}-improved.zip`;
    link.click();
    URL.revokeObjectURL(url);
  } catch {}
}
onMounted(async () => {
  await loadOptions();
  const runId = String(route.query.runId || '');
  if (runId) {
    currentRun.value = await getRunApi(runId);
    await refreshRun();
    if (!isTerminal.value)
      pollTimer = setInterval(() => {
        refreshRun().catch(() => undefined);
      }, 3000);
  }
});
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <Page title="Skill Optimizer 工作台" auto-content-height>
    <div class="workbench-shell">
      <ElSteps :active="currentStep" simple class="workbench-steps">
        <ElStep title="选择技能" /><ElStep title="复核评测" /><ElStep
          title="优化运行"
        /><ElStep title="结果" />
      </ElSteps>
      <div class="workbench-grid">
        <ElCard class="workspace-panel source-panel" shadow="never">
          <template #header>
            <div class="panel-heading">
              <span>技能包</span><ElTag type="info">仅优化 SKILL.md</ElTag>
            </div>
          </template>
          <ElUpload
            accept=".zip"
            :show-file-list="false"
            :before-upload="upload"
          >
            <ElButton :loading="uploading" type="primary" plain class="w-full">
              上传 ZIP 技能包
            </ElButton>
          </ElUpload>
          <ElDivider />
          <ElSelect
            v-model="selectedSkillId"
            placeholder="选择已上传技能"
            class="w-full"
          >
            <ElOption
              v-for="skill in skills"
              :key="skill.id"
              :label="skill.name"
              :value="skill.id"
            >
              <span>{{ skill.name }}</span
              ><span class="option-meta"
                >{{ skill.file_manifest.length }} files</span
              >
            </ElOption>
          </ElSelect>
          <div
            v-if="skills.find((item) => item.id === selectedSkillId)"
            class="skill-meta"
          >
            <strong>{{
              skills.find((item) => item.id === selectedSkillId)?.description ||
              '未填写描述'
            }}</strong
            ><span>{{
              skills.find((item) => item.id === selectedSkillId)
                ?.original_filename
            }}</span
            ><span
              >{{
                skills.find((item) => item.id === selectedSkillId)
                  ?.file_manifest.length
              }}
              个文件会原样保留</span
            >
          </div>
          <ElDivider />
          <div class="form-stack">
            <label>模型档案</label
            ><ElSelect v-model="selectedProviderId" class="w-full">
              <ElOption
                v-for="provider in providers"
                :key="provider.id"
                :label="`${provider.name} · ${provider.model}`"
                :value="provider.id"
              /> </ElSelect
            ><label>最大轮数</label
            ><ElInputNumber
              v-model="maxRounds"
              :min="1"
              :max="20"
              class="w-full"
            />
          </div>
          <ElButton
            class="mt-5 w-full"
            type="primary"
            :loading="working"
            :disabled="!selectedSkillId || !selectedProviderId"
            @click="createAndGenerate"
          >
            生成评测配置
          </ElButton>
        </ElCard>
        <ElCard class="workspace-panel config-panel" shadow="never">
          <template #header>
            <div class="panel-heading">
              <span>评测配置</span
              ><ElButton
                link
                type="primary"
                :loading="working"
                :disabled="!currentRun || currentRun.status !== 'draft'"
                @click="regenerate"
              >
                重新生成
              </ElButton>
            </div>
          </template>
          <ElEmpty
            v-if="!currentRun"
            description="选择技能和模型后生成测试配置"
            :image-size="88"
          />
          <ElCollapse v-else v-model="activeNames">
            <ElCollapseItem
              name="scenarios"
              :title="`测试场景 (${scenarios.length})`"
            >
              <div
                v-for="(item, index) in scenarios"
                :key="item.id"
                class="config-item"
              >
                <ElInput v-model="item.name" placeholder="场景名称" /><ElInput
                  v-model="item.input"
                  type="textarea"
                  :rows="3"
                  placeholder="用户输入"
                /><ElButton
                  link
                  type="danger"
                  @click="scenarios.splice(index, 1)"
                >
                  移除
                </ElButton>
              </div>
              <ElButton plain @click="addScenario">
                新增场景
              </ElButton> </ElCollapseItem
            ><ElCollapseItem
              name="evaluations"
              :title="`评估标准 (${evaluations.length})`"
            >
              <div
                v-for="(item, index) in evaluations"
                :key="item.id"
                class="config-item"
              >
                <ElInput v-model="item.name" placeholder="标准名称" /><ElInput
                  v-model="item.question"
                  placeholder="二元评估问题"
                /><ElInput
                  v-model="item.pass_condition"
                  placeholder="通过条件"
                /><ElButton
                  link
                  type="danger"
                  @click="evaluations.splice(index, 1)"
                >
                  移除
                </ElButton>
              </div>
              <ElButton plain @click="addEvaluation"> 新增标准 </ElButton>
            </ElCollapseItem>
          </ElCollapse>
          <ElButton
            v-if="currentRun?.status === 'draft'"
            type="primary"
            class="mt-5 w-full"
            :loading="working"
            @click="start"
          >
            开始优化
          </ElButton>
        </ElCard>
        <ElCard class="workspace-panel run-panel" shadow="never">
          <template #header>
            <div class="panel-heading">
              <span>优化进度</span
              ><ElTag
                v-if="currentRun"
                :type="
                  isTerminal
                    ? currentRun.status === 'completed'
                      ? 'success'
                      : 'danger'
                    : 'warning'
                "
              >
                {{ currentRun.status }}
              </ElTag>
            </div>
          </template>
          <ElEmpty
            v-if="!currentRun"
            description="任务运行记录会显示在这里"
            :image-size="88"
          />
          <template v-else>
            <div class="score-row">
              <div>
                <small>基线评分</small
                ><strong>{{ currentRun.baseline_score.toFixed(1) }}%</strong>
              </div>
              <div>
                <small>最终评分</small
                ><strong class="accent-score"
                  >{{ currentRun.final_score.toFixed(1) }}%</strong
                >
              </div>
            </div>
            <ElProgress
              :percentage="progress"
              :stroke-width="10"
              :show-text="false"
            />
            <p class="progress-note">
              {{
                currentRun.error_message ||
                (isTerminal ? '任务已结束' : '每 3 秒刷新一次进度')
              }}
            </p>
            <ElButton
              v-if="['queued', 'running'].includes(currentRun.status)"
              type="danger"
              plain
              class="w-full"
              @click="cancel"
            >
              停止优化 </ElButton
            ><ElDivider />
            <div class="iteration-list">
              <div
                v-for="item in iterations"
                :key="item.id"
                class="iteration-row"
              >
                <ElTag :type="item.kept ? 'success' : 'info'">
                  {{
                    item.round_number === 0
                      ? '基线'
                      : `第 ${item.round_number} 轮`
                  }} </ElTag
                ><span>{{
                  item.description || item.diagnosis || '基线评分'
                }}</span
                ><strong>{{ item.score_after.toFixed(1) }}%</strong>
              </div>
            </div>
            <template v-if="currentRun.status === 'completed'">
              <ElButton type="primary" class="mt-4 w-full" @click="download">
                下载改进包 </ElButton
              ><ElDivider /><label class="diff-title">最终 SKILL.md</label>
              <pre class="skill-preview">{{
                currentRun.improved_skill_md
              }}</pre>
            </template>
          </template>
        </ElCard>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.workbench-shell {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 14px;
  height: 100%;
}
.workbench-steps {
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}
.workbench-grid {
  display: grid;
  min-height: 0;
  flex: 1;
  grid-template-columns: minmax(245px, 0.78fr) minmax(390px, 1.25fr) minmax(
      300px,
      0.95fr
    );
  gap: 14px;
}
.workspace-panel {
  min-height: 0;
  overflow: auto;
  border-radius: 6px;
}
.panel-heading,
.score-row,
.iteration-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.option-meta,
.skill-meta span,
.progress-note,
small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.skill-meta,
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}
.form-stack label,
.diff-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.config-item {
  display: grid;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.score-row {
  padding: 12px 0 18px;
}
.score-row div {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.score-row strong {
  font-size: 28px;
}
.accent-score {
  color: var(--el-color-primary);
}
.iteration-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.iteration-row {
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}
.iteration-row span {
  flex: 1;
  color: var(--el-text-color-regular);
}
.skill-preview {
  max-height: 260px;
  overflow: auto;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}
@media (max-width: 1280px) {
  .workbench-grid {
    grid-template-columns: 1fr 1fr;
  }
  .run-panel {
    grid-column: span 2;
  }
}
@media (max-width: 760px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }
  .run-panel {
    grid-column: auto;
  }
}
</style>
