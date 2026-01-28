<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { getDashboardMatrix } from '#/api/delivery-matrix';
import { ElTag, ElSkeleton } from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import { UserAvatar } from '#/components/user-avatar';

const matrixData = ref<any[]>([]);
const loading = ref(false);
const activeDomainId = ref<string>('');
const collapsedByDomain = ref<Record<string, Record<string, boolean>>>({});

function ensureDomainCollapse(domainId: string) {
  if (!collapsedByDomain.value[domainId]) collapsedByDomain.value[domainId] = {};
  return collapsedByDomain.value[domainId]!;
}

function isGroupCollapsed(domainId: string, groupId: string) {
  const domainState = collapsedByDomain.value[domainId];
  return Boolean(domainState?.[groupId]);
}

function setGroupCollapsed(domainId: string, groupId: string, collapsed: boolean) {
  const domainState = ensureDomainCollapse(domainId);
  domainState[groupId] = collapsed;
}

function toggleGroup(domainId: string, groupId: string) {
  setGroupCollapsed(domainId, groupId, !isGroupCollapsed(domainId, groupId));
}

function setAllGroups(domainId: string, collapsed: boolean, groups: any[]) {
  const domainState = ensureDomainCollapse(domainId);
  for (const g of groups || []) {
    domainState[g.id] = collapsed;
  }
}

function initDomainUI(domains: any[]) {
  const list = domains || [];
  if (!activeDomainId.value && list.length > 0) activeDomainId.value = String(list[0].id);
  for (const d of list) {
    const domainId = String(d.id);
    const domainState = ensureDomainCollapse(domainId);
    const groups = d?.groups || [];
    for (let idx = 0; idx < groups.length; idx++) {
      const g = groups[idx];
      if (typeof domainState[g.id] !== 'boolean') domainState[g.id] = idx !== 0;
    }
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    const data = await getDashboardMatrix();
    matrixData.value = data;
    initDomainUI(data);
  } finally {
    loading.value = false;
  }
});

const stats = computed(() => {
  const domains = matrixData.value || [];
  let groupCount = 0;
  let componentCount = 0;
  let linkedProjectCount = 0;
  const totalPeopleKey = new Set<string>();

  for (const d of domains) {
    addUsersToSet(totalPeopleKey, d?.interface_people_info, d?.interface_people);
    const groups = d?.groups || [];
    groupCount += groups.length;
    for (const g of groups) {
      addUsersToSet(totalPeopleKey, g?.managers_info, g?.managers);
      const comps = g?.components || [];
      componentCount += comps.length;
      for (const c of comps) {
        addUsersToSet(totalPeopleKey, c?.managers_info, c?.managers);
        if (c?.project_name) linkedProjectCount += 1;
      }
    }
  }
  return [
    { label: '业务领域', value: domains.length, icon: 'carbon:wikis', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-500/10' },
    { label: '交付组件', value: componentCount, icon: 'carbon:cube', color: 'text-indigo-500', bg: 'bg-indigo-50 dark:bg-indigo-500/10' },
    { label: '涉及人员', value: totalPeopleKey.size, icon: 'carbon:user-multiple', color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-500/10' },
    { label: '已关联项目', value: linkedProjectCount, icon: 'carbon:connection-two-way', color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  ];
});

type SimpleUser = { id?: string; name: string };

function normalizeUsers(infoList?: any[], nameList?: any[]): SimpleUser[] {
  if (Array.isArray(infoList) && infoList.length > 0) {
    return infoList
      .filter((u: any) => u && (u.id || u.name))
      .map((u: any) => ({
        id: u.id ? String(u.id) : undefined,
        name: String(u.name ?? ''),
      }))
      .filter(u => u.name || u.id);
  }
  if (Array.isArray(nameList) && nameList.length > 0) {
    return nameList.filter(Boolean).map((n: any) => ({ name: String(n) }));
  }
  return [];
}

function addUsersToSet(set: Set<string>, infoList?: any[], nameList?: any[]) {
  for (const u of normalizeUsers(infoList, nameList)) {
    set.add(u.id ? `id:${u.id}` : `name:${u.name}`);
  }
}

function getDomainInterfaces(domain: any) {
  return normalizeUsers(domain?.interface_people_info, domain?.interface_people);
}

function getGroupManagers(group: any) {
  return normalizeUsers(group?.managers_info, group?.managers);
}

function getComponentManagers(comp: any) {
  return normalizeUsers(comp?.managers_info, comp?.managers);
}

function takeUsers(users: SimpleUser[], max: number) {
  const list = Array.isArray(users) ? users : [];
  if (list.length <= max) return { shown: list, more: 0 };
  return { shown: list.slice(0, max), more: list.length - max };
}

function getDomainComponentCount(domain: any) {
  const groups = domain?.groups || [];
  return (groups || []).reduce((acc: number, g: any) => acc + ((g?.components || []).length || 0), 0);
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return '';
  if (typeof dateStr !== 'string') return String(dateStr);
  return dateStr.length >= 10 ? dateStr.slice(5, 10) : dateStr; // MM-DD
}

function getMilestoneInfo(milestone: Record<string, any> | null | undefined) {
  const total = 8;
  let completed = 0;
  let lastIndex = 0;
  for (let i = 1; i <= total; i++) {
    const v = milestone?.[`qg${i}_date`];
    if (v) {
      completed += 1;
      lastIndex = i;
    }
  }
  const percent = Math.round((completed / total) * 100);
  const nextIndex = lastIndex < total ? lastIndex + 1 : null;
  return { total, completed, lastIndex, nextIndex, percent };
}

function getCurrentQG(milestone: any) {
  const info = getMilestoneInfo(milestone);
  if (info.lastIndex) return `QG${info.lastIndex}`;
  return '规划中';
}

function getNextQG(milestone: any) {
  const info = getMilestoneInfo(milestone);
  if (info.nextIndex) {
    const date = milestone[`qg${info.nextIndex}_date`];
    return `QG${info.nextIndex} · ${formatDate(date)}`;
  }
  return '已完成';
}
</script>

<template>
  <Page content-class="flex flex-col gap-10 pb-16 dm-page">
    <div class="grid grid-cols-2 gap-4 md:grid-cols-4 lg:gap-6">
      <div
        v-for="stat in stats"
        :key="stat.label"
        class="flex items-center gap-4 rounded-xl border border-border bg-card p-5 shadow-sm dark:bg-card/40"
      >
        <div :class="`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stat.bg}`">
          <IconifyIcon :icon="stat.icon" :class="`text-[22px] ${stat.color}`" />
        </div>
        <div class="min-w-0">
          <div class="text-xs font-medium text-muted-foreground">{{ stat.label }}</div>
          <div class="mt-1 text-2xl font-bold tabular-nums text-foreground">{{ stat.value }}</div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="space-y-6">
      <ElSkeleton :rows="10" animated />
    </div>

    <div v-else-if="matrixData.length === 0" class="flex flex-col items-center justify-center py-28">
      <IconifyIcon icon="carbon:data-vis-4" class="text-5xl text-muted-foreground/30" />
      <div class="mt-4 text-sm font-medium text-muted-foreground">暂无交付矩阵数据</div>
    </div>

    <div v-else class="space-y-10">
      <ElTabs v-model="activeDomainId" class="dm-domain-tabs">
        <ElTabPane v-for="domain in matrixData" :key="domain.id" :name="domain.id">
          <template #label>
            <div class="flex items-center gap-2">
              <span class="max-w-[180px] truncate font-semibold">{{ domain.name }}</span>
              <span class="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                {{ (domain.groups || []).length }}
              </span>
            </div>
          </template>

          <div class="mt-6 space-y-10">
            <div class="flex flex-col gap-4 rounded-2xl border border-border bg-card/40 p-6 shadow-sm dark:bg-card/20">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <div class="flex items-center gap-3">
                    <div class="h-6 w-1.5 rounded-full bg-primary"></div>
                    <div class="truncate text-xl font-semibold text-foreground">{{ domain.name }}</div>
                  </div>
                  <div class="mt-1 text-sm text-muted-foreground">
                    <span>项目群 {{ (domain.groups || []).length }}</span>
                    <span class="mx-2 text-muted-foreground/30">•</span>
                    <span>组件 {{ getDomainComponentCount(domain) }}</span>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    class="rounded-lg border border-border bg-background/40 px-3 py-1.5 text-xs font-medium text-foreground/75 hover:bg-background/70"
                    @click="setAllGroups(domain.id, false, domain.groups)"
                  >
                    展开全部
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-border bg-background/40 px-3 py-1.5 text-xs font-medium text-foreground/75 hover:bg-background/70"
                    @click="setAllGroups(domain.id, true, domain.groups)"
                  >
                    收起全部
                  </button>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
                <span class="text-xs font-medium text-muted-foreground">领域接口人</span>
                <div class="flex flex-wrap items-center gap-2">
                  <template v-if="getDomainInterfaces(domain).length">
                    <div
                      v-for="u in takeUsers(getDomainInterfaces(domain), 8).shown"
                      :key="u.id || u.name"
                      class="flex items-center gap-2 rounded-full border border-border bg-background/50 px-2 py-1.5"
                    >
                      <UserAvatar
                        :user-id="u.id"
                        :name="u.name"
                        :size="22"
                        :font-size="10"
                        :shadow="false"
                        :show-popover="Boolean(u.id)"
                      />
                      <span class="max-w-[140px] truncate text-xs font-medium text-foreground/80">{{ u.name || u.id }}</span>
                    </div>
                    <span
                      v-if="takeUsers(getDomainInterfaces(domain), 8).more"
                      class="rounded-full border border-border bg-background/40 px-2 py-1.5 text-xs text-muted-foreground"
                    >
                      +{{ takeUsers(getDomainInterfaces(domain), 8).more }}
                    </span>
                  </template>
                  <span v-else class="text-xs text-muted-foreground">未配置</span>
                </div>
              </div>
            </div>

            <div class="space-y-6">
              <div
                v-for="group in (domain.groups || [])"
                :key="group.id"
                class="overflow-hidden rounded-2xl border border-border bg-card shadow-sm dark:bg-card/60"
              >
                <button
                  type="button"
                  class="flex w-full items-center justify-between gap-4 p-6 text-left hover:bg-muted/10"
                  :aria-expanded="!isGroupCollapsed(domain.id, group.id)"
                  @click="toggleGroup(domain.id, group.id)"
                >
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <IconifyIcon icon="carbon:folder" class="text-[18px] text-primary" />
                      <span class="truncate text-lg font-semibold text-foreground">{{ group.name }}</span>
                      <span class="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                        {{ (group.components || []).length }} 组件
                      </span>
                    </div>
                    <div class="mt-3 flex flex-wrap items-center gap-2">
                      <span class="text-xs font-medium text-muted-foreground">负责人</span>
                      <template v-if="getGroupManagers(group).length">
                        <div class="flex items-center gap-2">
                          <div class="flex -space-x-2">
                            <UserAvatar
                              v-for="u in takeUsers(getGroupManagers(group), 4).shown"
                              :key="u.id || u.name"
                              :user-id="u.id"
                              :name="u.name"
                              :size="26"
                              :font-size="11"
                              :shadow="false"
                              :show-popover="Boolean(u.id)"
                              class="ring-2 ring-card"
                            />
                          </div>
                          <span
                            v-if="takeUsers(getGroupManagers(group), 4).more"
                            class="rounded-full border border-border bg-background/40 px-2 py-0.5 text-xs text-muted-foreground"
                          >
                            +{{ takeUsers(getGroupManagers(group), 4).more }}
                          </span>
                        </div>
                      </template>
                      <span v-else class="text-xs text-muted-foreground">-</span>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 text-muted-foreground">
                    <span class="hidden text-xs font-medium sm:inline">
                      {{ isGroupCollapsed(domain.id, group.id) ? '展开' : '收起' }}
                    </span>
                    <IconifyIcon
                      :icon="isGroupCollapsed(domain.id, group.id) ? 'carbon:chevron-down' : 'carbon:chevron-up'"
                      class="text-[20px]"
                    />
                  </div>
                </button>

                <div v-show="!isGroupCollapsed(domain.id, group.id)" class="border-t border-border/40 p-6 pt-5">
                  <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                    <div
                      v-for="comp in (group.components || [])"
                      :key="comp.id"
                      class="flex flex-col rounded-2xl border border-border bg-background/40 shadow-sm transition-shadow hover:shadow-md dark:bg-background/10"
                    >
                      <div class="flex items-start justify-between gap-3 border-b border-border/40 p-5">
                        <div class="min-w-0">
                          <div class="truncate text-base font-semibold text-foreground">{{ comp.name }}</div>
                          <div v-if="comp.remark" class="mt-1 truncate text-xs text-muted-foreground">{{ comp.remark }}</div>
                        </div>
                        <ElTag
                          v-if="comp.project_name"
                          type="primary"
                          effect="plain"
                          size="small"
                          class="shrink-0"
                        >
                          {{ comp.project_name }}
                        </ElTag>
                      </div>

                      <div class="flex flex-1 flex-col gap-4 p-5">
                        <div class="flex items-center justify-between">
                          <div class="text-xs font-medium text-muted-foreground">交付负责人</div>
                          <IconifyIcon icon="carbon:collaborate" class="text-[18px] text-muted-foreground/40" />
                        </div>

                        <div class="flex flex-wrap gap-2">
                          <template v-if="getComponentManagers(comp).length">
                            <div
                              v-for="u in takeUsers(getComponentManagers(comp), 4).shown"
                              :key="u.id || u.name"
                              class="flex items-center gap-2 rounded-xl border border-border bg-background/40 px-2.5 py-2"
                            >
                              <UserAvatar
                                :user-id="u.id"
                                :name="u.name"
                                :size="26"
                                :font-size="11"
                                :shadow="false"
                                :show-popover="Boolean(u.id)"
                              />
                              <span class="max-w-[140px] truncate text-sm font-medium text-foreground/80">{{ u.name || u.id }}</span>
                            </div>
                            <div
                              v-if="takeUsers(getComponentManagers(comp), 4).more"
                              class="flex items-center rounded-xl border border-dashed border-border bg-background/20 px-2.5 py-2 text-xs text-muted-foreground"
                            >
                              +{{ takeUsers(getComponentManagers(comp), 4).more }} 人
                            </div>
                          </template>
                          <div v-else class="w-full rounded-xl border border-dashed border-border bg-background/20 px-3 py-6 text-center text-xs text-muted-foreground">
                            待分配
                          </div>
                        </div>
                      </div>

                      <div class="border-t border-border/40 bg-muted/5 px-5 py-3">
                        <div v-if="comp.milestone" class="flex items-center justify-between text-xs">
                          <div class="flex items-center gap-2 text-muted-foreground">
                            <IconifyIcon icon="carbon:time" class="text-[14px]" />
                            <span class="font-medium text-foreground/80">{{ getCurrentQG(comp.milestone) }}</span>
                          </div>
                          <div class="text-muted-foreground">
                            下一步：<span class="font-medium text-foreground/80">{{ getNextQG(comp.milestone) }}</span>
                          </div>
                        </div>
                        <div v-else class="text-center text-xs text-muted-foreground/70">无里程碑</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>

<style scoped>
.dm-page :deep(.vben-page-content) {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

.dm-domain-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.dm-domain-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 0;
}

.dm-domain-tabs :deep(.el-tabs__item) {
  height: 40px;
  line-height: 40px;
  padding: 0 14px;
  border-radius: 10px;
  margin-right: 8px;
}

.dm-domain-tabs :deep(.el-tabs__item.is-active) {
  background: hsl(var(--muted));
}

@media (min-width: 1024px) {
  .dm-page :deep(.vben-page-content) {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}
</style>
