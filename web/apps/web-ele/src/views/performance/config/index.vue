<script lang="ts" setup>
import type { OnActionClickParams, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceIndicator } from '#/api/core/performance';

import { ref } from 'vue';
import { Page, useVbenDrawer } from '@vben/common-ui';
import { ElButton, ElMessage, ElMessageBox, ElDialog, ElUpload, ElLink } from 'element-plus';
import { Plus, Upload } from '@vben/icons';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getIndicatorListApi, deleteIndicatorApi, importIndicatorsApi } from '#/api/core/performance';

import { useColumns, useSearchFormSchema } from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'PerformanceConfig' });

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const importDialogVisible = ref(false);

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          };
          return await getIndicatorListApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      export: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<PerformanceIndicator>,
});

function onActionClick({ code, row }: OnActionClickParams<PerformanceIndicator>) {
  if (code === 'edit') {
    openEdit(row);
  } else if (code === 'delete') {
    handleDelete(row);
  }
}

function openCreate() {
  formDrawerApi.setData(null).open();
}

function openEdit(row: PerformanceIndicator) {
  formDrawerApi.setData(row).open();
}

async function handleDelete(row: PerformanceIndicator) {
  try {
    await deleteIndicatorApi(row.id);
    ElMessage.success('删除成功');
    gridApi.query();
  } catch (error) {
    // Error handled by global interceptor usually
  }
}

async function handleImportRequest(options: any) {
  try {
    await importIndicatorsApi(options.file);
    ElMessage.success('导入成功');
    importDialogVisible.value = false;
    gridApi.query();
  } catch (error) {
    ElMessage.error('导入失败');
  }
}

function downloadTemplate() {
    const csvContent = "Code,Name,Module,Project,Chip Type,Value Type,Baseline Value,Baseline Unit,Fluctuation Range,Fluctuation Direction,Owner\nTEST_001,示例指标1,load,ProjA,ChipA,avg,100,ms,10,down,UserA";
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "performance_indicator_template.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="gridApi.query()" />

    <Grid>
      <template #toolbar-actions>
         <ElButton type="primary" @click="openCreate">
          <Plus class="mr-1 size-4" /> 新增指标
        </ElButton>
        <ElButton type="success" @click="importDialogVisible = true">
          <Upload class="mr-1 size-4" /> 导入 Excel
        </ElButton>
      </template>
    </Grid>

    <!-- Import Dialog -->
    <ElDialog v-model="importDialogVisible" title="导入指标" width="400px">
        <div class="mb-4 text-right">
            <ElLink type="primary" :underline="false" @click="downloadTemplate">下载模板 CSV</ElLink>
        </div>
        <ElUpload
          class="upload-demo"
          drag
          action="#"
          :http-request="handleImportRequest"
          :show-file-list="false"
          accept=".xlsx,.csv"
        >
          <div class="el-upload__text">
            将文件拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
             <div class="el-upload__tip">
                支持 .xlsx 或 .csv 文件
             </div>
          </template>
        </ElUpload>
    </ElDialog>
  </Page>
</template>
