<!-- src/components/DataTable.vue -->
<script setup>
import { onMounted, ref, watch } from 'vue'
import { NDataTable, NPagination, NSpin, useMessage } from 'naive-ui' // 引入 useMessage
import { getMockList } from '@/service'

// 定义 props
const props = defineProps({
  selectedProject: {
    type: String,
    default: '',
  },
})

// 引入 Naive UI 的 Message
const message = useMessage()

// 表格数据
const data = ref([])
const loading = ref(false)

// 分页信息
const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)

// 表格列配置
const columns = [
  {
    title: '序号',
    key: 'no',
    width: 80,
    align: 'center',
  },
  {
    title: '姓名',
    key: 'name',
    width: 120,
  },
  {
    title: '性别',
    key: 'sex',
    width: 100,
  },
  {
    title: '年龄',
    key: 'age',
    width: 100,
  },
  {
    title: '身高 (cm)',
    key: 'height',
    width: 120,
  },
]

// 获取数据函数
async function fetchData() {
  if (!props.selectedProject) {
    // 如果没有选择项目，则不加载数据
    data.value = []
    totalItems.value = 0
    return
  }

  loading.value = true
  try {
    const params = {
      pageSize: pageSize.value,
      pageNo: currentPage.value,
      version: 'v1', // 假设版本固定为 v1
      project: props.selectedProject, // 将选中的项目作为参数传递
    }
    const response = await getMockList(params)
    if (response && response.success) { // 检查业务是否成功
      data.value = response.items || [] // 从 response.items 获取数据
      totalItems.value = response.pagination?.total || 0
      currentPage.value = response.pagination?.currentPage || 1
      pageSize.value = response.pagination?.pageSize || 10
    }
    else {
      data.value = []
      totalItems.value = 0
      currentPage.value = 1
    }
  }
  catch (error) {
    console.error('获取表格数据失败:', error)
  }
  finally {
    loading.value = false
  }
}

// 监听 selectedProject 变化，当项目改变时，重置页码并重新加载数据
watch(
  () => props.selectedProject,
  (newVal, oldVal) => {
    if (newVal !== oldVal) {
      currentPage.value = 1 // 切换项目时重置页码
      fetchData()
    }
  },
)

// 处理页码改变
function handlePageChange(page) {
  currentPage.value = page
  fetchData()
}

// 处理每页显示数量改变
function handlePageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1 // 改变每页数量后通常回到第一页
  fetchData()
}

// 组件挂载时如果已有项目，则加载数据
onMounted(() => {
  if (props.selectedProject) {
    fetchData()
  }
})
</script>

<template>
  <div class="data-table-container">
    <NSpin :show="loading">
      <NDataTable
        :columns="columns"
        :data="data"
        :bordered="false"
        :single-line="false"
        :pagination="false"
        size="small"
      />
      <div class="pagination-wrapper">
        <NPagination
          v-if="totalItems > 0"
          v-model:page="currentPage"
          v-model:page-size="pageSize"
          :item-count="totalItems"
          show-size-picker
          :page-sizes="[10, 20, 30, 50]"
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </NSpin>
    <div v-if="!props.selectedProject && !loading" class="no-project-tip">
      请在上方选择一个项目来查看数据。
    </div>
    <div v-if="props.selectedProject && !loading && data.length === 0" class="no-data-tip">
      当前项目暂无数据。
    </div>
  </div>
</template>

<style scoped>
.data-table-container {
  margin-top: 20px;
  min-height: 300px; /* 确保有足够的空间显示加载状态或提示 */
  position: relative;
}

.pagination-wrapper {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

.no-project-tip, .no-data-tip {
  text-align: center;
  padding: 20px;
  color: #999;
}
</style>
