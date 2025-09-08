import { request } from '../http'

export const scriptApi = {
  // 获取脚本列表
  getScriptList(params: object) {
    return request.Get('/system/scripts/', { params })
  },

  // 获取脚本详情
  getScriptDetail(id: string) {
    return request.Get(`/system/scripts/${id}/`)
  },

  // 创建脚本
  createScript(data: object) {
    return request.Post('/system/scripts/', data)
  },

  // 更新脚本
  updateScript(id: string, data: object) {
    return request.Put(`/system/scripts/${id}/`, data)
  },

  // 删除脚本
  deleteScript(id: string) {
    return request.Delete(`/system/scripts/${id}/`)
  },

  // 执行脚本
  executeScript(id: string, parameters = {}) {
    return request.Post(`/system/scripts/${id}/execute/`, { parameters })
  },
}

// 脚本执行记录相关API
export const executionApi = {
  // 获取执行记录列表
  getExecutionList(params: object) {
    return request.Get('/system/executions/', { params })
  },

  // 获取执行记录详情
  getExecutionDetail(id: string) {
    return request.Get(`/system/executions/${id}/`)
  },
}
