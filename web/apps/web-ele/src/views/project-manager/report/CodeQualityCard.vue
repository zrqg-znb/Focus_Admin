<script lang="ts" setup>
import type { CodeQualityModuleDetail, CodeQualitySummary } from '#/api/project-manager/report';
import { IconifyIcon } from '@vben/icons';
import { ElButton, ElTag } from 'element-plus';
import { computed, ref } from 'vue';

const props = defineProps<{
  data: CodeQualitySummary;
  details?: CodeQualityModuleDetail[] | null;
}>();

const detailVisible = ref(false);

const latestModules = computed(() => {
  const items = props.details || [];
  return items.slice(0, 6);
});

function scoreColor(score: number) {
  if (score >= 80) return 'text-green-600 dark:text-green-500';
  if (score >= 60) return 'text-orange-600 dark:text-orange-500';
  return 'text-red-600 dark:text-red-500';
}
</script>

<template>
  <div>
    <div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515] hover:shadow-md transition-shadow">
      <div class="mb-6 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
            <IconifyIcon icon="lucide:code-2" class="text-blue-500 text-xl" />
          </div>
          <div>
            <h3 class="text-base font-bold text-gray-800 dark:text-white">代码质量</h3>
            <p class="text-xs text-gray-400">代码静态分析结果</p>
          </div>
        </div>
        <div class="flex items-baseline gap-1">
          <span class="text-3xl font-bold text-green-600 dark:text-green-500">{{ data.health_score }}</span>
          <span class="text-xs text-gray-400">分</span>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-2 mb-6">
        <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">LOC</span>
          <span class="text-sm font-bold font-mono text-gray-700 dark:text-gray-200">{{ (data.total_loc / 1000).toFixed(1) }}k</span>
        </div>
        <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Modules</span>
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ data.total_modules }}</span>
        </div>
        <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Issues</span>
          <span class="text-sm font-bold" :class="data.total_issues > 0 ? 'text-red-500' : 'text-gray-700 dark:text-gray-200'">{{ data.total_issues }}</span>
        </div>
        <div class="flex flex-col items-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span class="text-[10px] text-gray-400 uppercase mb-1">Dup</span>
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ data.avg_duplication_rate }}%</span>
        </div>
      </div>

      <div class="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-xl flex items-start gap-3 border border-blue-100 dark:border-blue-900/20">
        <IconifyIcon icon="lucide:info" class="text-blue-500 mt-0.5 flex-shrink-0" />
        <div class="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
          <p v-if="data.health_score >= 80">代码质量整体表现优秀，请继续保持较低的重复率和问题数。</p>
          <p v-else-if="data.health_score >= 60">代码质量尚可，建议关注高重复率模块和潜在的安全风险。</p>
          <p v-else>代码质量堪忧，存在较多阻断性问题，建议立即安排重构或修复计划。</p>
        </div>
      </div>

      <div class="mt-4 flex justify-end">
        <ElButton
          size="small"
          plain
          type="primary"
          @click="detailVisible = !detailVisible"
          :disabled="!(props.details && props.details.length)"
        >
          {{ detailVisible ? '收起详情' : '展开详情' }}
        </ElButton>
      </div>

      <transition name="el-collapse-transition">
        <div v-show="detailVisible" class="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-900/20">
          <div class="mb-3 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="h-2 w-2 rounded-full bg-blue-500" />
              <div class="text-sm font-bold text-gray-800 dark:text-gray-100">模块概览（最新）</div>
            </div>
            <div class="text-xs text-gray-400">展示前 {{ latestModules.length }} 个模块</div>
          </div>

          <div class="grid grid-cols-1 gap-3">
            <div
              v-for="m in latestModules"
              :key="m.id"
              class="rounded-xl border border-gray-100 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-sm font-bold text-gray-900 dark:text-white">
                    {{ m.oem_name }} / {{ m.module }}
                  </div>
                  <div class="mt-0.5 truncate text-[11px] text-gray-400">
                    责任人：{{ (m.owner_names || []).join('、') || '-' }} · {{ m.record_date || '-' }}
                  </div>
                </div>
                <ElTag :type="m.is_clean_code ? 'success' : 'danger'" size="small">
                  {{ m.is_clean_code ? 'Clean' : 'Risk' }}
                </ElTag>
              </div>

              <div class="mt-3 grid grid-cols-4 gap-2">
                <div class="rounded-lg bg-gray-50 px-2 py-2 text-center dark:bg-gray-800/50">
                  <div class="text-[10px] text-gray-400">LOC</div>
                  <div class="text-sm font-bold text-gray-800 dark:text-gray-100">{{ Math.round(m.loc / 100) / 10 }}k</div>
                </div>
                <div class="rounded-lg bg-gray-50 px-2 py-2 text-center dark:bg-gray-800/50">
                  <div class="text-[10px] text-gray-400">函数</div>
                  <div class="text-sm font-bold text-gray-800 dark:text-gray-100">{{ m.function_count }}</div>
                </div>
                <div class="rounded-lg bg-gray-50 px-2 py-2 text-center dark:bg-gray-800/50">
                  <div class="text-[10px] text-gray-400">危险</div>
                  <div class="text-sm font-bold" :class="m.dangerous_func_count > 0 ? 'text-red-600 dark:text-red-500' : 'text-gray-800 dark:text-gray-100'">
                    {{ m.dangerous_func_count }}
                  </div>
                </div>
                <div class="rounded-lg bg-gray-50 px-2 py-2 text-center dark:bg-gray-800/50">
                  <div class="text-[10px] text-gray-400">重复率</div>
                  <div class="text-sm font-bold" :class="m.duplication_rate > 5 ? 'text-orange-600 dark:text-orange-500' : 'text-gray-800 dark:text-gray-100'">
                    {{ m.duplication_rate }}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-3 flex items-center justify-between rounded-xl bg-white px-3 py-2 text-xs text-gray-500 dark:bg-[#151515] dark:text-gray-400">
            <span>提示：这里是精简版模块明细，后续你可继续补充字段。</span>
            <span class="font-medium" :class="scoreColor(data.health_score)">整体得分 {{ data.health_score }}</span>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>
