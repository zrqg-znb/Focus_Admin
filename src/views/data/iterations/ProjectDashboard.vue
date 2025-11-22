<script setup lang='ts'>
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { DataTableColumn } from 'naive-ui'
import { getProjectDashboard } from '@/service/api/iterations'
import { productApi } from '@/service/api/product'

const { createProduct, updateProduct } = productApi

const route = useRoute()
const productId = route.params.productId

// Iteration Table
const iterationTableRef = ref()
const iterationQuery = ref({ name: '' })
const iterationColumns: DataTableColumn<Api.Iteration.IterationItem>[] = [
  { title: '迭代名称', key: 'name' },
  { title: '开始日期', key: 'start_date' },
  { title: '结束日期', key: 'end_date' },
  { title: '是否为当前迭代', key: 'is_current' },
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
]

// Metric Table
const metricTableRef = ref()
const metricQuery = ref({})
const metricColumns: DataTableColumn[] = [
  { title: '迭代名称', key: 'iteration_name' },
  { title: '故事点', key: 'story_points' },
  { title: '已完成故事点', key: 'completed_story_points' },
]

// Product Modal
const showProductModal = ref(false)
const productFormRef = ref()
const productForm = reactive({
  id: null,
  name: '',
  pm: '',
})
const productRules = {
  name: { required: true, message: '请输入项目名称', trigger: 'blur' },
  pm: { required: true, message: '请输入项目经理', trigger: 'blur' },
}

async function handleProductSave() {
  await productFormRef.value.validate()
  if (productForm.id) {
    await updateProduct(productForm.id, productForm)
  }
  else {
    await createProduct(productForm)
  }
  showProductModal.value = false
}
</script>

<template>
  <div class="p-2 h-full">
    <n-card title="项目管理">
      <n-button type="primary" @click="showProductModal = true">
        新增项目
      </n-button>
    </n-card>

    <n-card title="迭代列表" class="mt-4">
      <CrudTable
        ref="iterationTableRef"
        :get-data="getIterationList"
        :query-items="iterationQuery"
        :columns="iterationColumns"
        :extra-params="{ product_id: productId }"
      >
        <template #queryBar>
          <QueryBarItem label="迭代名称" :label-width="80">
            <n-input
              v-model:value="iterationQuery.name"
              class="w-48"
              placeholder="请输入迭代名称"
              @keydown.enter="iterationTableRef.handleSearch()"
            />
          </QueryBarItem>
        </template>
      </CrudTable>
    </n-card>

    <n-card title="迭代指标历史" class="mt-4">
      <CrudTable
        ref="metricTableRef"
        :get-data="getProjectDashboard"
        :query-items="metricQuery"
        :columns="metricColumns"
        :extra-params="{ product_id: productId }"
      />
    </n-card>

    <CrudModal
      v-model:visible="showProductModal"
      title="新增项目"
      @save="handleProductSave"
    >
      <n-form
        ref="productFormRef"
        :model="productForm"
        :rules="productRules"
      >
        <n-form-item label="项目名称" path="name">
          <n-input v-model:value="productForm.name" placeholder="请输入项目名称" />
        </n-form-item>
        <n-form-item label="项目经理" path="pm">
          <n-input v-model:value="productForm.pm" placeholder="请输入项目经理" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </div>
</template>
