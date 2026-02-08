<script lang="ts" setup>
import type { OrgNode } from '#/api/delivery-matrix';
import { onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { getTree } from '#/api/delivery-matrix';
import { ElTag, ElSkeleton, ElTabs, ElTabPane, ElButton, ElTooltip } from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import { UserAvatar } from '#/components/user-avatar';
import { useRouter } from 'vue-router';

const router = useRouter();
const matrixData = ref<OrgNode[]>([]);
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

function setAllGroups(domainId: string, collapsed: boolean, groups: OrgNode[]) {
  const domainState = ensureDomainCollapse(domainId);
  for (const g of groups || []) {
    domainState[g.id] = collapsed;
  }
}

function initDomainUI(domains: OrgNode[]) {
  const list = domains || [];
  if (!activeDomainId.value && list.length > 0) activeDomainId.value = list[0]!.id;
  for (const d of list) {
    const domainId = d.id;
    const domainState = ensureDomainCollapse(domainId);
    const groups = d.children || [];
    for (let idx = 0; idx < groups.length; idx++) {
      const g = groups[idx];
      if (g && typeof domainState[g.id] !== 'boolean') domainState[g.id] = idx !== 0;
    }
  }
}

async function fetchData() {
  loading.value = true;
  try {
    matrixData.value = await getTree();
    initDomainUI(matrixData.value);
  } finally {
    loading.value = false;
  }
}

onMounted(fetchData);

function takeUsers(users: any[], max: number) {
  const list = Array.isArray(users) ? users : [];
  if (list.length <= max) return { shown: list, more: 0 };
  return { shown: list.slice(0, max), more: list.length - max };
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return '';
  if (typeof dateStr !== 'string') return String(dateStr);
  return dateStr.length >= 10 ? dateStr.slice(5, 10) : dateStr;
}

function getMilestoneInfo(milestone: Record<string, any> | null | undefined) {
  if (!milestone) return { total: 0, completed: 0, lastIndex: 0, nextIndex: null, percent: 0 };
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
  return '未开始';
}

function getNextQG(milestone: any) {
  const info = getMilestoneInfo(milestone);
  if (info.nextIndex) {
    const date = milestone[`qg${info.nextIndex}_date`];
    return `QG${info.nextIndex} · ${formatDate(date)}`;
  }
  return '已完成';
}

function goToAdmin() {
  router.push('/delivery-matrix/admin');
}
</script>

<template>
  <Page content-class="flex flex-col gap-6 pb-16 dm-page" auto-content-height>
    <!-- Loading 状态 -->
    <div v-if="loading" class="space-y-6">
      <ElSkeleton :rows="10" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="matrixData.length === 0" class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/20 py-32">
      <IconifyIcon icon="carbon:data-vis-4" class="mb-4 text-6xl text-muted-foreground/30" />
      <div class="mb-2 text-lg font-semibold text-foreground">暂无组织架构数据</div>
      <div class="mb-6 text-sm text-muted-foreground">请先在管理页面创建组织节点</div>
      <ElButton type="primary" @click="goToAdmin">
        <IconifyIcon icon="carbon:settings" class="mr-1" />
        前往管理
      </ElButton>
    </div>

    <!-- 主内容区 -->
    <div v-else class="space-y-6">
      <ElTabs v-model="activeDomainId" class="dm-domain-tabs">
        <ElTabPane v-for="domain in matrixData" :key="domain.id" :name="domain.id">
          <template #label>
            <div class="flex items-center gap-2">
              <IconifyIcon icon="carbon:data-structured" class="text-base" />
              <span class="max-w-[160px] truncate font-semibold">{{ domain.name }}</span>
            </div>
          </template>

          <div class="mt-6 space-y-6">
            <!-- 领域信息卡片 -->
            <div class="rounded-xl border border-border bg-gradient-to-br from-card/60 to-card/40 p-5 shadow-sm backdrop-blur-sm">
              <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                      <IconifyIcon icon="carbon:data-structured" class="text-xl text-primary" />
                    </div>
                    <div class="truncate text-xl font-bold text-foreground">{{ domain.name }}</div>
                  </div>

                  <!-- 领域岗位 -->
                  <div v-if="domain.positions && domain.positions.length > 0" class="mt-5 flex flex-wrap gap-x-6 gap-y-3">
                    <div v-for="pos in domain.positions" :key="pos.name" class="flex flex-wrap items-center gap-3">
                      <div class="flex items-center gap-2">
                        <IconifyIcon icon="carbon:user-role" class="text-sm text-muted-foreground" />
                        <span class="text-sm font-semibold text-foreground">{{ pos.name }}</span>
                      </div>
                      <div class="flex flex-wrap items-center gap-2">
                        <template v-if="pos.users_info.length">
                          <div
                            v-for="u in takeUsers(pos.users_info, 6).shown"
                            :key="u.id"
                            class="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-1.5 transition-colors hover:bg-background"
                          >
                            <UserAvatar
                              :user-id="u.id"
                              :name="u.name"
                              :size="22"
                              :font-size="10"
                              :shadow="false"
                              :show-popover="true"
                            />
                            <span class="max-w-[110px] truncate text-sm font-medium text-foreground/90">{{ u.name }}</span>
                          </div>
                          <span
                            v-if="takeUsers(pos.users_info, 6).more"
                            class="rounded-lg border border-dashed border-border bg-background/40 px-3 py-1.5 text-xs font-medium text-muted-foreground"
                          >
                            +{{ takeUsers(pos.users_info, 6).more }}
                          </span>
                        </template>
                        <span v-else class="rounded-lg border border-dashed border-border bg-background/20 px-3 py-1.5 text-sm text-muted-foreground">
                          未配置
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="flex shrink-0 flex-wrap gap-2">
                  <ElButton size="small" @click="setAllGroups(domain.id, false, domain.children || [])">
                    <IconifyIcon icon="carbon:chevron-down" class="mr-1" />
                    展开全部
                  </ElButton>
                  <ElButton size="small" @click="setAllGroups(domain.id, true, domain.children || [])">
                    <IconifyIcon icon="carbon:chevron-up" class="mr-1" />
                    收起全部
                  </ElButton>
                </div>
              </div>
            </div>

            <!-- 子节点列表 -->
            <div class="space-y-4">
              <div
                v-for="group in (domain.children || [])"
                :key="group.id"
                class="overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md dark:bg-card/60"
              >
                <!-- 子节点头部 -->
                <button
                  type="button"
                  class="flex w-full items-center justify-between gap-4 bg-card/40 p-5 text-left transition-colors hover:bg-muted/10"
                  :aria-expanded="!isGroupCollapsed(domain.id, group.id)"
                  @click="toggleGroup(domain.id, group.id)"
                >
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-3">
                      <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                        <IconifyIcon icon="carbon:folder" class="text-lg text-primary" />
                      </div>
                      <span class="truncate text-lg font-bold text-foreground">{{ group.name }}</span>
                    </div>

                    <!-- 子节点岗位 -->
                    <div v-if="group.positions && group.positions.length > 0" class="mt-4 flex flex-wrap items-center gap-4">
                      <div v-for="pos in group.positions" :key="pos.name" class="flex flex-wrap items-center gap-2">
                        <span class="text-xs font-medium text-muted-foreground">{{ pos.name }}</span>
                        <template v-if="pos.users_info.length">
                          <div class="flex items-center gap-2">
                            <div class="flex -space-x-2">
                              <UserAvatar
                                v-for="u in takeUsers(pos.users_info, 4).shown"
                                :key="u.id"
                                :user-id="u.id"
                                :name="u.name"
                                :size="26"
                                :font-size="11"
                                :shadow="false"
                                :show-popover="true"
                                class="ring-2 ring-card"
                              />
                            </div>
                            <span
                              v-if="takeUsers(pos.users_info, 4).more"
                              class="rounded-full border border-border bg-background/40 px-2 py-1 text-xs text-muted-foreground"
                            >
                              +{{ takeUsers(pos.users_info, 4).more }}
                            </span>
                          </div>
                        </template>
                        <span v-else class="text-xs text-muted-foreground">-</span>
                      </div>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 text-muted-foreground">
                    <span class="hidden text-sm font-medium sm:inline">
                      {{ isGroupCollapsed(domain.id, group.id) ? '展开' : '收起' }}
                    </span>
                    <IconifyIcon
                      :icon="isGroupCollapsed(domain.id, group.id) ? 'carbon:chevron-down' : 'carbon:chevron-up'"
                      class="text-[20px]"
                    />
                  </div>
                </button>

                <!-- 孙节点列表 -->
                <div v-show="!isGroupCollapsed(domain.id, group.id)" class="border-t border-border/40 bg-muted/5 p-5">
                  <div v-if="!group.children || group.children.length === 0" class="rounded-xl border border-dashed border-border bg-background/20 py-8 text-center">
                    <IconifyIcon icon="carbon:document-blank" class="mb-2 text-3xl text-muted-foreground/30" />
                    <div class="text-sm text-muted-foreground">暂无子节点</div>
                  </div>
                  <div v-else class="space-y-3">
                    <div
                      v-for="comp in (group.children || [])"
                      :key="comp.id"
                      class="flex items-start gap-4 rounded-lg border border-border bg-card/60 p-4 transition-all hover:bg-card hover:shadow-sm"
                    >
                      <!-- 左侧图标 -->
                      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <IconifyIcon icon="carbon:cube" class="text-lg text-primary" />
                      </div>

                      <!-- 中间内容 -->
                      <div class="min-w-0 flex-1">
                        <div class="mb-3 flex items-start justify-between gap-3">
                          <div class="min-w-0">
                            <div class="truncate text-base font-bold text-foreground">{{ comp.name }}</div>
                            <div v-if="comp.description" class="mt-1 line-clamp-1 text-sm text-muted-foreground">
                              {{ comp.description }}
                            </div>
                          </div>
                          <ElTag v-if="comp.linked_project_info" type="primary" effect="light" size="small" class="shrink-0">
                            {{ comp.linked_project_info.name }}
                          </ElTag>
                        </div>

                        <!-- 岗位横向排列 -->
                        <div v-if="comp.positions && comp.positions.length > 0" class="flex flex-wrap gap-x-5 gap-y-2">
                          <div v-for="pos in comp.positions" :key="pos.name" class="flex items-center gap-2">
                            <span class="text-xs font-medium text-muted-foreground">{{ pos.name }}</span>
                            <div class="flex items-center gap-1.5">
                              <template v-if="pos.users_info.length">
                                <ElTooltip
                                  v-for="u in takeUsers(pos.users_info, 3).shown"
                                  :key="u.id"
                                  :content="u.name"
                                  placement="top"
                                >
                                  <UserAvatar
                                    :user-id="u.id"
                                    :name="u.name"
                                    :size="24"
                                    :font-size="10"
                                    :shadow="false"
                                    :show-popover="false"
                                  />
                                </ElTooltip>
                                <span
                                  v-if="takeUsers(pos.users_info, 3).more"
                                  class="ml-1 text-xs text-muted-foreground"
                                >
                                  +{{ takeUsers(pos.users_info, 3).more }}
                                </span>
                              </template>
                              <span v-else class="text-xs text-muted-foreground">-</span>
                            </div>
                          </div>
                        </div>

                        <!-- 里程碑信息 -->
                        <div v-if="comp.milestone_info" class="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                          <div class="flex items-center gap-1.5">
                            <IconifyIcon icon="carbon:time" class="text-sm" />
                            <span class="font-medium text-foreground">{{ getCurrentQG(comp.milestone_info) }}</span>
                          </div>
                          <div class="flex items-center gap-1.5">
                            <span>下一步：</span>
                            <span class="font-medium text-foreground">{{ getNextQG(comp.milestone_info) }}</span>
                          </div>
                        </div>
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
  padding: 1.5rem;
}

.dm-domain-tabs :deep(.el-tabs__header) {
  margin: 0 0 1rem;
}

.dm-domain-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 0;
}

.dm-domain-tabs :deep(.el-tabs__item) {
  height: 42px;
  line-height: 42px;
  padding: 0 16px;
  border-radius: 10px;
  margin-right: 10px;
  font-weight: 600;
  transition: all 0.2s;
}

.dm-domain-tabs :deep(.el-tabs__item:hover) {
  background: hsl(var(--muted) / 0.5);
}

.dm-domain-tabs :deep(.el-tabs__item.is-active) {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

@media (min-width: 768px) {
  .dm-page :deep(.vben-page-content) {
    padding: 2rem;
  }
}

@media (min-width: 1024px) {
  .dm-page :deep(.vben-page-content) {
    padding: 2.5rem;
  }
}
</style>
