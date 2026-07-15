<script setup lang="ts">
/* eslint-disable prettier/prettier */
import type { Provider, SkillRun } from '#/api/tools/agent-skills';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElTag } from 'element-plus';
import {
  ArrowUpRight,
  Bot,
  BrainCircuit,
  CircleDot,
  Settings2,
  Sparkles,
  WandSparkles,
} from 'lucide-vue-next';

import { listProvidersApi, listRunsApi } from '#/api/tools/agent-skills';

defineOptions({ name: 'AgentHub' });
const router = useRouter();
const providers = ref<Provider[]>([]);
const runs = ref<SkillRun[]>([]);
const loading = ref(true);
const activeProviders = computed(() =>
  providers.value.filter((item) => item.is_active),
);
const statusText: Record<string, string> = {
  completed: '已完成',
  failed: '失败',
  running: '运行中',
  queued: '排队中',
  draft: '待配置',
  cancelled: '已取消',
};

async function loadHub() {
  loading.value = true;
  try {
    providers.value = await listProvidersApi();
    const result = await listRunsApi({ page: 1, pageSize: 4 });
    runs.value = result.items;
  } finally {
    loading.value = false;
  }
}
function openSkillAgent() {
  router.push('/ai-tools/agent-skills');
}
function openModels() {
  router.push('/ai-tools/model-config');
}
onMounted(loadHub);
</script>

<template>
  <Page title="AI辅助工具" auto-content-height>
    <div class="hub-page">
      <section class="hub-intro">
        <div>
          <div class="eyebrow"><Sparkles :size="15" /> AI WORKSPACE</div>
          <h1>Agent Hub</h1>
          <p>
            把可复用的 AI 能力集中到一个工作台，从模型连接到 Agent
            运行都在这里完成。
          </p>
        </div>
        <div class="intro-actions">
          <ElButton plain @click="openModels">
            <Settings2 :size="16" /> 模型配置
</ElButton><ElButton type="primary" @click="openSkillAgent">
            <WandSparkles :size="16" /> 开始一次优化
          </ElButton>
        </div>
      </section>

      <section class="hub-metrics">
        <div><span>可用 Agent</span><strong>01</strong></div>
        <div>
          <span>已连接模型</span><strong>{{
            activeProviders.length.toString().padStart(2, '0')
          }}</strong>
        </div>
        <div>
          <span>近期运行</span><strong>{{ runs.length.toString().padStart(2, '0') }}</strong>
        </div>
        <div class="metric-note"><CircleDot :size="15" /> 工作区状态正常</div>
      </section>

      <section class="section-heading">
        <div>
          <span class="section-kicker">AVAILABLE AGENTS</span>
          <h2>选择一个 Agent 开始工作</h2>
        </div>
        <span class="section-caption">Agent 是可独立配置、运行和审计的 AI 工具单元</span>
      </section>
      <section class="agent-grid">
        <article class="agent-card featured" @click="openSkillAgent">
          <div class="agent-card-top">
            <div class="agent-icon"><BrainCircuit :size="26" /></div>
            <span class="agent-state"><i></i> READY</span>
          </div>
          <div class="agent-copy">
            <div class="agent-label">PROMPT ENGINEERING</div>
            <h3>Skill 自进化 Agent</h3>
            <p>
              自动生成评测场景，诊断失败输出，并通过可审计的单点改写持续优化
              SKILL.md。
            </p>
          </div>
          <div class="agent-card-bottom">
            <span>评测 · 诊断 · 迭代</span><ArrowUpRight :size="20" />
          </div>
        </article>
        <article class="agent-card coming">
          <div class="agent-card-top">
            <div class="agent-icon muted"><Bot :size="26" /></div>
            <span class="agent-state muted-state">COMING SOON</span>
          </div>
          <div class="agent-copy">
            <div class="agent-label">AUTOMATION</div>
            <h3>更多 Agent</h3>
            <p>后续接入代码分析、知识检索、测试生成等专用 AI 工具。</p>
          </div>
          <div class="agent-card-bottom">
            <span>工具目录持续扩展</span><span class="plus-mark">+</span>
          </div>
        </article>
      </section>

      <section class="lower-grid">
        <div class="runs-panel">
          <div class="section-heading compact">
            <div>
              <span class="section-kicker">RECENT RUNS</span>
              <h2>最近运行</h2>
            </div>
            <ElButton
              link
              type="primary"
              @click="router.push('/ai-tools/agent-skills/records')"
            >
              查看全部
            </ElButton>
          </div>
          <div v-if="loading" class="empty-run">正在加载工作区...</div>
          <div v-else-if="runs.length === 0" class="empty-run">
            还没有运行记录，开始第一次 Skill 优化吧。
          </div>
          <div v-else class="run-list">
            <div
              v-for="run in runs"
              :key="run.id"
              class="run-item"
              @click="
                router.push({
                  path: '/ai-tools/agent-skills',
                  query: { runId: run.id },
                })
              "
            >
              <div class="run-mark"><BrainCircuit :size="16" /></div>
              <div class="run-main">
                <strong>{{ run.skill_name }}</strong><span>{{ run.provider_model }} ·
                  {{ run.sys_create_datetime }}</span>
              </div>
              <ElTag
                size="small"
                :type="
                  run.status === 'completed'
                    ? 'success'
                    : run.status === 'failed'
                      ? 'danger'
                      : 'warning'
                "
              >
                {{ statusText[run.status] || run.status }}
</ElTag><ArrowUpRight :size="16" class="run-arrow" />
            </div>
          </div>
        </div>
        <div class="model-panel">
          <div class="section-heading compact">
            <div>
              <span class="section-kicker">MODEL CONNECTIONS</span>
              <h2>我的模型</h2>
            </div>
            <ElButton link type="primary" @click="openModels">管理</ElButton>
          </div>
          <div v-if="activeProviders.length === 0" class="model-empty">
            <Settings2 :size="22" /><span>配置一个模型，解锁 Agent</span><ElButton type="primary" plain size="small" @click="openModels">
              去配置
            </ElButton>
          </div>
          <div v-else class="model-list">
            <div
              v-for="provider in activeProviders.slice(0, 3)"
              :key="provider.id"
              class="model-item"
            >
              <span class="model-dot"></span>
              <div>
                <strong>{{ provider.name }}</strong><small>{{ provider.model }}</small>
              </div>
              <span class="model-online">ONLINE</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </Page>
</template>

<style scoped>
.hub-page {
  min-height: 100%;
  color: var(--el-text-color-primary);
}
.hub-intro {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 0 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.eyebrow,
.section-kicker {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.4px;
}
.hub-intro h1 {
  margin: 10px 0 5px;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: 0;
}
.hub-intro p {
  max-width: 680px;
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.intro-actions {
  display: flex;
  gap: 10px;
}
.intro-actions :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.hub-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr) 1.4fr;
  gap: 1px;
  margin: 20px 0 34px;
  background: var(--el-border-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
}
.hub-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 15px 18px;
  background: var(--el-bg-color);
}
.hub-metrics span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.hub-metrics strong {
  font-size: 25px;
  font-weight: 650;
}
.hub-metrics .metric-note {
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  color: var(--el-color-success);
  font-size: 12px;
}
.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 13px;
}
.section-heading h2 {
  margin: 5px 0 0;
  font-size: 18px;
  font-weight: 650;
}
.section-caption {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.agent-card {
  position: relative;
  display: flex;
  min-height: 255px;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  cursor: pointer;
  transition:
    border-color 0.2s,
    transform 0.2s,
    box-shadow 0.2s;
}
.agent-card:hover {
  border-color: var(--el-color-primary);
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgb(15 23 42 / 8%);
}
.agent-card.featured {
  color: #fff;
  border-color: #2d4356;
  background: linear-gradient(135deg, #172536 0%, #223d4b 55%, #2c594e 100%);
}
.agent-card.featured::after {
  position: absolute;
  right: -55px;
  bottom: -95px;
  width: 260px;
  height: 260px;
  border: 1px solid rgb(255 255 255 / 14%);
  border-radius: 50%;
  content: '';
  box-shadow:
    0 0 0 22px rgb(255 255 255 / 3%),
    0 0 0 45px rgb(255 255 255 / 2%);
}
.agent-card-top,
.agent-card-bottom {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.agent-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 25%);
  border-radius: 8px;
  color: #b9f4d9;
  background: rgb(255 255 255 / 10%);
}
.agent-icon.muted {
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-color: var(--el-border-color-lighter);
}
.agent-state {
  color: #b9f4d9;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.1px;
}
.agent-state i {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 5px;
  border-radius: 50%;
  background: #6ce0a9;
}
.muted-state {
  color: var(--el-text-color-secondary);
}
.agent-copy {
  position: relative;
  z-index: 1;
  max-width: 520px;
}
.agent-label {
  margin-bottom: 8px;
  color: #9ee5c7;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
}
.coming .agent-label {
  color: var(--el-text-color-secondary);
}
.agent-copy h3 {
  margin: 0 0 8px;
  font-size: 23px;
  font-weight: 650;
}
.agent-copy p {
  max-width: 470px;
  margin: 0;
  color: rgb(255 255 255 / 72%);
  font-size: 13px;
  line-height: 1.7;
}
.coming .agent-copy p {
  color: var(--el-text-color-secondary);
}
.agent-card-bottom {
  color: rgb(255 255 255 / 66%);
  font-size: 12px;
}
.coming .agent-card-bottom {
  color: var(--el-text-color-secondary);
}
.plus-mark {
  font-size: 24px;
  font-weight: 300;
}
.lower-grid {
  display: grid;
  grid-template-columns: 1.35fr 0.85fr;
  gap: 14px;
  margin-top: 30px;
}
.runs-panel,
.model-panel {
  min-height: 200px;
  padding: 18px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}
.compact {
  margin-bottom: 13px;
}
.compact h2 {
  font-size: 16px;
}
.run-list,
.model-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.run-item,
.model-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
}
.run-mark {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 6px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.run-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.run-main strong,
.model-item strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.run-main span,
.model-item small {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.run-arrow {
  color: var(--el-text-color-placeholder);
}
.empty-run,
.model-empty {
  display: flex;
  min-height: 120px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.model-item {
  cursor: default;
}
.model-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-success);
  box-shadow: 0 0 0 4px var(--el-color-success-light-9);
}
.model-item > div {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.model-online {
  color: var(--el-color-success);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
}
@media (max-width: 900px) {
  .hub-intro {
    align-items: flex-start;
    flex-direction: column;
  }
  .hub-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .metric-note {
    grid-column: span 2;
  }
  .agent-grid,
  .lower-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 560px) {
  .intro-actions {
    width: 100%;
  }
  .intro-actions :deep(.el-button) {
    flex: 1;
  }
  .hub-intro h1 {
    font-size: 28px;
  }
}
</style>
