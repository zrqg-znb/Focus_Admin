<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import {
  type CascaderOption,
  type DataTableColumns,
  NCard,
  NCascader,
  NDataTable,
  NIcon,
  NPagination,
  NSpace,
  NStatistic,
  NTag,
} from 'naive-ui'
import {
  AlertCircleOutline,
  CloseCircleOutline,
  InformationCircleOutline,
  ListOutline,
  WarningOutline,
} from '@vicons/ionicons5'
// 根据你的实际 API 路径调整导入
import { getCategoryList, getDetailList, getSummaryData } from '@/service/api'

// 级联选择器选中的值
const selectedProject = ref<string | null>(null)

// 级联选择器选项
const cascaderOptions = ref<CascaderOption[]>([])

// 汇总数据
const summaryData = reactive({
  total: 0,
  critical: 0,
  major: 0,
  warning: 0,
  info: 0,
})

// 表格数据
const tableData = ref<any[]>([])

// 加载状态
const loading = ref(false)

// 分页信息
const pagination = reactive({
  page: 1,
  pageSize: 10,
  pageCount: 0,
  itemCount: 0,
})

// 表格列定义
const columns: DataTableColumns<any> = [
  {
    title: '序号',
    key: 'index',
    width: 80,
    render: (_, index) => {
      return (pagination.page - 1) * pagination.pageSize + index + 1
    },
  },
  {
    title: '名称',
    key: 'name',
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: '级别',
    key: 'level',
    width: 100,
    render: (row) => {
      const levelMap: Record<string, { type: any, label: string }> = {
        critical: { type: 'error', label: '严重' },
        major: { type: 'warning', label: '关键' },
        warning: { type: 'warning', label: '警告' },
        info: { type: 'info', label: '提示' },
      }
      const config = levelMap[row.level] || { type: 'default', label: row.level }
      return h(NTag, { type: config.type }, { default: () => config.label })
    },
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: '创建时间',
    key: 'createTime',
    width: 180,
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const statusMap: Record<string, { type: any, label: string }> = {
        active: { type: 'success', label: '正常' },
        inactive: { type: 'default', label: '已关闭' },
        pending: { type: 'warning', label: '待处理' },
      }
      const config = statusMap[row.status] || { type: 'default', label: row.status }
      return h(NTag, { type: config.type }, { default: () => config.label })
    },
  },
]

// 初始化级联选择器数据
async function initCascaderOptions() {
  try {
    // 根据你的实际 API 调整
    const response = await getCategoryList()
    cascaderOptions.value = response.data || []

    // 默认选择第一个项目
    if (cascaderOptions.value.length > 0) {
      const firstCategory = cascaderOptions.value[0]
      if (firstCategory.children && firstCategory.children.length > 0) {
        selectedProject.value = firstCategory.children[0].value as string
        await loadData()
      }
    }
  }
  catch (error) {
    console.error('加载分类列表失败:', error)
  }
}

// 加载汇总数据（请求A）
async function loadSummaryData() {
  if (!selectedProject.value)
    return

  try {
    const response = await getSummaryData({ projectId: selectedProject.value })
    const data = response.data || {}
    summaryData.total = data.total || 0
    summaryData.critical = data.critical || 0
    summaryData.major = data.major || 0
    summaryData.warning = data.warning || 0
    summaryData.info = data.info || 0
  }
  catch (error) {
    console.error('加载汇总数据失败:', error)
  }
}

// 加载列表数据（请求B）
async function loadListData() {
  if (!selectedProject.value)
    return

  loading.value = true
  try {
    const response = await getDetailList({
      projectId: selectedProject.value,
      page: pagination.page,
      pageSize: pagination.pageSize,
    })

    const data = response.data || {}
    tableData.value = data.list || []
    pagination.pageCount = data.pageCount || 0
    pagination.itemCount = data.total || 0
  }
  catch (error) {
    console.error('加载列表数据失败:', error)
    tableData.value = []
  }
  finally {
    loading.value = false
  }
}

// 加载所有数据
async function loadData() {
  await Promise.all([loadSummaryData(), loadListData()])
}

// 项目切换处理
async function handleProjectChange(value: string | null) {
  if (!value) {
    // 清空数据
    Object.assign(summaryData, {
      total: 0,
      critical: 0,
      major: 0,
      warning: 0,
      info: 0,
    })
    tableData.value = []
    return
  }

  // 重置分页
  pagination.page = 1
  await loadData()
}

// 页码变化处理
async function handlePageChange(page: number) {
  pagination.page = page
  await loadListData()
}

// 每页条数变化处理
async function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  await loadListData()
}

// 组件挂载时初始化
onMounted(() => {
  initCascaderOptions()
})
</script>

<template>
  <div class="page-container">
    <!-- 上半部分：级联选择器 -->
    <div class="filter-section">
      <NCascader
        v-model:value="selectedProject"
        :options="cascaderOptions"
        placeholder="请选择分类和项目"
        :show-path="true"
        filterable
        clearable
        style="width: 400px"
        @update:value="handleProjectChange"
      />
    </div>

    <!-- 下半部分：数据展示卡片 -->
    <NCard class="data-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <NSpace :size="24">
            <NStatistic label="总数" :value="summaryData.total">
              <template #prefix>
                <NIcon :component="ListOutline" />
              </template>
            </NStatistic>
            <NStatistic label="严重" :value="summaryData.critical">
              <template #prefix>
                <NIcon :component="CloseCircleOutline" color="#d03050" />
              </template>
            </NStatistic>
            <NStatistic label="关键" :value="summaryData.major">
              <template #prefix>
                <NIcon :component="WarningOutline" color="#f0a020" />
              </template>
            </NStatistic>
            <NStatistic label="警告" :value="summaryData.warning">
              <template #prefix>
                <NIcon :component="AlertCircleOutline" color="#faad14" />
              </template>
            </NStatistic>
            <NStatistic label="提示" :value="summaryData.info">
              <template #prefix>
                <NIcon :component="InformationCircleOutline" color="#2080f0" />
              </template>
            </NStatistic>
          </NSpace>
        </div>
      </template>

      <!-- 数据表格 -->
      <NDataTable
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="false"
        :bordered="false"
        :single-line="false"
      />

      <!-- 分页控件 -->
      <div class="pagination-container">
        <NPagination
          v-model:page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-count="pagination.pageCount"
          :item-count="pagination.itemCount"
          :page-sizes="[10, 20, 30, 50]"
          show-size-picker
          show-quick-jumper
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        >
          <template #prefix="{ itemCount }">
            共 {{ itemCount }} 条
          </template>
        </NPagination>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.page-container {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.data-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.data-card :deep(.n-card__content) {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 0;
}

.card-header {
  padding: 4px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding: 20px;
  border-top: 1px solid #f0f0f0;
  margin-top: auto;
}

:deep(.n-data-table) {
  flex: 1;
}
</style>
