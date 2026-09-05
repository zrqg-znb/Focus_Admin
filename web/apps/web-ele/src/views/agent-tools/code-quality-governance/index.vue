<script lang="ts" setup>
import type { Component } from 'vue';

import type {
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';
import type { Section } from './types';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  listProjectsApi,
  listResponsibilitiesApi,
  listUsersApi,
} from '#/api/agent-tools/code-quality-governance';

import AgentToolsPageShell from '../components/agent-tools-page-shell.vue';
import AuditPanel from './audit-panel.vue';
import DashboardPanel from './dashboard-panel.vue';
import FindingsPanel from './findings-panel.vue';
import ScopeConfigPanel from './scope-config-panel.vue';

defineOptions({ name: 'CodeQualityGovernance' });

const sections: { key: Section; label: string }[] = [
  { key: 'dashboard', label: '治理看板' },
  { key: 'config', label: '项目与责任田' },
  { key: 'findings', label: '问题明细' },
  { key: 'audit', label: '屏蔽审核' },
];

const section = ref<Section>('dashboard');
const projects = ref<GovernanceProject[]>([]);
const responsibilities = ref<GovernanceResponsibility[]>([]);
const users = ref<UserOption[]>([]);

const currentPanel = computed(() => {
  const panels: Record<Section, Component> = {
    audit: AuditPanel,
    config: ScopeConfigPanel,
    dashboard: DashboardPanel,
    findings: FindingsPanel,
  };
  return panels[section.value];
});

async function loadOptions() {
  const [projectPage, responsibilityPage, userOptions] = await Promise.all([
    listProjectsApi({ pageSize: 100 }),
    listResponsibilitiesApi({ pageSize: 100 }),
    listUsersApi(),
  ]);
  projects.value = projectPage.items;
  responsibilities.value = responsibilityPage.items;
  users.value = userOptions;
}

function switchSection(nextSection: Section) {
  section.value = nextSection;
}

onMounted(loadOptions);
</script>

<template>
  <Page title="治理看板" auto-content-height>
    <AgentToolsPageShell class="governance-shell">
      <aside class="governance-nav" aria-label="代码问题治理功能">
        <div class="nav-heading">
          <strong>代码问题治理</strong>
          <span>扫描结果与屏蔽审核</span>
        </div>
        <nav class="nav-list">
          <button
            v-for="item in sections"
            :key="item.key"
            class="nav-item"
            :class="{ active: section === item.key }"
            type="button"
            @click="switchSection(item.key)"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="governance-content">
        <component
          :is="currentPanel"
          :projects="projects"
          :responsibilities="responsibilities"
          :users="users"
          @changed="loadOptions"
        />
      </main>
    </AgentToolsPageShell>
  </Page>
</template>

<style scoped>
.governance-shell.agent-tools-page-shell {
  display: flex;
  flex-direction: row;
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.governance-nav {
  width: 196px;
  flex: 0 0 196px;
  padding: 4px 0;
  border-right: 1px solid var(--el-border-color-lighter);
}

.nav-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px 18px;
  color: var(--el-text-color-primary);
}

.nav-heading strong {
  font-size: 15px;
  font-weight: 600;
}

.nav-heading span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: block;
  width: 100%;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--el-text-color-regular);
  background: transparent;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition:
    color 0.15s,
    background-color 0.15s,
    border-color 0.15s;
}

.nav-item.active {
  border-color: var(--el-color-primary-light-7);
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  font-weight: 500;
}

.nav-item:hover:not(.active) {
  color: var(--el-color-primary);
  background: var(--el-fill-color-light);
}

.governance-content {
  min-width: 0;
  flex: 1;
  overflow: auto;
  padding: 4px 0;
}

@media (max-width: 640px) {
  .governance-shell {
    gap: 10px;
  }

  .governance-nav {
    width: 132px;
    flex-basis: 132px;
  }

  .nav-heading {
    padding-left: 8px;
  }

  .nav-item {
    padding-left: 8px;
  }
}
</style>
