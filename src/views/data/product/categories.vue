<script setup lang="ts">
import { onMounted, ref } from 'vue' // 引入 onMounted
import { productApi } from '@/service'
import { NCard, NEmpty, NSpace, NTag } from 'naive-ui' // 引入 Naive UI 组件

const categoryList = ref([])

// 定义查询参数
const queryItems = ref({
  page: 1, // 默认页码
  page_size: 10, // 默认每页数量
})

// 获取分类数据
async function getCategoryList(params: object) {
  try {
    const res = await productApi.getProductCategoryList(params)
    if (res) {
      categoryList.value = res.items
    }
    else {
      window.$message?.error('分类数据获取失败')
    }
  }
  catch (error) {
    console.error('请求产品分类接口出错:', error)
    categoryList.value = [] // 清空列表
  }
}

onMounted(() => {
  getCategoryList(queryItems.value)
})
</script>

<template>
  <NSpace vertical :size="16">
    <template v-if="categoryList.length > 0">
      <NCard v-for="category in categoryList" :key="category.id" :title="category.name">
        <template #header-extra>
          <NTag v-if="category.products && category.products.length > 0" type="info" size="small">
            {{ category.products.length }} 个产品
          </NTag>
          <NTag v-else type="default" size="small">
            暂无产品
          </NTag>
        </template>
        <p v-if="category.description">
          {{ category.description }}
        </p>
        <p v-else style="color: #999;">
          暂无描述
        </p>

        <template v-if="category.products && category.products.length > 0" #footer>
          <NSpace>
            <NTag v-for="product in category.products" :key="product.id" type="success" size="small">
              {{ product.name }}
            </NTag>
          </NSpace>
        </template>
      </NCard>
    </template>
    <template v-else>
      <NEmpty description="暂无产品分类数据" />
    </template>
  </NSpace>
</template>

<style scoped>
</style>
