<!-- src/views/HomePage.vue -->
<script setup>
import { ref } from 'vue'
import { NCard, NDivider, NSelect, NSpace } from 'naive-ui'
import DataTable from './components/list.vue'

// 模拟项目列表
const projectOptions = [
  {
    label: '项目 A',
    value: 'projectA',
  },
  {
    label: '项目 B',
    value: 'projectB',
  },
  {
    label: '项目 C',
    value: 'projectC',
  },
]

// 选中的项目
const selectedProject = ref(null)

// 处理项目选择变化
function handleProjectChange(value) {
  selectedProject.value = value
}
</script>

<template>
  <div class="home-page-container">
    <NCard title="数据总览" :bordered="false">
      <NSpace vertical>
        <NSpace align="center">
          <span>选择项目:</span>
          <NSelect
            v-model:value="selectedProject"
            :options="projectOptions"
            placeholder="请选择项目"
            style="width: 200px"
            clearable
            @update:value="handleProjectChange"
          />
        </NSpace>

        <NDivider />

        <!-- 数据表格组件，通过 props 传递 selectedProject -->
        <DataTable :selected-project="selectedProject" />
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.home-page-container {
  padding: 20px;
  width: 100%;
  height: 1000px;
}
</style>
