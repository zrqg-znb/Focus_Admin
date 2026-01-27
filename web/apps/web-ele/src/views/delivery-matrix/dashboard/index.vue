<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { getDashboardMatrix } from '#/api/delivery-matrix';
import { ElTag, ElTooltip, ElSkeleton, ElAvatar } from 'element-plus';
import { IconifyIcon } from '@vben/icons';

const matrixData = ref<any[]>([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    matrixData.value = await getDashboardMatrix();
  } finally {
    loading.value = false;
  }
});

const stats = computed(() => {
  const domains = matrixData.value || [];
  let groupCount = 0;
  let componentCount = 0;
  let linkedProjectCount = 0;
  let totalManagers = new Set();

  for (const d of domains) {
    (d.interface_people || []).forEach((p: string) => totalManagers.add(p));
    const groups = d?.groups || [];
    groupCount += groups.length;
    for (const g of groups) {
      (g.managers || []).forEach((p: string) => totalManagers.add(p));
      const comps = g?.components || [];
      componentCount += comps.length;
      for (const c of comps) {
        (c.managers || []).forEach((p: string) => totalManagers.add(p));
        if (c?.project_name) linkedProjectCount += 1;
      }
    }
  }
  return [
    { label: '业务领域', value: domains.length, icon: 'carbon:wikis', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-500/10' },
    { label: '交付组件', value: componentCount, icon: 'carbon:cube', color: 'text-indigo-500', bg: 'bg-indigo-50 dark:bg-indigo-500/10' },
    { label: '涉及人员', value: totalManagers.size, icon: 'carbon:user-multiple', color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-500/10' },
    { label: '已关联项目', value: linkedProjectCount, icon: 'carbon:connection-two-way', color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  ];
});

function safeJoin(arr: any[], fallback = '') {
  if (!Array.isArray(arr) || arr.length === 0) return fallback;
  return arr.join(', ');
}

function getInitials(name: string) {
  return name ? name.substring(0, 1).toUpperCase() : '?';
}

// Generate consistent pastel colors from name
function getAvatarColor(name: string) {
  const colors = [
    '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#6366f1'
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
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
  <Page content-class="flex flex-col gap-8 pb-12">
    <!-- Header Stats -->
    <div class="grid grid-cols-2 gap-4 md:grid-cols-4 lg:gap-6">
      <div 
        v-for="stat in stats" 
        :key="stat.label" 
        class="flex items-center gap-4 rounded-xl border border-border bg-card p-4 shadow-sm transition-all hover:shadow-md dark:bg-card/50"
      >
        <div :class="`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${stat.bg}`">
          <IconifyIcon :icon="stat.icon" :class="`text-2xl ${stat.color}`" />
        </div>
        <div>
          <p class="text-xs font-medium text-muted-foreground">{{ stat.label }}</p>
          <p class="text-xl font-bold tracking-tight text-foreground">{{ stat.value }}</p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="space-y-10">
      <ElSkeleton :rows="3" animated />
    </div>

    <div v-else-if="matrixData.length === 0" class="flex flex-col items-center justify-center py-20">
      <IconifyIcon icon="carbon:data-vis-4" class="text-4xl text-muted-foreground/30" />
      <p class="mt-4 text-sm text-muted-foreground">暂无交付矩阵数据</p>
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-10">
      <section v-for="domain in matrixData" :key="domain.id" class="space-y-6">
        <!-- Domain Header with Interface People -->
        <div class="flex flex-col gap-4 rounded-lg bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between border border-border/50">
          <div class="flex items-center gap-3">
            <div class="h-8 w-1.5 rounded-full bg-blue-500"></div>
            <h2 class="text-xl font-bold text-foreground">{{ domain.name }}</h2>
          </div>
          
          <!-- Domain Interface People -->
          <div class="flex items-center gap-3 rounded-md bg-background px-4 py-2 shadow-sm border border-border/50">
            <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">领域接口人</span>
            <div class="h-4 w-px bg-border"></div>
            <div class="flex -space-x-2 overflow-hidden">
              <template v-if="domain.interface_people && domain.interface_people.length">
                <ElTooltip 
                  v-for="person in domain.interface_people" 
                  :key="person" 
                  :content="person" 
                  placement="top"
                >
                  <div 
                    class="flex h-8 w-8 items-center justify-center rounded-full border-2 border-background text-xs font-bold text-white shadow-sm ring-1 ring-black/5"
                    :style="{ backgroundColor: getAvatarColor(person) }"
                  >
                    {{ getInitials(person) }}
                  </div>
                </ElTooltip>
              </template>
              <span v-else class="text-xs text-muted-foreground">未指定</span>
            </div>
          </div>
        </div>

        <!-- Groups -->
        <div class="pl-0 sm:pl-4 space-y-8">
          <div v-for="group in (domain.groups || [])" :key="group.id" class="space-y-4">
            
            <!-- Group Header with Managers -->
            <div class="flex items-center gap-4 border-b border-border border-dashed pb-2">
              <div class="flex items-center gap-2">
                <IconifyIcon icon="carbon:folder" class="text-muted-foreground" />
                <h3 class="text-base font-semibold text-foreground/90">{{ group.name }}</h3>
              </div>
              
              <div class="flex items-center gap-2 rounded-full bg-muted/50 px-3 py-1">
                <span class="text-[10px] font-medium text-muted-foreground">负责人</span>
                <div class="flex items-center gap-1.5">
                   <template v-if="group.managers && group.managers.length">
                      <span v-for="mgr in group.managers" :key="mgr" class="flex items-center gap-1">
                         <div class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: getAvatarColor(mgr) }"></div>
                         <span class="text-xs font-medium text-foreground/80">{{ mgr }}</span>
                      </span>
                   </template>
                   <span v-else class="text-xs text-muted-foreground">-</span>
                </div>
              </div>
            </div>

            <!-- Components Grid (Contact Focused) -->
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <div
                v-for="comp in (group.components || [])"
                :key="comp.id"
                class="flex flex-col rounded-xl border border-border bg-card shadow-sm transition-all hover:border-primary/40 hover:shadow-md dark:bg-card/80"
              >
                <!-- Card Header -->
                <div class="flex items-start justify-between border-b border-border/40 p-4 bg-muted/5">
                  <div class="min-w-0">
                    <h4 class="truncate font-bold text-foreground">{{ comp.name }}</h4>
                    <div class="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                       <IconifyIcon icon="carbon:tag" />
                       <span class="truncate">{{ comp.remark || '无备注' }}</span>
                    </div>
                  </div>
                  <ElTag 
                    v-if="comp.project_name" 
                    type="primary" 
                    effect="plain" 
                    size="small" 
                    class="shrink-0 !bg-transparent"
                  >
                    {{ comp.project_name }}
                  </ElTag>
                </div>

                <!-- Card Body: Contact Info (Primary Focus) -->
                <div class="flex flex-1 flex-col justify-center gap-3 p-5">
                   <div class="flex items-center justify-between">
                      <span class="text-xs font-medium text-muted-foreground">交付负责人</span>
                      <IconifyIcon icon="carbon:user-filled" class="text-muted-foreground/20 text-xl" />
                   </div>
                   
                   <div class="flex flex-wrap gap-2">
                      <template v-if="comp.managers && comp.managers.length">
                        <div 
                          v-for="mgr in comp.managers" 
                          :key="mgr" 
                          class="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2 border border-border/50 transition-colors hover:bg-muted/80 hover:border-primary/20"
                        >
                           <div 
                              class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white shadow-sm"
                              :style="{ backgroundColor: getAvatarColor(mgr) }"
                           >
                              {{ getInitials(mgr) }}
                           </div>
                           <div class="flex flex-col">
                              <span class="text-sm font-semibold text-foreground">{{ mgr }}</span>
                              <span class="text-[10px] text-muted-foreground leading-none">Manager</span>
                           </div>
                        </div>
                      </template>
                      <div v-else class="flex w-full items-center justify-center rounded-lg border border-dashed border-border py-3 text-xs text-muted-foreground">
                         待分配
                      </div>
                   </div>
                </div>

                <!-- Card Footer: Milestone (Secondary Focus) -->
                <div class="mt-auto border-t border-border/40 bg-muted/5 p-3">
                   <div v-if="comp.milestone" class="flex items-center justify-between text-xs">
                      <div class="flex items-center gap-1.5">
                         <div 
                            class="h-2 w-2 rounded-full animate-pulse"
                            :class="getMilestoneInfo(comp.milestone).percent === 100 ? 'bg-green-500' : 'bg-blue-500'"
                         ></div>
                         <span class="font-medium text-foreground">{{ getCurrentQG(comp.milestone) }}</span>
                      </div>
                      
                      <div class="flex items-center gap-1 text-muted-foreground">
                         <IconifyIcon icon="carbon:arrow-right" class="text-[10px]" />
                         <span>{{ getNextQG(comp.milestone) }}</span>
                      </div>
                   </div>
                   <div v-else class="text-center text-[10px] text-muted-foreground/50">
                      无里程碑计划
                   </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </Page>
</template>

<style scoped>
/* Scoped styles */
</style>
