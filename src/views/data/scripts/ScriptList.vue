<script setup>
import { h, reactive, ref, watch } from 'vue'
import { NButton, NDynamicInput, NFormItemGi, NGrid, NInputNumber, NPopconfirm, NTag } from 'naive-ui'
import CrudTable from '@/components/table/CrudTable.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import { scriptApi } from '@/service'
import { formatDateTime } from '@/utils'
import NovaIcon from '@/components/common/NovaIcon.vue'

const router = useRouter()
// 查询参数
const queryItems = ref({
  name: null,
  script_type: null,
  status: null,
})

// 选项数据
const scriptTypeOptions = [
  { label: 'Bash脚本', value: 'bash' },
  { label: 'Python脚本', value: 'python' },
]

const returnTypeOptions = [
  { label: '纯文本', value: 'text' },
  { label: 'JSON格式', value: 'json' },
  { label: 'HTML格式', value: 'html' },
  { label: 'XML格式', value: 'xml' },
]

const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'inactive' },
  { label: '草稿', value: 'draft' },
]

// 表格引用
const tableRef = ref()
const checkedRowKeys = ref([])

// 表格列配置
const columns = [
  { type: 'selection' },
  { title: '脚本名称', key: 'name', width: 150 },
  {
    title: '脚本类型',
    key: 'script_type',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.script_type === 'bash' ? 'info' : 'primary' },
        { default: () => row.script_type_display },
      )
    },
  },
  {
    title: '返回类型',
    key: 'return_type',
    width: 100,
    render(row) {
      return row.return_type_display
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render(row) {
      const typeMap = {
        active: 'success',
        inactive: 'error',
        draft: 'warning',
      }
      return h(
        NTag,
        { type: typeMap[row.status] },
        { default: () => row.status_display },
      )
    },
  },
  { title: '执行次数', key: 'execution_count', width: 100 },
  {
    title: '上次执行时间',
    key: 'last_executed_at',
    width: 180,
    render(row) {
      return row.last_executed_at ? formatDateTime(row.last_executed_at) : '未执行'
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return formatDateTime(row.created_at)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    fixed: 'right',
    render(row) {
      return [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            secondary: true,
            onClick: () => handleExecuteScript(row),
            disabled: row.status !== 'active',
          },
          { default: () => '执行', icon: () => h(NovaIcon, { icon: 'icon-park-outline:play-two' }) },
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            secondary: true,
            style: 'margin-left: 8px',
            onClick: () => handleViewExecutions(row),
          },
          { default: () => '记录', icon: () => h(NovaIcon, { icon: 'icon-park-outline:edit-two' }) },
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            secondary: true,
            style: 'margin-left: 8px',
            onClick: () => handleEdit(row),
          },
          { default: () => '编辑', icon: () => h(NovaIcon, { icon: 'icon-park-outline:edit-two' }) },
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete(row),
          },
          {
            default: () => '确定删除这个脚本吗？',
            trigger: () =>
              h(
                NButton,
                {
                  size: 'small',
                  type: 'error',
                  secondary: true,
                  style: 'margin-left: 8px',
                },
                { default: () => '删除', icon: () => h(NovaIcon, { icon: 'icon-park-outline:delete-five' }) },
              ),
          },
        ),
      ]
    },
  },
]

// 弹窗相关
const modalVisible = ref(false)
const modalLoading = ref(false)
const modalTitle = ref('')
const isEdit = ref(false)
const editId = ref('')

// 执行弹窗相关
const executeModalVisible = ref(false)
const executeLoading = ref(false)
const currentScript = ref(null)

// 表单相关
const formRef = ref()
const formData = reactive({
  name: '',
  script_type: 'bash',
  return_type: 'text',
  parameters: {},
  content: '',
  description: '',
  status: 'draft',
  timeout: 300,
})

// 参数列表
const parameterList = ref([])

// 执行表单
const executeFormRef = ref()
const executeFormData = reactive({
  parameters: {},
})

const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  script_type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入脚本内容', trigger: 'blur' }],
}

// 处理选中行
function handleChecked(rowKeys) {
  checkedRowKeys.value = rowKeys
}

// 新增
function handleAdd() {
  isEdit.value = false
  modalTitle.value = '新增脚本'
  resetForm()
  modalVisible.value = true
}

// 编辑
function handleEdit(row) {
  isEdit.value = true
  modalTitle.value = '编辑脚本'
  editId.value = row.id
  Object.assign(formData, {
    name: row.name,
    script_type: row.script_type,
    return_type: row.return_type,
    parameters: row.parameters || {},
    content: row.content,
    description: row.description || '',
    status: row.status,
    timeout: row.timeout,
  })

  // 转换参数为列表格式
  parameterList.value = Object.entries(row.parameters || {}).map(([key, description]) => ({
    key,
    description: description || '',
  }))

  modalVisible.value = true
}

// 删除
async function handleDelete(row) {
  try {
    const response = await scriptApi.deleteScript(row.id)
    if (response.success) {
      window.$message?.success('删除成功')
      tableRef.value?.refresh()
    }
  }
  catch (error) {
    console.error('删除失败:', error)
  }
}

// 批量删除
async function handleBatchDelete() {
  if (checkedRowKeys.value.length === 0) {
    window.$message?.warning('请选择要删除的脚本')
    return
  }

  try {
    const promises = checkedRowKeys.value.map(id => scriptApi.deleteScript(id))
    await Promise.all(promises)
    window.$message?.success('批量删除成功')
    checkedRowKeys.value = []
    tableRef.value?.refresh()
  }
  catch (error) {
    console.error('批量删除失败:', error)
  }
}

// 执行脚本
function handleExecuteScript(row) {
  currentScript.value = row
  executeFormData.parameters = {}
  // 初始化参数
  row.parameter_names?.forEach((paramName) => {
    executeFormData.parameters[paramName] = ''
  })
  executeModalVisible.value = true
}

// 查看执行记录
function handleViewExecutions(row) {
  // 跳转到执行记录页面
  router.push({ name: 'data_scripts_exe_detail', query: { script_id: row.id } })
}

// 保存
async function handleSave() {
  try {
    await formRef.value?.validate()
    modalLoading.value = true

    const response = isEdit.value
      ? await scriptApi.updateScript(editId.value, formData)
      : await scriptApi.createScript(formData)

    if (response.success) {
      window.$message?.success(isEdit.value ? '更新成功' : '创建成功')
      modalVisible.value = false
      tableRef.value?.refresh()
    }
  }
  catch (error) {
    console.error('保存失败:', error)
  }
  finally {
    modalLoading.value = false
  }
}

// 执行脚本
async function handleExecute() {
  try {
    executeLoading.value = true

    const response = await scriptApi.executeScript(
      currentScript.value.id,
      executeFormData.parameters,
    )

    if (response.success) {
      window.$message?.success('脚本开始执行')
      executeModalVisible.value = false
      tableRef.value?.refresh()
    }
  }
  catch (error) {
    console.error('执行失败:', error)
  }
  finally {
    executeLoading.value = false
  }
}

// 取消
function handleCancel() {
  resetForm()
}

function handleExecuteCancel() {
  executeFormData.parameters = {}
}

// 重置表单
function resetForm() {
  Object.assign(formData, {
    name: '',
    script_type: 'bash',
    return_type: 'text',
    parameters: {},
    content: '',
    description: '',
    status: 'draft',
    timeout: 300,
  })
  parameterList.value = []
  formRef.value?.restoreValidation()
}

// 创建参数
function createParameter() {
  return {
    key: '',
    description: '',
  }
}

// 监听参数列表变化，更新 formData
watch(
  parameterList,
  (value) => {
    const params = {}
    value.forEach((item) => {
      if (item.key) {
        params[item.key] = item.description || ''
      }
    })
    formData.parameters = params
  },
  { deep: true },
)
</script>

<template>
  <div>
    <CrudTable
      ref="tableRef"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="scriptApi.getScriptList"
      @on-checked="handleChecked"
    >
      <template #queryBar>
        <QueryBarItem label="脚本名称">
          <n-input
            v-model:value="queryItems.name"
            placeholder="请输入脚本名称"
            clearable
          />
        </QueryBarItem>
        <QueryBarItem label="脚本类型">
          <n-select
            v-model:value="queryItems.script_type"
            placeholder="请选择脚本类型"
            clearable
            :options="scriptTypeOptions"
          />
        </QueryBarItem>
        <QueryBarItem label="状态">
          <n-select
            v-model:value="queryItems.status"
            placeholder="请选择状态"
            clearable
            :options="statusOptions"
          />
        </QueryBarItem>
      </template>

      <template #tableHeader>
        <div>
          <NButton type="primary" @click="handleAdd">
            <template #icon>
              <NovaIcon icon="icon-park-outline:plus" />
            </template>
            新增脚本
          </NButton>
          <NButton
            v-if="checkedRowKeys.length > 0"
            ml-10
            type="error"
            @click="handleBatchDelete"
          >
            批量删除
          </NButton>
        </div>
      </template>
    </CrudTable>

    <!-- 新增/编辑弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      width="900px"
      @save="handleSave"
      @cancel="handleCancel"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="left"
        label-width="120px"
      >
        <NGrid :cols="2" :x-gap="24">
          <NFormItemGi label="脚本名称" path="name">
            <n-input
              v-model:value="formData.name"
              placeholder="请输入脚本名称"
            />
          </NFormItemGi>
          <NFormItemGi label="脚本类型" path="script_type">
            <n-select
              v-model:value="formData.script_type"
              placeholder="请选择脚本类型"
              :options="scriptTypeOptions"
            />
          </NFormItemGi>
          <NFormItemGi label="返回类型" path="return_type">
            <n-select
              v-model:value="formData.return_type"
              placeholder="请选择返回类型"
              :options="returnTypeOptions"
            />
          </NFormItemGi>
          <NFormItemGi label="状态" path="status">
            <n-select
              v-model:value="formData.status"
              placeholder="请选择状态"
              :options="statusOptions"
            />
          </NFormItemGi>
          <NFormItemGi label="超时时间(秒)" path="timeout">
            <NInputNumber
              v-model:value="formData.timeout"
              placeholder="请输入超时时间"
              :min="1"
              :max="3600"
            />
          </NFormItemGi>
        </NGrid>

        <n-form-item label="脚本参数" path="parameters">
          <div style="width: 100%">
            <NDynamicInput
              v-model:value="parameterList"
              :on-create="createParameter"
            >
              <template #default="{ value }">
                <div style="display: flex; align-items: center; width: 100%">
                  <n-input
                    v-model:value="value.key"
                    placeholder="参数名"
                    style="margin-right: 12px; width: 200px"
                  />
                  <n-input
                    v-model:value="value.description"
                    placeholder="参数描述"
                  />
                </div>
              </template>
            </NDynamicInput>
          </div>
        </n-form-item>

        <n-form-item label="脚本内容" path="content">
          <n-input
            v-model:value="formData.content"
            type="textarea"
            placeholder="请输入脚本内容"
            :autosize="{ minRows: 10, maxRows: 20 }"
            show-count
          />
        </n-form-item>

        <n-form-item label="备注说明" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入备注说明"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </n-form-item>
      </n-form>
    </CrudModal>

    <!-- 执行脚本弹窗 -->
    <CrudModal
      v-model:visible="executeModalVisible"
      title="执行脚本"
      :loading="executeLoading"
      width="600px"
      @save="handleExecute"
      @cancel="handleExecuteCancel"
    >
      <n-form
        ref="executeFormRef"
        :model="executeFormData"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="脚本名称">
          <n-input :value="currentScript?.name" readonly />
        </n-form-item>
        <n-form-item
          v-for="paramName in currentScript?.parameter_names || []"
          :key="paramName"
          :label="paramName"
        >
          <n-input
            v-model:value="executeFormData.parameters[paramName]"
            :placeholder="`请输入${paramName}`"
          />
        </n-form-item>
      </n-form>
    </CrudModal>
  </div>
</template>
