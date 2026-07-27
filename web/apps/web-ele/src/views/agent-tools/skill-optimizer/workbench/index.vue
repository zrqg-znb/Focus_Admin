<script setup lang="ts">
/* eslint-disable unicorn/empty-brace-spaces, vue/html-closing-bracket-newline */
import type { Provider } from '#/api/agent-tools/providers';
import type {
  Evaluation,
  Iteration,
  Scenario,
  Skill,
  SkillRun,
  SkillTrace,
} from '#/api/agent-tools/skill-optimizer';

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCollapse,
  ElCollapseItem,
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
  Download,
  FileArchive,
  Gauge,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Square,
  Trash2,
  Upload,
} from 'lucide-vue-next';

import { listProvidersApi } from '#/api/agent-tools/providers';
import {
  cancelRunApi,
  createRunApi,
  downloadRunApi,
  getRunApi,
  listIterationsApi,
  listSkillsApi,
  listTracesApi,
  regenerateRunConfigApi,
  saveRunConfigApi,
  startRunApi,
  uploadSkillApi,
} from '#/api/agent-tools/skill-optimizer';

import AgentToolsPageShell from '../../components/agent-tools-page-shell.vue';

defineOptions({ name: 'SkillOptimizerWorkbench' });

const POLL_INTERVAL_MS = 1200;
const route = useRoute();
const providers = ref<Provider[]>([]);
const skills = ref<Skill[]>([]);
const currentRun = ref<SkillRun>();
const iterations = ref<Iteration[]>([]);
const traces = ref<SkillTrace[]>([]);
const selectedSkillId = ref('');
const selectedProviderId = ref('');
const selectedTraceId = ref('');
const traceOutputRef = ref<HTMLElement>();
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
const activeStep = computed(() => {
  if (!currentRun.value) return 0;
  return currentRun.value.status === 'draft' ? 1 : 2;
});
const progress = computed(() => {
  if (!currentRun.value) return 0;
  if (currentRun.value.status === 'completed') return 100;
  return Math.min(
    (iterations.value.length * 100) /
      Math.max(currentRun.value.max_rounds + 1, 1),
    95,
  );
});
const selectedTrace = computed(
  () =>
    traces.value.find((item) => item.id === selectedTraceId.value) ||
    traces.value.at(-1),
);
const selectedSkill = computed(() =>
  skills.value.find((item) => item.id === selectedSkillId.value),
);
const scoreDelta = computed(() => {
  if (!currentRun.value) return 0;
  return (
    (currentRun.value.final_score || currentRun.value.baseline_score) -
    currentRun.value.baseline_score
  );
});
const selectedTraceContent = computed(() => {
  if (!selectedTrace.value) return '';
  return (
    selectedTrace.value.error_message ||
    selectedTrace.value.response_content ||
    '请求已发送，正在接收模型输出...'
  );
});
const traceStageText: Record<string, string> = {
  baseline_response: '基线回答',
  baseline_evaluation: '基线评分',
  candidate_response: '候选回答',
  candidate_evaluation: '候选评分',
  config_generation: '生成评测配置',
  diagnosis: '失败诊断',
  mutation: '单点改写',
};

watch(traces, (items) => {
  const latest = items.at(-1);
  if (!latest) return;
  if (!selectedTraceId.value || latest.status === 'running') {
    selectedTraceId.value = latest.id;
  }
});

watch(selectedTraceId, async () => {
  // 调用切换只重置右侧消息阅读位置，绝不干预外层工作流滚动。
  await nextTick();
  traceOutputRef.value?.scrollTo({ top: 0, behavior: 'auto' });
});

function selectTrace(traceId: string) {
  /** 仅切换右侧会话，不让浏览器将外层工作台滚动到当前按钮。 */
  selectedTraceId.value = traceId;
}

async function loadOptions() {
  providers.value = await listProvidersApi();
  const result = await listSkillsApi({ page: 1, pageSize: 100 });
  skills.value = result.items;
  if (!selectedSkillId.value) selectedSkillId.value = skills.value[0]?.id || '';
  if (!selectedProviderId.value) {
    selectedProviderId.value = providers.value[0]?.id || '';
  }
}

async function refreshRun() {
  if (!currentRun.value) return;
  currentRun.value = await getRunApi(currentRun.value.id);
  scenarios.value = currentRun.value.scenarios || [];
  evaluations.value = currentRun.value.evaluations || [];
  const [nextIterations, nextTraces] = await Promise.all([
    listIterationsApi(currentRun.value.id),
    listTracesApi(currentRun.value.id),
  ]);
  iterations.value = nextIterations;
  traces.value = nextTraces;
  if (isTerminal.value && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = undefined;
  }
}

function beginPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    refreshRun().catch(() => undefined);
  }, POLL_INTERVAL_MS);
}

async function loadRunFromRoute() {
  const runId = String(route.query.runId || '');
  if (!runId) {
    currentRun.value = undefined;
    iterations.value = [];
    traces.value = [];
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = undefined;
    return;
  }
  currentRun.value = await getRunApi(runId);
  await refreshRun();
  if (!isTerminal.value) beginPolling();
}

async function createAndGenerate() {
  if (!selectedSkillId.value || !selectedProviderId.value) {
    return ElMessage.warning('请先上传技能包并选择模型档案');
  }
  working.value = true;
  try {
    currentRun.value = await createRunApi({
      skill_id: selectedSkillId.value,
      provider_id: selectedProviderId.value,
      max_rounds: maxRounds.value,
    });
    currentRun.value = await regenerateRunConfigApi(currentRun.value.id);
    await refreshRun();
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
    await refreshRun();
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
  if (scenarios.value.length === 0 || evaluations.value.length === 0) {
    return ElMessage.warning('至少需要一个场景和一个评估标准');
  }
  working.value = true;
  try {
    await saveRunConfigApi(currentRun.value.id, {
      scenarios: scenarios.value,
      evaluations: evaluations.value,
    });
    currentRun.value = await startRunApi(currentRun.value.id);
    await refreshRun();
    beginPolling();
  } catch {
  } finally {
    working.value = false;
  }
}

async function cancel() {
  if (!currentRun.value) return;
  try {
    currentRun.value = await cancelRunApi(currentRun.value.id);
    ElMessage.info('已请求停止，当前调用完成后生效');
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
  await loadRunFromRoute();
});

watch(
  () => route.query.runId,
  (runId, previousRunId) => {
    if (runId !== previousRunId) loadRunFromRoute().catch(() => undefined);
  },
);

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <Page auto-content-height content-class="flex h-full min-h-0 flex-col">
    <AgentToolsPageShell class="workbench-shell">
      <header class="workflow-header">
        <div class="workflow-kicker">
          <span>SKILL OPTIMIZATION PROTOCOL</span>
          <small>DEFINE · EVALUATE · EVOLVE</small>
        </div>
        <ElSteps :active="activeStep" simple class="workbench-steps">
          <ElStep title="选择技能" />
          <ElStep title="复核评测" />
          <ElStep title="优化运行" />
        </ElSteps>
      </header>
      <div class="step-content">
        <section v-if="activeStep === 0" class="step-scroll setup-content">
          <section class="step-intro">
            <div class="step-heading">
              <span class="step-sequence">01 / PREPARE</span>
              <h2>选择技能与模型</h2>
              <p>上传包只读取并优化 SKILL.md，其余文件会在下载时原样保留。</p>
            </div>
            <div class="step-brief">
              <span>SKILL.md ONLY</span>
              <small>{{ skills.length }} PACKAGES READY</small>
            </div>
          </section>
          <section class="setup-grid">
            <article class="form-section source-panel">
              <div class="panel-heading">
                <div>
                  <span>INPUT PACKAGE</span>
                  <h3>技能包</h3>
                </div>
                <FileArchive :size="21" />
              </div>
              <p class="panel-desc">选择已有技能包，或导入新的 ZIP 文件。</p>
              <ElUpload
                accept=".zip"
                :show-file-list="false"
                :before-upload="upload"
              >
                <ElButton
                  :loading="uploading"
                  type="primary"
                  class="upload-action"
                >
                  <Upload :size="16" />
                  上传 ZIP 技能包
                </ElButton>
              </ElUpload>
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
                  <span>{{ skill.name }}</span>
                  <span class="option-meta">
                    {{ skill.file_manifest.length }} FILES
                  </span>
                </ElOption>
              </ElSelect>
              <div v-if="selectedSkill" class="skill-meta">
                <div class="selection-caption">
                  <span>SELECTED</span><i></i>
                </div>
                <strong>
                  {{ selectedSkill.description || '未填写描述' }}
                </strong>
                <span>{{ selectedSkill.original_filename }}</span>
                <span>
                  {{ selectedSkill.file_manifest.length }}
                  个文件会原样保留
                </span>
              </div>
            </article>
            <article class="form-section runtime-panel">
              <div class="panel-heading">
                <div>
                  <span>RUNTIME PROFILE</span>
                  <h3>模型与轮次</h3>
                </div>
                <Gauge :size="21" />
              </div>
              <p class="panel-desc">选择执行模型，并限定本次优化的探索深度。</p>
              <div class="field-block">
                <label>模型档案</label>
                <ElSelect
                  v-model="selectedProviderId"
                  class="w-full"
                  placeholder="选择模型档案"
                >
                  <ElOption
                    v-for="provider in providers"
                    :key="provider.id"
                    :label="`${provider.name} · ${provider.model}`"
                    :value="provider.id"
                  />
                </ElSelect>
              </div>
              <div class="field-block">
                <label>最大优化轮数</label>
                <ElInputNumber
                  v-model="maxRounds"
                  :min="1"
                  :max="20"
                  class="w-full"
                />
              </div>
              <p class="form-note">
                每轮会诊断失败原因、执行一次定向改写并重新评分。
              </p>
            </article>
          </section>
          <div class="step-actions">
            <span>准备完成后，生成可编辑的评测计划</span>
            <ElButton
              type="primary"
              :loading="working"
              :disabled="!selectedSkillId || !selectedProviderId"
              @click="createAndGenerate"
            >
              <Sparkles :size="16" />
              生成评测配置
            </ElButton>
          </div>
        </section>

        <section
          v-else-if="activeStep === 1"
          class="step-scroll review-content"
        >
          <section class="step-intro">
            <div class="step-heading">
              <span class="step-sequence">02 / REVIEW</span>
              <h2>复核评测计划</h2>
              <p>模型生成初稿后，可直接编辑测试场景与二元评估标准。</p>
            </div>
            <ElButton
              link
              type="primary"
              :loading="working"
              :disabled="!currentRun || currentRun.status !== 'draft'"
              @click="regenerate"
            >
              <RefreshCw :size="15" />
              重新生成
            </ElButton>
          </section>
          <ElEmpty
            v-if="!currentRun"
            description="先在上一步生成测试配置"
            :image-size="88"
          />
          <template v-else>
            <ElCollapse v-model="activeNames" class="config-collapse">
              <ElCollapseItem
                name="scenarios"
                :title="`测试场景 (${scenarios.length})`"
              >
                <div
                  v-for="(item, index) in scenarios"
                  :key="item.id"
                  class="config-item"
                >
                  <div class="config-item-head">
                    <span>CASE {{ String(index + 1).padStart(2, '0') }}</span>
                    <ElButton
                      link
                      type="danger"
                      @click="scenarios.splice(index, 1)"
                    >
                      <Trash2 :size="14" />
                      移除
                    </ElButton>
                  </div>
                  <div class="config-fields scenario-fields">
                    <div class="config-field">
                      <label>SCENARIO NAME</label>
                      <ElInput v-model="item.name" placeholder="场景名称" />
                    </div>
                    <div class="config-field">
                      <label>USER INPUT</label>
                      <ElInput
                        v-model="item.input"
                        type="textarea"
                        :rows="3"
                        placeholder="用户输入"
                      />
                    </div>
                  </div>
                </div>
                <ElButton plain @click="addScenario">
                  <Plus :size="15" />
                  新增场景
                </ElButton>
              </ElCollapseItem>
              <ElCollapseItem
                name="evaluations"
                :title="`评估标准 (${evaluations.length})`"
              >
                <div
                  v-for="(item, index) in evaluations"
                  :key="item.id"
                  class="config-item"
                >
                  <div class="config-item-head">
                    <span>RULE {{ String(index + 1).padStart(2, '0') }}</span>
                    <ElButton
                      link
                      type="danger"
                      @click="evaluations.splice(index, 1)"
                    >
                      <Trash2 :size="14" />
                      移除
                    </ElButton>
                  </div>
                  <div class="config-fields evaluation-fields">
                    <div class="config-field">
                      <label>RULE NAME</label>
                      <ElInput v-model="item.name" placeholder="标准名称" />
                    </div>
                    <div class="config-field">
                      <label>QUESTION</label>
                      <ElInput
                        v-model="item.question"
                        placeholder="二元评估问题"
                      />
                    </div>
                    <div class="config-field">
                      <label>PASS CONDITION</label>
                      <ElInput
                        v-model="item.pass_condition"
                        placeholder="通过条件"
                      />
                    </div>
                  </div>
                </div>
                <ElButton plain @click="addEvaluation">
                  <Plus :size="15" />
                  新增标准
                </ElButton>
              </ElCollapseItem>
            </ElCollapse>
            <div class="step-actions">
              <span>评测规则确认后，开始生成基线评分与改进候选</span>
              <ElButton type="primary" :loading="working" @click="start">
                <Play :size="16" />
                开始优化
              </ElButton>
            </div>
          </template>
        </section>

        <section v-else class="step-scroll run-content">
          <section class="step-intro run-intro">
            <div class="step-heading">
              <span class="step-sequence">03 / EVOLVE</span>
              <h2>实时优化监测</h2>
              <p>模型调用、诊断和改写会按执行顺序同步记录在本次运行中。</p>
            </div>
            <div class="step-brief run-brief">
              <span>{{
                currentRun ? `ROUND LIMIT ${currentRun.max_rounds}` : 'WAITING'
              }}</span>
              <small>LIVE TELEMETRY</small>
            </div>
          </section>
          <ElEmpty
            v-if="!currentRun"
            description="启动任务后查看优化过程"
            :image-size="88"
          />
          <template v-else>
            <section class="run-dashboard">
              <div class="score-card baseline-card">
                <span>BASELINE SCORE</span>
                <strong>{{ currentRun.baseline_score.toFixed(1) }}%</strong>
                <small>初始能力基准</small>
              </div>
              <div class="score-card current-card">
                <span>CURRENT SCORE</span>
                <strong class="accent-score">
                  {{
                    (
                      currentRun.final_score || currentRun.baseline_score
                    ).toFixed(1)
                  }}%
                </strong>
                <small :class="{ 'score-positive': scoreDelta > 0 }">
                  {{ scoreDelta > 0 ? '+' : '' }}{{ scoreDelta.toFixed(1) }} PTS
                </small>
              </div>
              <div class="run-state">
                <span>RUN STATUS</span>
                <ElTag
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
                <small>
                  {{
                    currentRun.error_message ||
                    (isTerminal ? '任务已结束' : '模型调用实时更新中')
                  }}
                </small>
              </div>
            </section>
            <ElProgress
              :percentage="progress"
              :stroke-width="10"
              :show-text="false"
            />
            <div class="run-actions">
              <ElButton
                v-if="['queued', 'running'].includes(currentRun.status)"
                type="danger"
                plain
                @click="cancel"
              >
                <Square :size="15" />
                停止优化
              </ElButton>
              <ElButton
                v-if="currentRun.status === 'completed'"
                type="primary"
                @click="download"
              >
                <Download :size="16" />
                下载改进包
              </ElButton>
            </div>

            <section class="console-layout">
              <aside class="trace-rail">
                <div class="rail-heading">
                  <div>
                    <span>CALL TRACE</span
                    ><small>{{ traces.length }} EVENTS</small>
                  </div>
                  <i :class="{ active: !isTerminal }"></i>
                </div>
                <button
                  v-for="trace in traces"
                  :key="trace.id"
                  class="trace-select"
                  :class="{
                    active: selectedTrace?.id === trace.id,
                    running: trace.status === 'running',
                    failed: trace.status === 'failed',
                  }"
                  @click="selectTrace(trace.id)"
                >
                  <span>{{ traceStageText[trace.stage] || trace.stage }}</span>
                  <small>
                    {{
                      trace.round_number === 0
                        ? '准备'
                        : `第 ${trace.round_number} 轮`
                    }}
                  </small>
                </button>
                <p v-if="traces.length === 0" class="trace-empty">
                  正在等待模型调用...
                </p>
              </aside>

              <section class="stream-console">
                <div class="console-heading">
                  <div>
                    <span>LIVE MODEL OUTPUT</span>
                    <small>
                      {{
                        selectedTrace
                          ? traceStageText[selectedTrace.stage] ||
                            selectedTrace.stage
                          : '等待调用'
                      }}
                    </small>
                  </div>
                  <small>
                    {{
                      selectedTrace?.duration_ms
                        ? `${(selectedTrace.duration_ms / 1000).toFixed(1)}s`
                        : 'STREAM'
                    }}
                  </small>
                </div>
                <pre
                  v-if="selectedTrace"
                  :key="selectedTrace.id"
                  ref="traceOutputRef"
                  class="stream-output">{{ selectedTraceContent }}<i v-if="selectedTrace.status === 'running'"></i></pre>
                <div v-else class="stream-empty">模型回复会在这里逐步输出</div>
                <details v-if="selectedTrace" class="stream-input">
                  <summary>查看发送给模型的内容</summary>
                  <pre>{{ selectedTrace.request_content }}</pre>
                </details>
              </section>
            </section>

            <section v-if="iterations.length > 0" class="iteration-summary">
              <div class="iteration-heading">
                <span>ITERATION LEDGER</span
                ><small>{{ iterations.length }} ENTRIES</small>
              </div>
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
                  }}
                </ElTag>
                <span>
                  {{ item.description || item.diagnosis || '基线评分' }}
                </span>
                <strong>{{ item.score_after.toFixed(1) }}%</strong>
              </div>
            </section>
            <section
              v-if="currentRun.status === 'completed'"
              class="final-skill"
            >
              <label class="diff-title">FINAL / SKILL.md</label>
              <pre class="skill-preview">{{
                currentRun.improved_skill_md
              }}</pre>
            </section>
          </template>
        </section>
      </div>
    </AgentToolsPageShell>
  </Page>
</template>

<style scoped>
.workbench-shell {
  display: flex;
  width: 100%;
  flex: 1;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  gap: 18px;
}
.workflow-header {
  flex: none;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-light);
}
.workflow-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 18px 0;
  color: var(--el-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.35px;
}
.workflow-kicker small {
  color: var(--el-text-color-secondary);
  font-size: 9px;
  letter-spacing: 1.1px;
}
.workbench-steps {
  flex: none;
  min-height: 58px;
  padding: 12px 18px 16px;
  overflow-x: auto;
  background: transparent;
}
.workbench-steps :deep(.el-step.is-simple) {
  min-width: 185px;
  flex: 1;
}
.workbench-steps :deep(.el-step__title) {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.workbench-steps :deep(.el-step__title.is-process) {
  color: var(--el-color-primary);
}
.workbench-steps :deep(.el-step__title.is-finish),
.workbench-steps :deep(.el-step__head.is-finish) {
  color: var(--el-color-primary);
}
.workbench-steps :deep(.el-step__head.is-process) {
  color: var(--el-color-primary);
}
.workbench-steps :deep(.el-step__arrow) {
  color: var(--el-text-color-placeholder);
}
.step-content {
  position: relative;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}
.step-scroll {
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding: 28px 4px 10px;
  scrollbar-gutter: stable;
}
.step-intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 0 2px 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.step-heading {
  padding-left: 15px;
  border-left: 3px solid var(--el-color-primary);
}
.step-sequence,
.panel-heading span,
.selection-caption,
.config-item-head > span,
.config-field label,
.iteration-heading {
  color: var(--el-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.2px;
}
.step-intro h2 {
  margin: 8px 0 6px;
  font-size: 26px;
  font-weight: 680;
  letter-spacing: 0;
}
.step-intro p,
.form-note {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}
.step-brief {
  display: flex;
  min-width: 160px;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  padding: 5px 0 5px 15px;
  border-left: 1px solid var(--el-border-color);
  color: var(--el-text-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.85px;
  text-align: right;
}
.step-brief small {
  color: var(--el-text-color-secondary);
  font-size: 9px;
  letter-spacing: 0.7px;
}
.setup-grid {
  display: grid;
  grid-template-columns: minmax(420px, 1.08fr) minmax(390px, 0.92fr);
  gap: 18px;
  padding: 26px 0 22px;
}
.form-section {
  position: relative;
  display: flex;
  min-height: 390px;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  box-shadow: 0 8px 20px rgb(15 23 42 / 4%);
}
.source-panel {
  border-top: 3px solid var(--el-color-primary);
}
.runtime-panel {
  border-top: 3px solid var(--el-color-primary);
}
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.panel-heading h3 {
  margin: 5px 0 0;
  color: var(--el-text-color-primary);
  font-size: 19px;
  font-weight: 670;
}
.panel-heading > svg {
  color: var(--el-color-primary);
}
.runtime-panel .panel-heading > svg {
  color: var(--el-color-primary);
}
.panel-desc {
  min-height: 40px;
  margin: -5px 0 1px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.7;
}
.source-panel :deep(.el-upload) {
  align-self: flex-start;
}
.form-section :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 5px;
}
.upload-action {
  min-height: 36px;
}
.form-section :deep(.el-input__wrapper) {
  min-height: 38px;
  border-radius: 5px;
  background: var(--el-fill-color-light);
  box-shadow: 0 0 0 1px var(--el-border-color-lighter) inset;
}
.form-section :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}
.form-section :deep(.el-input-number) {
  width: 100%;
}
.form-section :deep(.el-input-number .el-input__wrapper) {
  background: var(--el-fill-color-light);
}
.field-block {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field-block label,
.diff-title {
  color: var(--el-text-color-regular);
  font-size: 12px;
  font-weight: 650;
}
.option-meta {
  float: right;
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  letter-spacing: 0.6px;
}
.skill-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: auto;
  padding: 13px 0 0 14px;
  border-left: 2px solid var(--el-color-primary);
  border-top: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
}
.selection-caption {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
}
.selection-caption i,
.rail-heading i {
  display: block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-success);
}
.skill-meta strong {
  display: -webkit-box;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.skill-meta span {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.step-actions,
.run-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 2px 4px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.step-actions > span {
  margin-right: auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.step-actions :deep(.el-button),
.run-actions :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  border-radius: 5px;
}
.config-collapse {
  display: grid;
  gap: 12px;
  margin-top: 24px;
  border: 0;
}
.config-collapse :deep(.el-collapse-item) {
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
}
.config-collapse :deep(.el-collapse-item__header) {
  height: 52px;
  padding: 0 17px;
  border-bottom: 0;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-light);
  font-size: 14px;
  font-weight: 650;
}
.config-collapse :deep(.el-collapse-item__arrow) {
  color: var(--el-color-primary);
}
.config-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: 0;
  background: var(--el-bg-color);
}
.config-collapse :deep(.el-collapse-item__content) {
  padding: 0 17px 17px;
}
.config-item {
  display: grid;
  gap: 12px;
  padding: 17px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.config-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.config-item-head > span {
  color: var(--el-text-color-secondary);
  font-size: 10px;
}
.config-item-head :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.config-fields {
  display: grid;
  gap: 10px;
}
.scenario-fields {
  grid-template-columns: minmax(180px, 0.58fr) minmax(0, 1.42fr);
}
.evaluation-fields {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.config-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
}
.config-field label {
  color: var(--el-text-color-secondary);
  font-size: 9px;
  letter-spacing: 0.9px;
}
.config-collapse :deep(.el-input__wrapper) {
  min-height: 36px;
  border-radius: 5px;
  background: var(--el-fill-color-light);
  box-shadow: 0 0 0 1px var(--el-border-color-lighter) inset;
}
.config-collapse :deep(.el-textarea__inner) {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 5px;
  background: var(--el-fill-color-light);
  box-shadow: none;
}
.config-collapse :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 5px;
}
.run-content {
  min-width: 0;
}
.run-intro {
  margin-bottom: 22px;
}
.run-dashboard {
  display: grid;
  grid-template-columns: minmax(180px, 0.72fr) minmax(180px, 0.72fr) minmax(
      260px,
      1.56fr
    );
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-border-color);
}
.score-card,
.run-state {
  display: flex;
  min-height: 122px;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  padding: 18px 20px;
  background: var(--el-bg-color);
}
.score-card > span,
.run-state > span {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.95px;
}
.score-card strong {
  color: var(--el-text-color-primary);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0;
}
.score-card small {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.65px;
}
.accent-score {
  color: var(--el-color-primary);
}
.score-positive {
  color: var(--el-color-success) !important;
}
.run-state {
  align-items: flex-start;
  background: var(--el-fill-color-light);
}
.run-state :deep(.el-tag) {
  align-self: flex-start;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  letter-spacing: 0.45px;
}
.run-state small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.run-content :deep(.el-progress) {
  margin-top: 15px;
}
.run-content :deep(.el-progress-bar__outer) {
  border-radius: 2px;
  background: var(--el-fill-color-light);
}
.run-content :deep(.el-progress-bar__inner) {
  border-radius: 2px;
}
.console-layout {
  display: grid;
  height: clamp(420px, 56vh, 620px);
  min-height: 0;
  grid-template-columns: minmax(210px, 0.32fr) minmax(0, 1fr);
  margin-top: 18px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-border-color);
}
.trace-rail {
  min-height: 0;
  overflow-y: auto;
  padding: 14px 11px;
  border-right: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
}
.rail-heading,
.console-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 4px 13px;
}
.rail-heading > div,
.console-heading > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}
.rail-heading span,
.console-heading span,
.iteration-heading span {
  color: var(--el-text-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
}
.rail-heading small,
.console-heading small {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9px;
  letter-spacing: 0.75px;
}
.rail-heading i {
  background: var(--el-color-primary);
  box-shadow: 0 0 0 4px var(--el-color-primary-light-8);
}
.rail-heading i.active {
  animation: live-pulse 1.4s ease-in-out infinite;
}
.trace-select {
  display: flex;
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin: 4px 0;
  padding: 11px 9px;
  border: 0;
  border-left: 2px solid transparent;
  border-radius: 4px;
  color: var(--el-text-color-regular);
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  text-align: left;
}
.trace-select:hover,
.trace-select.active {
  border-left-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.trace-select.running {
  color: var(--el-color-primary);
}
.trace-select.failed {
  color: var(--el-color-danger);
}
.trace-select small {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  white-space: nowrap;
}
.trace-empty {
  padding: 12px 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.stream-console {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  background: var(--el-bg-color);
}
.console-heading {
  flex: none;
  padding: 14px 17px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
}
.console-heading span {
  color: var(--el-text-color-primary);
}
.console-heading small {
  color: var(--el-text-color-secondary);
}
.stream-output,
.stream-empty {
  min-height: 0;
  flex: 1;
  margin: 0;
  padding: 19px;
  overflow: auto;
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.75;
  white-space: pre-wrap;
}
.stream-empty {
  display: flex;
  align-items: center;
  color: var(--el-text-color-secondary);
}
.stream-output i {
  display: inline-block;
  width: 7px;
  height: 14px;
  margin-left: 4px;
  vertical-align: -2px;
  background: var(--el-color-primary);
  animation: terminal-cursor 0.9s steps(2, start) infinite;
}
.stream-input {
  flex: none;
  padding: 12px 17px;
  border-top: 1px solid var(--el-border-color);
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  letter-spacing: 0.45px;
}
.stream-input summary {
  cursor: pointer;
}
.stream-input pre {
  max-height: 160px;
  margin: 10px 0 0;
  overflow: auto;
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
}
.iteration-summary {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-top: 24px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.iteration-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 2px 8px;
}
.iteration-heading span {
  color: var(--el-text-color-primary);
}
.iteration-heading small {
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9px;
  letter-spacing: 0.75px;
}
.iteration-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 2px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}
.iteration-row :deep(.el-tag) {
  min-width: 54px;
  justify-content: center;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
}
.iteration-row span {
  flex: 1;
  color: var(--el-text-color-regular);
}
.final-skill {
  margin-top: 24px;
}
.skill-preview {
  max-height: 260px;
  margin-top: 10px;
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
}
@keyframes terminal-cursor {
  50% {
    opacity: 0;
  }
}
@keyframes live-pulse {
  50% {
    opacity: 0.45;
  }
}
@media (max-width: 900px) {
  .setup-grid,
  .run-dashboard,
  .evaluation-fields {
    grid-template-columns: 1fr;
  }
  .form-section {
    min-height: 0;
  }
  .score-card,
  .run-state {
    min-height: 104px;
  }
}
@media (max-width: 760px) {
  .workflow-kicker {
    padding: 11px 13px 0;
    font-size: 9px;
  }
  .workflow-kicker small {
    display: none;
  }
  .workbench-steps {
    min-height: 54px;
    padding: 10px 12px 14px;
  }
  .workbench-steps :deep(.el-step.is-simple) {
    min-width: 105px;
  }
  .workbench-steps :deep(.el-step__title) {
    font-size: 11px;
  }
  .step-scroll {
    padding-top: 21px;
  }
  .step-intro {
    align-items: flex-start;
    flex-direction: column;
    padding-bottom: 19px;
  }
  .step-intro h2 {
    font-size: 23px;
  }
  .step-brief {
    align-items: flex-start;
    min-width: 0;
    padding-left: 12px;
    text-align: left;
  }
  .setup-grid,
  .console-layout,
  .scenario-fields {
    grid-template-columns: 1fr;
  }
  .setup-grid {
    gap: 12px;
    padding-top: 20px;
  }
  .form-section {
    padding: 18px;
  }
  .panel-desc {
    min-height: 0;
  }
  .step-actions,
  .run-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .step-actions > span {
    margin: 0;
  }
  .step-actions :deep(.el-button),
  .run-actions :deep(.el-button) {
    width: 100%;
  }
  .config-collapse :deep(.el-collapse-item__content) {
    padding: 0 13px 13px;
  }
  .trace-rail {
    max-height: 170px;
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color);
  }
  .console-layout {
    height: 480px;
  }
  .stream-output,
  .stream-empty {
    padding: 15px;
  }
}
</style>
