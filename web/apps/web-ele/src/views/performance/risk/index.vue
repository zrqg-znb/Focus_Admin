<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceRiskRecord } from '#/api/core/performance';

import dayjs from 'dayjs';
import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElButton, ElDatePicker, ElDialog, ElMessage, ElOption, ElRadioButton, ElRadioGroup, ElSelect, ElTag } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { confirmRiskApi, getIndicatorTreeApi, getRiskDetailApi, getRiskListApi, resolveRiskApi } from '#/api/core/performance';

import type { PerformanceTreeNode } from '#/api/core/performance';

defineOptions({ name: 'PerformanceRiskList' });

const treeData = ref<PerformanceTreeNode[]>([]);
const category = ref<'vehicle' | 'cockpit'>('vehicle');
const project = ref<string>('');
const module = ref<string>('');
const status = ref<string>('open');

const dateRange = ref<[string, string]>([
  dayjs().subtract(6, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
]);

const projectOptions = computed(() => {
  const catNode = treeData.value.find((i) => i.key === category.value);
  return (catNode?.children || []).map((i) => ({ label: i.label, value: i.label }));
});

const moduleOptions = computed(() => {
  const catNode = treeData.value.find((i) => i.key === category.value);
  const projNode = catNode?.children?.find((i) => i.label === project.value);
  return (projNode?.children || []).map((i) => ({ label: i.label, value: i.label }));
});

const startDate = computed(() => dateRange.value[0]);
const endDate = computed(() => dateRange.value[1]);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: [
      { field: 'occur_date', title: '日期', minWidth: 120, sortable: true },
      { field: 'project', title: '项目', minWidth: 120 },
      { field: 'module', title: '模块', minWidth: 120 },
      { field: 'chip_type', title: '芯片', minWidth: 100 },
      { field: 'indicator_name', title: '指标', minWidth: 160 },
      {
        field: 'status',
        title: '状态',
        minWidth: 100,
        slots: { default: 'status' },
      },
      {
        field: 'deviation_value',
        title: '偏差',
        minWidth: 120,
      },
      {
        field: 'baseline_value',
        title: '基线/当前',
        minWidth: 160,
        formatter: ({ row }) =>
          `${row.baseline_value} → ${row.measured_value}`,
      },
      {
        field: 'owner_name',
        title: '责任人',
        minWidth: 120,
      },
      {
        field: 'action',
        title: '操作',
        fixed: 'right',
        width: 200,
        slots: { default: 'action' },
      },
    ],
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            category: category.value,
            project: project.value,
            module: module.value,
            status: status.value || undefined,
            start_date: startDate.value,
            end_date: endDate.value,
          };
          return await getRiskListApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: false,
      zoom: true,
    },
  } as VxeTableGridOptions<PerformanceRiskRecord>,
});

async function loadTree() {
  treeData.value = await getIndicatorTreeApi();
  if (!project.value) {
    const first = projectOptions.value[0]?.value;
    if (first) project.value = first;
  }
}

watch(
  () => category.value,
  () => {
    project.value = projectOptions.value[0]?.value || '';
    module.value = '';
    gridApi.query();
  },
);

watch(
  () => project.value,
  () => {
    module.value = '';
    gridApi.query();
  },
);

watch(
  () => [module.value, status.value, startDate.value, endDate.value] as const,
  () => {
    gridApi.query();
  },
);

onMounted(async () => {
  await loadTree();
  gridApi.query();
});

const confirmVisible = ref(false);
const confirmResolved = ref<boolean>(false);
const confirmReason = ref<string>('');
let confirmTarget: PerformanceRiskRecord | null = null;
function openConfirm(row: PerformanceRiskRecord) {
  confirmTarget = row;
  confirmResolved.value = false;
  confirmReason.value = '';
  confirmVisible.value = true;
}

async function submitConfirm() {
  if (!confirmTarget) return;
  if (!confirmReason.value.trim()) {
    ElMessage.error('请填写引发风险的原因');
    return;
    }
  await confirmRiskApi(confirmTarget.id, {
    resolved: confirmResolved.value,
    reason: confirmReason.value,
  });
  ElMessage.success('确认成功');
  confirmVisible.value = false;
  gridApi.query();
}

async function doResolve(row: PerformanceRiskRecord) {
  await resolveRiskApi(row.id);
  ElMessage.success('已解决');
  gridApi.query();
}

const detailVisible = ref(false);
const detailRow = ref<PerformanceRiskRecord | null>(null);
async function viewDetail(row: PerformanceRiskRecord) {
  const data = await getRiskDetailApi(row.id);
  detailRow.value = data;
  detailVisible.value = true;
}
</script>

<template>
  <Page auto-content-height>
    <div class="mb-4 flex flex-col gap-4 border-b pb-4 px-4">
      <div class="flex items-center">
        <ElRadioGroup v-model="category" size="large">
          <ElRadioButton label="vehicle">车控应用</ElRadioButton>
          <ElRadioButton label="cockpit">座舱应用</ElRadioButton>
        </ElRadioGroup>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">项目</div>
          <ElSelect
            v-model="project"
            class="w-[180px]"
            filterable
            placeholder="选择项目"
          >
            <ElOption
              v-for="p in projectOptions"
              :key="p.value"
              :label="p.label"
              :value="p.value"
            />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">模块</div>
          <ElSelect
            v-model="module"
            class="w-[180px]"
            filterable
            clearable
            placeholder="全部模块"
          >
            <ElOption
              v-for="m in moduleOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">风险状态</div>
          <ElSelect
            v-model="status"
            class="w-[140px]"
            clearable
            placeholder="全部状态"
          >
            <ElOption label="未处理" value="open" />
            <ElOption label="已确认" value="ack" />
            <ElOption label="已解决" value="resolved" />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">发生日期</div>
          <ElDatePicker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="!w-[260px]"
          />
        </div>
      </div>
    </div>

    <Grid>
      <template #status="{ row }">
        <ElTag
          :type="row.status === 'open' ? 'danger' : row.status === 'ack' ? 'warning' : 'success'"
        >
          {{ row.status === 'open' ? '未处理' : row.status === 'ack' ? '已确认' : '已解决' }}
        </ElTag>
      </template>
      <template #default>
        <div />
      </template>
      <template #action="{ row }">
        <ElButton 
          v-if="row.status === 'open'"
          type="danger" size="small" @click="openConfirm(row)"
        >确认风险</ElButton>
        <ElButton 
          v-else-if="row.status === 'ack'"
          type="warning" size="small" @click="doResolve(row)"
        >标记解决</ElButton>
        <ElTag v-else type="success">已解决</ElTag>
        <ElButton 
          class="ml-2" type="primary" size="small" 
          @click="viewDetail(row)"
        >处理记录</ElButton>
      </template>
    </Grid>

    <ElDialog v-model="detailVisible" title="风险处理记录" width="600px" destroy-on-close>
      <div v-if="detailRow" class="space-y-2">
        <div>指标：{{ detailRow.indicator_name }}（{{ detailRow.project }} / {{ detailRow.module }} / {{ detailRow.chip_type }}）</div>
        <div>日期：{{ detailRow.occur_date }}</div>
        <div>状态：{{ detailRow.status }}</div>
        <div>责任人：{{ detailRow.owner_name || '—' }}</div>
        <div>基线值：{{ detailRow.baseline_value }}，当前值：{{ detailRow.measured_value }}</div>
        <div>偏差：{{ detailRow.deviation_value }}，允许范围：{{ detailRow.allowed_range }}（方向：{{ detailRow.direction }}）</div>
        <div>说明：{{ detailRow.message || '暂无' }}</div>
      </div>
    </ElDialog>

    <ElDialog v-model="confirmVisible" title="确认风险" width="500px" destroy-on-close>
      <div class="space-y-4">
        <div class="flex items-center gap-3">
          <span class="text-sm text-[var(--el-text-color-regular)]">处理结论</span>
          <ElRadioGroup v-model="confirmResolved">
            <ElRadioButton :label="false">未解决</ElRadioButton>
            <ElRadioButton :label="true">已解决</ElRadioButton>
          </ElRadioGroup>
        </div>
        <div>
          <span class="mb-2 block text-sm text-[var(--el-text-color-regular)]">引发风险的原因</span>
          <textarea
            v-model="confirmReason"
            class="w-full rounded border p-2"
            rows="4"
            placeholder="请填写原因说明"
          ></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <ElButton @click="confirmVisible = false">取消</ElButton>
          <ElButton type="primary" @click="submitConfirm">提交</ElButton>
        </div>
      </div>
    </ElDialog>
  </Page>
</template>
