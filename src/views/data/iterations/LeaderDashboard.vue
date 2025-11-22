<script setup lang="ts">
import { h, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { DataTableColumn } from 'naive-ui'
import { NButton } from 'naive-ui'
import { getLeaderDashboard } from '@/service/api/iterations'

const router = useRouter()
const tableRef = ref<any>(null)
const query = ref({
  product_name: '',
  pm: '',
})

const columns: DataTableColumn<Api.Iteration.LeaderDashboardItem>[] = [
  { title: '项目名称', key: 'product_name' },
  { title: '项目经理', key: 'pm' },
  { title: '当前迭代名称', key: 'name' },
  {
    title: '完成率 (%)',
    key: 'latest_metric.completion_rate',
    render(row) {
      return row.latest_metric?.completion_rate ?? 'N/A'
    },
  },
  {
    title: 'A级需求占比 (%)',
    key: 'latest_metric.grade_a_rate',
    render(row) {
      return row.latest_metric?.grade_a_rate ?? 'N/A'
    },
  },
  {
    title: 'AC级需求占比 (%)',
    key: 'latest_metric.grade_ac_rate',
    render(row) {
      return row.latest_metric?.grade_ac_rate ?? 'N/A'
    },
  },
  {
    title: '需求分解率 (%)',
    key: 'latest_metric.decompose_rate',
    render(row) {
      return row.latest_metric?.decompose_rate ?? 'N/A'
    },
  },
  {
    title: '孤儿需求占比 (%)',
    key: 'latest_metric.orphan_rate',
    render(row) {
      return row.latest_metric?.orphan_rate ?? 'N/A'
    },
  },
  { title: '指标更新日期', key: 'latest_metric.refresh_date' },
  {
    title: '操作',
    key: 'actions',
    render(row) {
      return h(
        NButton,
        {
          strong: true,
          tertiary: true,
          size: 'small',
          onClick: () => {
            router.push({ name: 'project_dashboard', params: { productId: row.product_id } })
          },
        },
        { default: () => '详情' },
      )
    },
  },
]
</script>

<template>
  <div class="p-2 h-full">
    <CrudTable
      ref="tableRef"
      :get-data="getLeaderDashboard"
      :query-items="query"
      :columns="columns"
    >
      <template #queryBar>
        <QueryBarItem label="项目名称" :label-width="80">
          <n-input
            v-model:value="query.product_name"
            class="w-48"
            placeholder="请输入项目名称"
            @keydown.enter="tableRef.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="项目经理" :label-width="80">
          <n-input
            v-model:value="query.pm"
            class="w-48"
            placeholder="请输入项目经理"
            @keydown.enter="tableRef.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </div>
</template>
