<script lang="ts" setup>
import { reactive, ref, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid, type VxeGridProps } from '#/adapter/vxe-table';
import { ElTag } from 'element-plus';
import { 
  getProjectList, 
  getProjectDailyData, 
  type ProjectConfig,
  type ProjectDailyData
} from '#/api/ci_daily_report';

defineOptions({ name: 'CIDailyReport' });

// ------------------- 数据报表 -------------------
const projectList = ref<ProjectConfig[]>([]);

async function loadProjects() {
  const res = await getProjectList({ size: 100 });
  projectList.value = res.items || [];
}

const formOptions = reactive({
  collapsed: false,
  items: [
    {
      component: 'VbenSelect',
      fieldName: 'project_id',
      label: '选择项目',
      componentProps: {
        placeholder: '全部项目',
        options: projectList,
        fieldNames: { label: 'name', value: 'id' },
        showSearch: true,
        optionFilterProp: 'label',
        allowClear: true, 
      },
    },
    {
      component: 'VbenRangePicker',
      fieldName: 'dateRange',
      label: '日期范围',
    },
  ],
});

const gridOptions = reactive<VxeGridProps<ProjectDailyData>>({
  columns: [
    { field: 'date', title: '日期', width: 120, sortable: true },
    { field: 'project_name', title: '项目名称', minWidth: 150 },
    { field: 'test_cases_count', title: '总用例数', width: 100 },
    { field: 'test_cases_passed', title: '通过数', width: 100 },
    { field: 'pass_rate', title: '通过率', width: 100, slots: { default: 'pass_rate' } },
    { field: 'compile_standard_options', title: '编译规范', minWidth: 200, formatter: ({ cellValue }) => JSON.stringify(cellValue) },
    { field: 'build_standard_options', title: '构建规范', minWidth: 200, formatter: ({ cellValue }) => JSON.stringify(cellValue) },
    { field: 'extra_data', title: '其他数据', minWidth: 200, formatter: ({ cellValue }) => JSON.stringify(cellValue) },
  ],
  proxyConfig: {
    ajax: {
      query: async ({ page, form }) => {
        const params: any = {
          page: page.currentPage,
          size: page.pageSize,
          project_id: form.project_id,
        };
        if (form.dateRange && form.dateRange.length === 2) {
          params.start_date = form.dateRange[0];
          params.end_date = form.dateRange[1];
        }
        
        const res = await getProjectDailyData(params);
        
        // Enrich data with project name (since API might return ID)
        // Ideally backend returns project name or we map it here
        const items = res.items || [];
        const enrichedItems = items.map(item => {
          const project = projectList.value.find(p => p.id === item.project_id);
          return {
            ...item,
            project_name: project ? project.name : `Project ${item.project_id}`,
          };
        });

        return { items: enrichedItems, total: res.total };
      },
    },
  },
});

const [Grid, gridApi] = useVbenVxeGrid({ formOptions, gridOptions });

// Initial Load
onMounted(() => {
  loadProjects();
});
</script>

<template>
  <Page title="每日集成报告">
    <div class="h-full bg-white p-4 shadow rounded-lg">
      <Grid>
        <template #pass_rate="{ row }">
          <ElTag :type="row.test_cases_passed === row.test_cases_count ? 'success' : 'warning'">
            {{ row.test_cases_count > 0 ? ((row.test_cases_passed / row.test_cases_count) * 100).toFixed(1) + '%' : '0%' }}
          </ElTag>
        </template>
      </Grid>
    </div>
  </Page>
</template>
