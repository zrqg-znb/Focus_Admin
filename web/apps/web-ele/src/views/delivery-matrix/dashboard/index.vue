<script lang="ts" setup>
import type { OrgNode, PositionStaff } from '#/api/delivery-matrix';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElInput,
  ElSkeleton,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
} from 'element-plus';

import { getTree } from '#/api/delivery-matrix';
import { UserAvatar } from '#/components/user-avatar';

interface MatrixNode extends OrgNode {
  description_html?: string;
  children?: MatrixNode[];
}

type PositionUser = PositionStaff['users_info'][number];

const HIGHLIGHT_POSITION_NAMES = new Set(['pl', 'xm']);

const router = useRouter();
const matrixData = ref<MatrixNode[]>([]);
const loading = ref(false);
const activeDomainId = ref<string>('');
const collapsedByDomain = ref<Record<string, Record<string, boolean>>>({});
const searchQuery = ref('');

function sanitizeRichTextHtml(input: unknown) {
  const raw = String(input ?? '').trim();
  if (!raw) return '';

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(raw, 'text/html');
    const blockedTags = ['script', 'style', 'iframe', 'object', 'embed'];

    blockedTags.forEach((tag) => {
      doc.querySelectorAll(tag).forEach((node) => node.remove());
    });

    doc.querySelectorAll('*').forEach((element) => {
      [...element.attributes].forEach((attribute) => {
        const name = attribute.name.toLowerCase();
        const value = String(attribute.value || '')
          .trim()
          .toLowerCase();
        if (name.startsWith('on')) {
          element.removeAttribute(attribute.name);
          return;
        }
        if (
          (name === 'href' || name === 'src') &&
          value.startsWith('javascript:')
        ) {
          element.removeAttribute(attribute.name);
        }
      });
    });

    const html = doc.body.innerHTML || '';
    const text = (doc.body.textContent || '').replaceAll(/\s+/g, ' ').trim();
    const hasVisibleMedia = Boolean(
      doc.body.querySelector('img, video, audio, iframe, object, embed'),
    );

    if (!html || (!text && !hasVisibleMedia)) {
      return '';
    }

    return html;
  } catch {
    return '';
  }
}

function decorateMatrixNodes(nodes: OrgNode[]): MatrixNode[] {
  return (nodes || []).map((node) => ({
    ...node,
    description_html: sanitizeRichTextHtml(node.description),
    children: decorateMatrixNodes(node.children || []),
  }));
}

function normalizePositionName(name: unknown) {
  return String(name ?? '')
    .trim()
    .toLowerCase();
}

function isHighlightedPosition(name: unknown) {
  return HIGHLIGHT_POSITION_NAMES.has(normalizePositionName(name));
}

const filteredData = computed<MatrixNode[]>(() => {
  const normalizedQuery = searchQuery.value.trim();
  if (!normalizedQuery) return matrixData.value;
  const query = normalizedQuery.toLowerCase();

  return matrixData.value
    .map((domain) => {
      // Filter children (Groups)
      const filteredGroups = (domain.children || [])
        .map((group) => {
          // Filter children (Components)
          const filteredComps = (group.children || []).filter((comp) =>
            comp.name.toLowerCase().includes(query),
          );

          // Keep group if it matches or has matching children
          if (
            group.name.toLowerCase().includes(query) ||
            filteredComps.length > 0
          ) {
            return { ...group, children: filteredComps };
          }
          return null;
        })
        .filter(Boolean) as MatrixNode[];

      // Keep domain if it matches or has matching children
      if (
        domain.name.toLowerCase().includes(query) ||
        filteredGroups.length > 0
      ) {
        return { ...domain, children: filteredGroups };
      }
      return null;
    })
    .filter(Boolean) as MatrixNode[];
});

function ensureDomainCollapse(domainId: string) {
  if (!collapsedByDomain.value[domainId])
    collapsedByDomain.value[domainId] = {};
  return collapsedByDomain.value[domainId]!;
}

function isGroupCollapsed(domainId: string, groupId: string) {
  const domainState = collapsedByDomain.value[domainId];
  return Boolean(domainState?.[groupId]);
}

function setGroupCollapsed(
  domainId: string,
  groupId: string,
  collapsed: boolean,
) {
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
  if (!activeDomainId.value && list.length > 0)
    activeDomainId.value = list[0]!.id;
  for (const d of list) {
    const domainId = d.id;
    const domainState = ensureDomainCollapse(domainId);
    const groups = d.children || [];
    for (const [idx, g] of groups.entries()) {
      if (g && typeof domainState[g.id] !== 'boolean')
        domainState[g.id] = idx !== 0;
    }
  }
}

async function fetchData() {
  loading.value = true;
  try {
    matrixData.value = decorateMatrixNodes(await getTree());
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

function takePositionUsers(users: PositionUser[], max: number) {
  return takeUsers(users, max);
}

function goToProjectReport() {
  router.push('/project-manager/project-report');
}

function goToAdmin() {
  router.push('/delivery-matrix/admin');
}
</script>

<template>
  <!-- eslint-disable vue/no-v-html, vue/html-closing-bracket-newline -->
  <Page content-class="flex flex-col gap-6 pb-16 dm-page" auto-content-height>
    <!-- Loading 状态 -->
    <div v-if="loading" class="space-y-6">
      <ElSkeleton :rows="10" animated />
    </div>

    <!-- 空状态 -->
    <div
      v-else-if="matrixData.length === 0"
      class="border-border bg-card/20 flex flex-col items-center justify-center rounded-2xl border border-dashed py-32"
    >
      <IconifyIcon
        icon="carbon:data-vis-4"
        class="text-muted-foreground/30 mb-4 text-6xl"
      />
      <div class="text-foreground mb-2 text-lg font-semibold">
        暂无组织架构数据
      </div>
      <div class="text-muted-foreground mb-6 text-sm">
        请先在管理页面创建组织节点
      </div>
      <ElButton type="primary" @click="goToAdmin">
        <IconifyIcon icon="carbon:settings" class="mr-1" />
        前往管理
      </ElButton>
    </div>

    <!-- 主内容区 -->
    <div v-else class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="w-64">
          <ElInput
            v-model="searchQuery"
            placeholder="搜索节点..."
            clearable
            prefix-icon="carbon:search"
          />
        </div>
      </div>

      <ElTabs v-model="activeDomainId" class="dm-domain-tabs">
        <ElTabPane
          v-for="domain in filteredData"
          :key="domain.id"
          :name="domain.id"
        >
          <template #label>
            <div class="flex items-center gap-2">
              <IconifyIcon icon="carbon:data-structured" class="text-base" />
              <span class="max-w-[160px] truncate font-semibold">{{
                domain.name
              }}</span>
            </div>
          </template>

          <div class="mt-6 space-y-6">
            <!-- 领域信息卡片 -->
            <div
              class="border-border from-card/60 to-card/40 rounded-xl border bg-gradient-to-br p-5 shadow-sm backdrop-blur-sm"
            >
              <div
                class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-3">
                    <div
                      class="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-xl"
                    >
                      <IconifyIcon
                        icon="carbon:data-structured"
                        class="text-primary text-xl"
                      />
                    </div>
                    <div class="text-foreground truncate text-xl font-bold">
                      {{ domain.name }}
                    </div>
                  </div>

                  <!-- 领域岗位 -->
                  <div
                    v-if="domain.positions && domain.positions.length > 0"
                    class="mt-5 flex flex-wrap gap-x-6 gap-y-3"
                  >
                    <div
                      v-for="pos in domain.positions"
                      :key="pos.name"
                      class="flex flex-wrap items-center gap-3"
                    >
                      <div class="flex items-center gap-2">
                        <IconifyIcon
                          icon="carbon:user-role"
                          class="text-muted-foreground text-sm"
                        />
                        <span class="text-foreground text-sm font-semibold">{{
                          pos.name
                        }}</span>
                      </div>
                      <div class="flex flex-wrap items-center gap-2">
                        <template v-if="pos.users_info.length > 0">
                          <div
                            v-for="u in takeUsers(pos.users_info, 6).shown"
                            :key="u.id"
                            class="border-border bg-background/60 hover:bg-background flex items-center gap-2 rounded-lg border px-3 py-1.5 transition-colors"
                          >
                            <UserAvatar
                              :user-id="u.id"
                              :name="u.name"
                              :size="22"
                              :font-size="10"
                              :shadow="false"
                              :show-popover="true"
                            />
                            <span
                              class="text-foreground/90 max-w-[110px] truncate text-sm font-medium"
                              >{{ u.name }}</span
                            >
                          </div>
                          <span
                            v-if="takeUsers(pos.users_info, 6).more"
                            class="border-border bg-background/40 text-muted-foreground rounded-lg border border-dashed px-3 py-1.5 text-xs font-medium"
                          >
                            +{{ takeUsers(pos.users_info, 6).more }}
                          </span>
                        </template>
                        <span
                          v-else
                          class="border-border bg-background/20 text-muted-foreground rounded-lg border border-dashed px-3 py-1.5 text-sm"
                        >
                          未配置
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="flex shrink-0 flex-wrap gap-2">
                  <ElButton
                    size="small"
                    @click="
                      setAllGroups(domain.id, false, domain.children || [])
                    "
                  >
                    <IconifyIcon icon="carbon:chevron-down" class="mr-1" />
                    展开全部
                  </ElButton>
                  <ElButton
                    size="small"
                    @click="
                      setAllGroups(domain.id, true, domain.children || [])
                    "
                  >
                    <IconifyIcon icon="carbon:chevron-up" class="mr-1" />
                    收起全部
                  </ElButton>
                </div>
              </div>
            </div>

            <!-- 子节点列表 -->
            <div class="space-y-4">
              <div
                v-for="group in domain.children || []"
                :key="group.id"
                class="border-border bg-card dark:bg-card/60 overflow-hidden rounded-xl border shadow-sm transition-shadow hover:shadow-md"
              >
                <!-- 子节点头部 -->
                <button
                  type="button"
                  class="bg-card/40 hover:bg-muted/10 flex w-full items-center justify-between gap-4 p-5 text-left transition-colors"
                  :aria-expanded="!isGroupCollapsed(domain.id, group.id)"
                  @click="toggleGroup(domain.id, group.id)"
                >
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-3">
                      <div
                        class="bg-primary/10 flex h-9 w-9 items-center justify-center rounded-lg"
                      >
                        <IconifyIcon
                          icon="carbon:folder"
                          class="text-primary text-lg"
                        />
                      </div>
                      <span
                        class="text-foreground truncate text-lg font-bold"
                        >{{ group.name }}</span
                      >
                    </div>

                    <!-- 子节点岗位 -->
                    <div
                      v-if="group.positions && group.positions.length > 0"
                      class="mt-4 flex flex-wrap items-center gap-4"
                    >
                      <div
                        v-for="pos in group.positions"
                        :key="pos.name"
                        class="flex flex-wrap items-center gap-2"
                      >
                        <span
                          class="text-muted-foreground text-xs font-medium"
                          >{{ pos.name }}</span
                        >
                        <template v-if="pos.users_info.length > 0">
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
                                class="ring-card ring-2"
                              />
                            </div>
                            <span
                              v-if="takeUsers(pos.users_info, 4).more"
                              class="border-border bg-background/40 text-muted-foreground rounded-full border px-2 py-1 text-xs"
                            >
                              +{{ takeUsers(pos.users_info, 4).more }}
                            </span>
                          </div>
                        </template>
                        <span v-else class="text-muted-foreground text-xs"
                          >-</span
                        >
                      </div>
                    </div>
                  </div>

                  <div class="text-muted-foreground flex items-center gap-2">
                    <span class="hidden text-sm font-medium sm:inline">
                      {{
                        isGroupCollapsed(domain.id, group.id) ? '展开' : '收起'
                      }}
                    </span>
                    <IconifyIcon
                      :icon="
                        isGroupCollapsed(domain.id, group.id)
                          ? 'carbon:chevron-down'
                          : 'carbon:chevron-up'
                      "
                      class="text-[20px]"
                    />
                  </div>
                </button>

                <!-- 孙节点列表 -->
                <div
                  v-show="!isGroupCollapsed(domain.id, group.id)"
                  class="border-border/40 bg-muted/5 border-t p-5"
                >
                  <div
                    v-if="!group.children || group.children.length === 0"
                    class="border-border bg-background/20 rounded-xl border border-dashed py-8 text-center"
                  >
                    <IconifyIcon
                      icon="carbon:document-blank"
                      class="text-muted-foreground/30 mb-2 text-3xl"
                    />
                    <div class="text-muted-foreground text-sm">暂无子节点</div>
                  </div>
                  <div v-else class="space-y-3">
                    <div
                      v-for="comp in group.children || []"
                      :key="comp.id"
                      class="border-border bg-card/60 hover:bg-card flex items-start gap-4 rounded-lg border p-4 transition-all hover:shadow-sm"
                    >
                      <!-- 左侧图标 -->
                      <div
                        class="bg-primary/10 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                      >
                        <IconifyIcon
                          icon="carbon:cube"
                          class="text-primary text-lg"
                        />
                      </div>

                      <!-- 中间内容 -->
                      <div class="min-w-0 flex-1">
                        <div
                          class="mb-3 flex items-start justify-between gap-3"
                        >
                          <div class="min-w-0">
                            <div
                              class="text-foreground truncate text-base font-bold"
                            >
                              {{ comp.name }}
                            </div>
                            <!-- eslint-disable-next-line vue/no-v-html -->
                            <div
                              v-if="comp.description_html"
                              class="rich-text-preview text-muted-foreground mt-1 line-clamp-2 text-sm"
                              v-html="comp.description_html"
                            ></div>
                          </div>
                          <ElTag
                            v-if="comp.linked_project_info"
                            type="primary"
                            effect="light"
                            size="small"
                            class="shrink-0"
                          >
                            {{ comp.linked_project_info.name }}
                          </ElTag>
                        </div>

                        <!-- 岗位横向排列 -->
                        <div
                          v-if="comp.positions && comp.positions.length > 0"
                          class="flex flex-wrap gap-x-5 gap-y-2"
                        >
                          <div
                            v-for="pos in comp.positions"
                            :key="pos.id || pos.name"
                            class="min-w-0"
                          >
                            <template v-if="isHighlightedPosition(pos.name)">
                              <div
                                class="border-primary/20 bg-primary/5 flex min-w-0 flex-col gap-2 rounded-xl border px-3 py-2 shadow-sm"
                              >
                                <div class="flex items-center gap-2">
                                  <IconifyIcon
                                    icon="carbon:user-role"
                                    class="text-primary text-sm"
                                  />
                                  <span
                                    class="text-foreground text-xs font-bold"
                                  >
                                    {{ pos.name }}
                                  </span>
                                </div>

                                <div
                                  class="flex flex-wrap items-center gap-1.5"
                                >
                                  <template v-if="pos.users_info.length > 0">
                                    <ElTooltip
                                      v-for="u in takePositionUsers(
                                        pos.users_info,
                                        3,
                                      ).shown"
                                      :key="u.id"
                                      :content="u.name"
                                      placement="top"
                                    >
                                      <div
                                        class="border-border bg-background/80 flex items-center gap-2 rounded-full border px-2.5 py-1"
                                      >
                                        <UserAvatar
                                          :user-id="u.id"
                                          :name="u.name"
                                          :size="20"
                                          :font-size="9"
                                          :shadow="false"
                                          :show-popover="false"
                                        />
                                        <span
                                          class="text-foreground max-w-[96px] truncate text-xs font-bold"
                                          >{{ u.name }}</span
                                        >
                                      </div>
                                    </ElTooltip>
                                    <span
                                      v-if="
                                        takePositionUsers(pos.users_info, 3)
                                          .more
                                      "
                                      class="border-border bg-background/50 text-muted-foreground rounded-full border border-dashed px-2 py-1 text-xs font-medium"
                                    >
                                      +{{
                                        takePositionUsers(pos.users_info, 3)
                                          .more
                                      }}
                                    </span>
                                  </template>
                                  <span
                                    v-else
                                    class="border-border bg-background/20 text-muted-foreground rounded-full border border-dashed px-2 py-1 text-xs font-medium"
                                  >
                                    未配置
                                  </span>
                                </div>
                              </div>
                            </template>
                            <template v-else>
                              <div class="flex items-center gap-2">
                                <IconifyIcon
                                  icon="carbon:user-role"
                                  class="text-muted-foreground text-sm"
                                />
                                <span
                                  class="text-muted-foreground text-xs font-medium"
                                  >{{ pos.name }}</span
                                >
                                <div class="flex items-center gap-1.5">
                                  <template v-if="pos.users_info.length > 0">
                                    <ElTooltip
                                      v-for="u in takeUsers(pos.users_info, 3)
                                        .shown"
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
                                      class="text-muted-foreground ml-1 text-xs"
                                    >
                                      +{{ takeUsers(pos.users_info, 3).more }}
                                    </span>
                                  </template>
                                  <span
                                    v-else
                                    class="text-muted-foreground text-xs"
                                    >-</span
                                  >
                                </div>
                              </div>
                            </template>
                          </div>
                        </div>

                        <!-- 里程碑信息 -->
                        <div
                          class="text-muted-foreground mt-3 flex items-center gap-4 text-xs"
                        >
                          <ElButton
                            link
                            type="primary"
                            size="small"
                            @click="goToProjectReport"
                          >
                            <IconifyIcon
                              icon="carbon:document-view"
                              class="mr-1"
                            />
                            查看项目报告
                          </ElButton>
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

.rich-text-preview :deep(p) {
  margin: 0;
}

.rich-text-preview :deep(p + p) {
  margin-top: 0.35rem;
}

.rich-text-preview :deep(a) {
  color: hsl(var(--primary));
  text-decoration: underline;
  word-break: break-word;
}

.rich-text-preview :deep(ul),
.rich-text-preview :deep(ol) {
  margin: 0;
  padding-left: 1.25rem;
}

.rich-text-preview :deep(blockquote) {
  margin: 0;
  padding-left: 0.75rem;
  border-left: 2px solid hsl(var(--border));
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
