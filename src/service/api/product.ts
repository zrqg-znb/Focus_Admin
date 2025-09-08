import { request } from '@/service/http'

export const productApi = {
  // 获取产品分类
  getProductCategoryList(params: object) {
    return request.Get('/release_gap/categories/', { params })
  },

  // 创建产品分类
  createProductCategory(data: object) {
    return request.Post('/release_gap/categories/', data)
  },
  // 更新产品分类
  updateProductCategory(id: string, data: object) {
    return request.Put(`/release_gap/categories/${id}/`, data)
  },
  // 删除产品分类

  // 获取产品列表

  // 创建产品

  // 获取产品详情

  // 更新产品

  // 删除产品
}
