# 交付矩阵前端附录

交付矩阵前端位于 `web/apps/web-ele/src/views/delivery-matrix/`，分为管理端和展示端两个视角。

## 页面结构

- `admin/index.vue`
  管理端主页面
- `admin/modules/DeliveryTree.vue`
  树结构导航与节点操作
- `admin/modules/DeliveryForm.vue`
  节点与岗位编辑表单
- `admin/modules/PositionEdit.vue`
  岗位编辑子组件
- `dashboard/index.vue`
  展示型矩阵看板

## API 入口

- `src/api/delivery-matrix/index.ts`

主要消费：

- `getTree`
- `createNode`
- `updateNode`
- `deleteNode`
- `updateNodePositions`
- `getValidParents`

## 实现特点

- 管理端采用“左树右表单”布局
- 父节点选择器会过滤当前节点及其子树
- 岗位列表是节点的整体配置，不是局部 patch

## 对应主线文档

- [交付矩阵](/modules/delivery-matrix)
