import { request } from '../http'

/**
 * 领导者看板
 * @param params
 */
export function getLeaderDashboard(params: any) {
  return request.Get<Service.ResponseResult<Api.Iteration.LeaderDashboardItem[]>>('/iterations/dashboard/leader/', { params })
}

/**
 * 项目看板
 * @param product_id
 * @param params
 */
export function getProjectDashboard(params: any) {
  const { product_id, ...rest } = params
  return request.Get<Service.ResponseResult<Api.Iteration.ProjectDashboardItem[]>>(`/iterations/dashboard/project/${product_id}/`, { params: rest })
}

/**
 * 获取迭代列表
 * @param params
 */
export function getIterationList(params: any) {
  const { product_id, ...rest } = params
  if (product_id) {
    return request.Get<Service.ResponseResult<Api.Iteration.IterationItem[]>>(`/iterations/project/${product_id}/iterations/`, { params: rest })
  }
  return request.Get<Service.ResponseResult<Api.Iteration.IterationItem[]>>('/iterations/iterations/', { params })
}

/**
 * 创建迭代
 * @param data
 */
export function createIteration(data: any) {
  return request.Post('/iterations/iterations/', data)
}

/**
 * 获取迭代详情
 * @param id
 */
export function getIteration(id: number) {
  return request.Get(`/iterations/iterations/${id}/`)
}

/**
 * 更新迭代
 * @param id
 * @param data
 */
export function updateIteration(id: number, data: any) {
  return request.Put(`/iterations/iterations/${id}/`, data)
}

/**
 * 删除迭代
 * @param id
 */
export function deleteIteration(id: number) {
  return request.Delete(`/iterations/iterations/${id}/`)
}

/**
 * 获取指定项目的所有迭代
 * @param product_id
 * @param params
 */
export function getProjectIterations(product_id: number, params: any) {
  return request.Get<Service.ResponseResult<Api.Iteration.IterationItem[]>>(`/iterations/project/${product_id}/iterations/`, { params })
}

/**
 * 获取指标列表
 * @param params
 */
export function getMetricsList(params: any) {
  return request.Get('/iterations/metrics/', { params })
}

/**
 * 获取单个指标
 * @param id
 */
export function getMetric(id: number) {
  return request.Get(`/iterations/metrics/${id}/`)
}

/**
 * 手动创建迭代指标
 * @param data
 */
export function createMetric(data: any) {
  return request.Post('/iterations/metrics/create/', data)
}

/**
 * 手动触发指标更新
 */
export function updateMetrics() {
  return request.Post('/iterations/metrics/update/')
}

/**
 * 切换当前迭代
 * @param data
 */
export function switchIteration(data: any) {
  return request.Post('/iterations/iteration/switch/', data)
}
