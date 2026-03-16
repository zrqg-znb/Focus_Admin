<script lang="ts" setup>
import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import { getDtsList } from '#/api/project-manager/dts-statistics';
import { useDrawer } from '#/components/drawer';
import { useZqTable, ZqTable } from '#/components/zq-table';

import { columns, searchFormProps } from './data';
import DtsEditDrawer from './DtsEditDrawer.vue';

const activeTab = ref('list');

const [registerDrawer, { openDrawer }] = useDrawer();

const [tableProps, { reload }] = useZqTable({
  api: getDtsList,
  columns,
  formConfig: searchFormProps,
  showIndexColumn: true,
  rowConfig: { keyField: 'defectNo' },
});

function handleEdit(row: any, type: string) {
  openDrawer(true, {
    row,
    editType: type,
  });
}
</script>

<template>
  <Page>
    <el-tabs v-model="activeTab" class="bg-white p-4">
      <el-tab-pane label="数据明细" name="list">
        <ZqTable v-bind="tableProps">
          <template #action="{ row }">
            <el-button type="primary" link @click="handleEdit(row, 'qa')">
              QA填报
            </el-button>
            <el-button type="primary" link @click="handleEdit(row, 'dev')">
              开发填报
            </el-button>
            <el-button type="primary" link @click="handleEdit(row, 'test')">
              测试填报
            </el-button>
          </template>
        </ZqTable>
      </el-tab-pane>
      <el-tab-pane label="统计看板" name="dashboard">
        <div class="p-4">
          <!-- 总结看板组件 -->
          <el-empty description="看板正在开发中..." />
        </div>
      </el-tab-pane>
    </el-tabs>

    <DtsEditDrawer @register="registerDrawer" @success="reload" />
  </Page>
</template>
