<script lang="ts" setup>
/* eslint-disable perfectionist/sort-imports, perfectionist/sort-object-types */
import type { Component } from 'vue';
import type { Section } from './types';
import type {
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { ElIcon } from 'element-plus';
import {
  ClipboardCheck,
  FolderKanban,
  Grid2X2,
  LandPlot,
  LayoutDashboard,
  ListChecks,
  Upload,
} from 'lucide-vue-next';

import {
  listProjectsApi,
  listResponsibilitiesApi,
  listUsersApi,
} from '#/api/agent-tools/code-quality-governance';

import AgentToolsPageShell from '../components/agent-tools-page-shell.vue';
import AuditPanel from './audit-panel.vue';
import FindingsPanel from './findings-panel.vue';
import MatrixPanel from './matrix-panel.vue';
import ProjectCenterPanel from './project-center-panel.vue';
import ResponsibilityCenterPanel from './responsibility-center-panel.vue';
import ScanCenterPanel from './scan-center-panel.vue';
import WorkbenchPanel from './workbench-panel.vue';

defineOptions({ name: 'CodeQualityGovernance' });

const sections: {
  key: Section;
  hint: string;
  icon: Component;
  label: string;
}[] = [
  {
    key: 'workbench',
    label: '治理工作台',
    hint: '风险与待办',
    icon: LayoutDashboard,
  },
  {
    key: 'projects',
    label: '项目中心',
    hint: '项目 360°',
    icon: FolderKanban,
  },
  {
    key: 'responsibilities',
    label: '责任田中心',
    hint: '看护范围',
    icon: LandPlot,
  },
  {
    key: 'matrix',
    label: '治理范围矩阵',
    hint: '横向关联',
    icon: Grid2X2,
  },
  {
    key: 'scan',
    label: '扫描接入中心',
    hint: '报告入库',
    icon: Upload,
  },
  {
    key: 'findings',
    label: '问题中心',
    hint: '问题治理',
    icon: ListChecks,
  },
  {
    key: 'audit',
    label: '审核中心',
    hint: '统一待办',
    icon: ClipboardCheck,
  },
];

const panelMap: Record<Section, Component> = {
  audit: AuditPanel,
  findings: FindingsPanel,
  matrix: MatrixPanel,
  projects: ProjectCenterPanel,
  responsibilities: ResponsibilityCenterPanel,
  scan: ScanCenterPanel,
  workbench: WorkbenchPanel,
};

const section = ref<Section>('workbench');
const projects = ref<GovernanceProject[]>([]);
const responsibilities = ref<GovernanceResponsibility[]>([]);
const users = ref<UserOption[]>([]);
const optionsLoading = ref(false);

const currentPanel = computed(() => panelMap[section.value]);

async function loadOptions() {
  optionsLoading.value = true;
  try {
    const [projectPage, responsibilityPage, userOptions] = await Promise.all([
      listProjectsApi({ pageSize: 100 }),
      listResponsibilitiesApi({ pageSize: 100 }),
      listUsersApi(),
    ]);
    projects.value = projectPage.items;
    responsibilities.value = responsibilityPage.items;
    users.value = userOptions;
  } finally {
    optionsLoading.value = false;
  }
}

onMounted(loadOptions);
</script>

<template>
  <Page auto-content-height>
    <AgentToolsPageShell class="governance-shell">
      <aside class="governance-nav">
        <div class="nav-heading">
          <strong>代码问题治理</strong>
          <span>独立质量治理工作台</span>
        </div>
        <nav class="nav-list" aria-label="治理工作区">
          <button
            v-for="item in sections"
            :key="item.key"
            type="button"
            class="nav-item"
            :class="{ active: section === item.key }"
            @click="section = item.key"
          >
            <ElIcon><component :is="item.icon" /></ElIcon>
            <span>
              <b>{{ item.label }}</b>
              <small>{{ item.hint }}</small>
            </span>
          </button>
        </nav>
      </aside>

      <main v-loading="optionsLoading" class="governance-content">
        <component
          :is="currentPanel"
          :projects="projects"
          :responsibilities="responsibilities"
          :users="users"
          :refresh-options="loadOptions"
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
  gap: 18px;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.governance-nav {
  width: 218px;
  flex: 0 0 218px;
  padding-right: 10px;
  border-right: 1px solid var(--el-border-color-lighter);
}

.nav-heading {
  padding: 8px 14px 18px;
}

.nav-heading strong {
  display: block;
  color: var(--el-text-color-primary);
  font-size: 16px;
}

.nav-heading span {
  display: block;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.nav-list {
  display: grid;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 13px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--el-text-color-regular);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: 0.15s ease;
}

.nav-item:hover {
  background: var(--el-fill-color-light);
}

.nav-item.active {
  border-color: var(--el-color-primary-light-7);
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.nav-item span {
  display: grid;
  gap: 3px;
}

.nav-item b {
  font-size: 13px;
  font-weight: 500;
}

.nav-item small {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.nav-item.active small {
  color: var(--el-color-primary);
}

.governance-content {
  display: flex;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  overflow: auto;
  padding: 4px 2px 12px 0;
}

@media (max-width: 720px) {
  .governance-nav {
    width: 164px;
    flex-basis: 164px;
  }

  .nav-item {
    padding-left: 8px;
  }
}
</style>
