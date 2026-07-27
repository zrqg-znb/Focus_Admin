<script setup lang="ts">
/* eslint-disable unicorn/empty-brace-spaces, vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline */
import type { Provider, ProviderPayload } from '#/api/agent-tools/providers';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElSwitch,
  ElTag,
} from 'element-plus';
import {
  KeyRound,
  Link2,
  MoreHorizontal,
  Pencil,
  Plus,
  Radio,
  ShieldCheck,
  Trash2,
} from 'lucide-vue-next';

import {
  createProviderApi,
  listProvidersApi,
  testProviderApi,
  updateProviderApi,
} from '#/api/agent-tools/providers';

import AgentToolsPageShell from '../components/agent-tools-page-shell.vue';

defineOptions({ name: 'AgentToolsProviders' });
const providers = ref<Provider[]>([]);
const dialogVisible = ref(false);
const editingId = ref('');
const testingId = ref('');
const form = reactive<ProviderPayload>({
  name: '',
  base_url: '',
  model: '',
  api_key: '',
  is_active: true,
  description: '',
});
const activeCount = computed(
  () => providers.value.filter((item) => item.is_active).length,
);
function resetForm(row?: Provider) {
  editingId.value = row?.id || '';
  Object.assign(form, {
    name: row?.name || '',
    base_url: row?.base_url || '',
    model: row?.model || '',
    api_key: '',
    is_active: row?.is_active ?? true,
    description: row?.description || '',
  });
  dialogVisible.value = true;
}
async function load() {
  providers.value = await listProvidersApi();
}
async function save() {
  if (
    !form.name ||
    !form.base_url ||
    !form.model ||
    (!editingId.value && !form.api_key)
  )
    return ElMessage.warning('请完整填写名称、URL、模型和 API Key');
  try {
    editingId.value
      ? await updateProviderApi(editingId.value, form)
      : await createProviderApi(form);
    ElMessage.success('模型配置已保存');
    dialogVisible.value = false;
    await load();
  } catch {}
}
async function test(row: Provider) {
  testingId.value = row.id;
  try {
    const result = await testProviderApi(row.id);
    result.ok
      ? ElMessage.success(result.message)
      : ElMessage.error(result.message);
  } catch {
  } finally {
    testingId.value = '';
  }
}
async function remove(row: Provider) {
  ElMessage.info(`删除配置「${row.name}」的能力将在下一版本开放`);
}
onMounted(load);
</script>

<template>
  <Page auto-content-height>
    <AgentToolsPageShell class="model-page">
      <section class="model-hero">
        <div>
          <div class="hero-kicker">
            <Radio :size="14" /> PERSONAL MODEL SPACE
          </div>
          <h1>我的模型连接</h1>
          <p>
            配置你自己的 API 连接，Agent Hub
            中的每次运行都会使用这里的模型档案。
          </p>
        </div>
        <ElButton type="primary" @click="resetForm()">
          <Plus :size="17" /> 新增连接
        </ElButton>
      </section>
      <section class="model-summary">
        <div class="summary-icon"><ShieldCheck :size="21" /></div>
        <div>
          <strong>{{ activeCount }} 个连接已就绪</strong
          ><span>API Key 仅加密保存在服务端，页面不会展示完整密钥</span>
        </div>
        <ElTag type="success">安全存储</ElTag>
      </section>
      <div v-if="providers.length === 0" class="empty-state">
        <ElEmpty description="还没有模型连接">
          <ElButton type="primary" @click="resetForm()">
            添加第一个连接
          </ElButton>
        </ElEmpty>
      </div>
      <section v-else class="provider-grid">
        <article
          v-for="provider in providers"
          :key="provider.id"
          class="provider-card"
          :class="{ inactive: !provider.is_active }"
        >
          <div class="provider-top">
            <div class="provider-badge"><KeyRound :size="17" /></div>
            <ElTag size="small" :type="provider.is_active ? 'success' : 'info'">
              {{ provider.is_active ? '已启用' : '已停用' }} </ElTag
            ><button class="icon-button" title="更多操作">
              <MoreHorizontal :size="18" />
            </button>
          </div>
          <div class="provider-body">
            <h2>{{ provider.name }}</h2>
            <div class="provider-model">{{ provider.model }}</div>
            <div class="provider-url">
              <Link2 :size="14" />{{ provider.base_url }}
            </div>
          </div>
          <div class="provider-footer">
            <span
              ><span class="status-dot"></span
              >{{
                provider.has_api_key ? 'API Key 已配置' : '缺少 API Key'
              }}</span
            >
            <div>
              <ElButton
                link
                :loading="testingId === provider.id"
                @click="test(provider)"
              >
                测试连接 </ElButton
              ><ElButton link type="primary" @click="resetForm(provider)">
                <Pencil :size="14" /> 编辑 </ElButton
              ><ElButton link type="danger" @click="remove(provider)">
                <Trash2 :size="14" />
              </ElButton>
            </div>
          </div>
        </article>
        <button class="add-card" @click="resetForm()">
          <span><Plus :size="22" /></span><strong>添加新的模型连接</strong
          ><small>OpenAI 兼容 API</small>
        </button>
      </section>
    </AgentToolsPageShell>
    <ElDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑模型连接' : '新增模型连接'"
      width="560px"
    >
      <ElForm label-width="104px">
        <ElFormItem label="连接名称">
          <ElInput
            v-model="form.name"
            placeholder="例如：个人 GPT"
          /> </ElFormItem
        ><ElFormItem label="API URL">
          <ElInput
            v-model="form.base_url"
            placeholder="https://api.example.com/v1"
          /> </ElFormItem
        ><ElFormItem label="模型名称">
          <ElInput
            v-model="form.model"
            placeholder="gpt-4o-mini"
          /> </ElFormItem
        ><ElFormItem label="API Key">
          <ElInput
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="editingId ? '留空保留当前 Key' : 'sk-...'"
          /> </ElFormItem
        ><ElFormItem label="启用连接">
          <ElSwitch v-model="form.is_active" /> </ElFormItem
        ><ElFormItem label="备注">
          <ElInput
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="记录这个连接的用途"
          />
        </ElFormItem> </ElForm
      ><template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton
        ><ElButton type="primary" @click="save">保存连接</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped>
.model-page {
  min-height: 100%;
}
.model-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 4px 0 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.model-hero h1 {
  margin: 10px 0 5px;
  font-size: 30px;
  font-weight: 700;
}
.model-hero p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.hero-kicker {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.4px;
}
.model-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 7px;
  background: var(--el-bg-color);
}
.summary-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 7px;
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}
.model-summary div:nth-child(2) {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.model-summary span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.provider-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(230px, 1fr));
  gap: 14px;
}
.provider-card,
.add-card {
  min-height: 222px;
  padding: 18px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
}
.provider-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.provider-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 8px 24px rgb(15 23 42 / 7%);
}
.provider-card.inactive {
  opacity: 0.68;
}
.provider-top,
.provider-footer {
  display: flex;
  align-items: center;
  gap: 7px;
}
.provider-top .icon-button {
  margin-left: auto;
}
.provider-badge {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 7px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.icon-button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  color: var(--el-text-color-secondary);
  background: transparent;
  cursor: pointer;
}
.icon-button:hover {
  background: var(--el-fill-color-light);
}
.provider-body {
  padding: 18px 0 14px;
}
.provider-body h2 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 650;
}
.provider-model {
  margin-bottom: 13px;
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
.provider-url {
  display: flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-footer {
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.provider-footer > span {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-success);
}
.add-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-direction: column;
  border-style: dashed;
  color: var(--el-text-color-secondary);
  cursor: pointer;
}
.add-card:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}
.add-card span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  background: var(--el-fill-color-light);
}
.add-card small {
  font-size: 11px;
}
.empty-state {
  padding: 60px 0;
}
@media (max-width: 1050px) {
  .provider-grid {
    grid-template-columns: repeat(2, minmax(230px, 1fr));
  }
}
@media (max-width: 650px) {
  .model-hero {
    align-items: flex-start;
    flex-direction: column;
  }
  .provider-grid {
    grid-template-columns: 1fr;
  }
}
</style>
