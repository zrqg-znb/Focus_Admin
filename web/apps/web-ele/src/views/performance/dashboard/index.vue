<script lang="ts" setup>
import { ref, onMounted, reactive } from 'vue';
import { Page } from '@vben/common-ui';
import { ElButton, ElTable, ElTableColumn, ElPagination, ElTag, ElSelect, ElOption, ElDialog, ElInput, ElDatePicker } from 'element-plus';
import { getDashboardDataApi, type PerformanceDashboardItem } from '#/api/core/performance';
import TrendChart from './components/TrendChart.vue';

defineOptions({ name: 'PerformanceDashboard' });

const loading = ref(false);
const tableData = ref<PerformanceDashboardItem[]>([]);
const total = ref(0);
const queryParams = reactive({
  page: 1,
  pageSize: 10,
  project: '',
  module: '',
  chip_type: '',
  date: ''
});

const trendVisible = ref(false);
const currentIndicatorId = ref('');
const currentIndicatorName = ref('');

async function loadData() {
  loading.value = true;
  try {
    const res = await getDashboardDataApi(queryParams);
    tableData.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

function getStatus(row: PerformanceDashboardItem) {
    if (row.current_value === undefined || row.current_value === null) return 'info';
    
    const fVal = row.fluctuation_value || 0;
    const range = row.fluctuation_range || 0;
    
    if (row.fluctuation_direction === 'up') {
        if (fVal < -range) return 'danger';
        return 'success';
    } else if (row.fluctuation_direction === 'down') {
        if (fVal > range) return 'danger';
        return 'success';
    } else {
        if (Math.abs(fVal) > range) return 'warning';
        return 'success';
    }
}

function showTrend(row: PerformanceDashboardItem) {
    currentIndicatorId.value = row.id;
    currentIndicatorName.value = row.name;
    trendVisible.value = true;
}

onMounted(() => {
    loadData();
});
</script>

<template>
  <Page auto-content-height>
    <div class="p-4">
        <!-- Filters -->
       <div class="mb-4 flex gap-4 flex-wrap">
           <ElInput v-model="queryParams.project" placeholder="Project" style="width: 150px" @keyup.enter="loadData" />
           <ElInput v-model="queryParams.module" placeholder="Module" style="width: 150px" @keyup.enter="loadData" />
           <ElInput v-model="queryParams.chip_type" placeholder="Chip Type" style="width: 150px" @keyup.enter="loadData" />
           <ElDatePicker v-model="queryParams.date" type="date" placeholder="Date" value-format="YYYY-MM-DD" style="width: 150px" />
           <ElButton type="primary" @click="loadData">查询</ElButton>
       </div>
       
       <ElTable v-loading="loading" :data="tableData" border style="width: 100%">
        <ElTableColumn prop="name" label="指标名称" min-width="150" />
        <ElTableColumn prop="baseline_value" label="基线值" width="120">
             <template #default="{ row }">
            {{ row.baseline_value }} {{ row.baseline_unit }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="current_value" label="当前值" width="120">
             <template #default="{ row }">
            {{ row.current_value !== null ? row.current_value?.toFixed(2) : '-' }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="fluctuation_value" label="浮动" width="120">
             <template #default="{ row }">
                 <ElTag :type="getStatus(row)" v-if="row.fluctuation_value !== null">
                     {{ row.fluctuation_value?.toFixed(2) }}
                 </ElTag>
          </template>
        </ElTableColumn>
         <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="showTrend(row)">趋势</ElButton>
          </template>
        </ElTableColumn>
       </ElTable>
       
       <div class="mt-4 flex justify-end">
        <ElPagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
      
      <ElDialog v-model="trendVisible" :title="`趋势图 - ${currentIndicatorName}`" width="800px" destroy-on-close>
          <TrendChart :indicator-id="currentIndicatorId" v-if="trendVisible" />
      </ElDialog>
    </div>
  </Page>
</template>
