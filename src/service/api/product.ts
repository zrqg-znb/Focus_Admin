import { request } from '@/service/http'

export const productApi = {
  // 获取产品列表
  getProductList(params: any) {
    return request.Get('/iterations/products/', { params })
  },

  // 创建产品
  createProduct(data: any) {
    return request.Post('/iterations/products/', data)
  },

  // 获取产品详情
  getProduct(id: number) {
    return request.Get(`/iterations/products/${id}/`)
  },

  // 更新产品
  updateProduct(id: number, data: any) {
    return request.Put(`/iterations/products/${id}/`, data)
  },

  // 删除产品
  deleteProduct(id: number) {
    return request.Delete(`/iterations/products/${id}/`)
  },
}
