<script setup lang="ts">
import { ref } from 'vue';

import { ElButton, ElTabPane, ElTabs, ElTree } from 'element-plus';

import { FuPage } from '#/components/fu-page';

defineOptions({ name: 'FuPageDemo' });

// 示例 1: 基础用法
const selectedItem1 = ref('Item 1');

// 示例 2: 树形结构
interface TreeNode {
  id: string;
  label: string;
  children?: TreeNode[];
}

const treeData = ref<TreeNode[]>([
  {
    id: '1',
    label: '一级 1',
    children: [
      {
        id: '1-1',
        label: '二级 1-1',
        children: [
          { id: '1-1-1', label: '三级 1-1-1' },
          { id: '1-1-2', label: '三级 1-1-2' },
        ],
      },
      { id: '1-2', label: '二级 1-2' },
    ],
  },
  {
    id: '2',
    label: '一级 2',
    children: [
      { id: '2-1', label: '二级 2-1' },
      { id: '2-2', label: '二级 2-2' },
    ],
  },
  {
    id: '3',
    label: '一级 3',
    children: [
      { id: '3-1', label: '二级 3-1' },
      { id: '3-2', label: '二级 3-2' },
    ],
  },
]);

const selectedNode = ref<TreeNode>();

function handleNodeClick(data: TreeNode) {
  selectedNode.value = data;
}

// 示例 3: 列表选择
const listItems = ref([
  { id: '1', name: '用户管理', desc: '管理系统用户' },
  { id: '2', name: '角色管理', desc: '管理用户角色' },
  { id: '3', name: '权限管理', desc: '管理系统权限' },
  { id: '4', name: '菜单管理', desc: '管理系统菜单' },
  { id: '5', name: '部门管理', desc: '管理组织架构' },
]);

const selectedListItem = ref(listItems.value[0]!);

function selectListItem(item: any) {
  selectedListItem.value = item;
}
</script>

<template>
  <div class="p-4">
    <ElTabs type="border-card">
      <!-- 示例 1: 基础用法 -->
      <ElTabPane label="1. 基础用法">
        <FuPage>
          <template #left>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">左侧内容</div>
              <div class="space-y-2">
                <div
                  v-for="i in 10"
                  :key="i"
                  class="cursor-pointer rounded p-2 hover:bg-gray-100"
                  :class="{ 'bg-blue-50': selectedItem1 === `Item ${i}` }"
                  @click="selectedItem1 = `Item ${i}`"
                >
                  Item {{ i }}
                </div>
              </div>
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">右侧内容</div>
              <div class="rounded bg-gray-50 p-4">
                <p class="mb-2">当前选中: {{ selectedItem1 }}</p>
                <p class="text-sm text-gray-500">
                  这是一个基础的左右分栏示例，左侧可以选择项目，右侧显示详情。
                </p>
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>

      <!-- 示例 2: 树形结构 -->
      <ElTabPane label="2. 树形结构">
        <FuPage left-title="菜单树" right-title="菜单详情">
          <template #left>
            <div class="p-4">
              <ElTree
                :data="treeData"
                :props="{ label: 'label', children: 'children' }"
                node-key="id"
                default-expand-all
                @node-click="handleNodeClick"
              />
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div v-if="selectedNode" class="space-y-4">
                <div>
                  <div class="mb-2 text-sm text-gray-500">节点 ID</div>
                  <div class="font-mono">{{ selectedNode.id }}</div>
                </div>
                <div>
                  <div class="mb-2 text-sm text-gray-500">节点名称</div>
                  <div class="text-lg font-bold">{{ selectedNode.label }}</div>
                </div>
                <div>
                  <div class="mb-2 text-sm text-gray-500">子节点数量</div>
                  <div>{{ selectedNode.children?.length || 0 }}</div>
                </div>
              </div>
              <div v-else class="text-center text-gray-400">
                请在左侧选择一个节点
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>

      <!-- 示例 3: 自定义头部 -->
      <ElTabPane label="3. 自定义头部">
        <FuPage>
          <template #left-header>
            <div class="flex items-center justify-between">
              <span class="font-bold">功能列表</span>
              <ElButton size="small" type="primary">新增</ElButton>
            </div>
          </template>

          <template #right-header>
            <div class="flex items-center justify-between">
              <span class="font-bold">功能详情</span>
              <div class="space-x-2">
                <ElButton size="small">编辑</ElButton>
                <ElButton size="small" type="danger">删除</ElButton>
              </div>
            </div>
          </template>

          <template #left>
            <div class="p-4">
              <div class="space-y-2">
                <div
                  v-for="item in listItems"
                  :key="item.id"
                  class="cursor-pointer rounded border p-3 transition-all hover:border-blue-400 hover:shadow-sm"
                  :class="{
                    'border-blue-400 bg-blue-50':
                      selectedListItem.id === item.id,
                  }"
                  @click="selectListItem(item)"
                >
                  <div class="font-bold">{{ item.name }}</div>
                  <div class="text-xs text-gray-500">{{ item.desc }}</div>
                </div>
              </div>
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div class="space-y-4">
                <div>
                  <div class="mb-2 text-sm text-gray-500">功能名称</div>
                  <div class="text-xl font-bold">
                    {{ selectedListItem.name }}
                  </div>
                </div>
                <div>
                  <div class="mb-2 text-sm text-gray-500">功能描述</div>
                  <div>{{ selectedListItem.desc }}</div>
                </div>
                <div>
                  <div class="mb-2 text-sm text-gray-500">功能 ID</div>
                  <div class="font-mono">{{ selectedListItem.id }}</div>
                </div>
                <div class="rounded bg-blue-50 p-4">
                  <div class="mb-2 text-sm font-bold">提示</div>
                  <div class="text-sm text-gray-600">
                    这是一个自定义头部的示例，左右两侧的卡片头部都可以自定义内容。
                  </div>
                </div>
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>

      <!-- 示例 4: 自定义宽度 -->
      <ElTabPane label="4. 自定义宽度">
        <FuPage
          left-width="300px"
          :left-min-width="250"
          :left-max-width="500"
          left-title="宽度可调整"
          right-title="主内容区"
        >
          <template #left>
            <div class="p-4">
              <div class="mb-4 rounded bg-blue-50 p-3">
                <div class="mb-2 text-sm font-bold">提示</div>
                <div class="text-xs text-gray-600">
                  <p>• 初始宽度: 300px</p>
                  <p>• 最小宽度: 250px</p>
                  <p>• 最大宽度: 500px</p>
                  <p>• 可以拖拽调整</p>
                  <p>• 可以点击折叠</p>
                </div>
              </div>
              <div class="space-y-2">
                <div v-for="i in 15" :key="i" class="rounded bg-gray-100 p-2">
                  列表项 {{ i }}
                </div>
              </div>
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">主内容区域</div>
              <div class="space-y-4">
                <div
                  v-for="i in 20"
                  :key="i"
                  class="rounded border p-4 hover:shadow-sm"
                >
                  <div class="mb-2 font-bold">内容块 {{ i }}</div>
                  <div class="text-sm text-gray-500">
                    这是一些示例内容，用于展示右侧区域的滚动效果。
                  </div>
                </div>
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>

      <!-- 示例 5: 带 Page 标题 -->
      <ElTabPane label="5. 带 Page 标题">
        <FuPage
          page-title="系统管理"
          page-description="管理系统的各项配置和设置"
        >
          <template #extra>
            <div class="space-x-2">
              <ElButton type="primary">保存</ElButton>
              <ElButton>重置</ElButton>
            </div>
          </template>

          <template #left>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">配置项</div>
              <div class="space-y-2">
                <div
                  v-for="i in 8"
                  :key="i"
                  class="cursor-pointer rounded p-3 hover:bg-gray-100"
                >
                  配置项 {{ i }}
                </div>
              </div>
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">配置详情</div>
              <div class="rounded bg-gray-50 p-4">
                <p class="mb-4">
                  这个示例展示了如何使用 Page
                  组件的标题、描述和额外内容插槽。
                </p>
                <p class="text-sm text-gray-500">
                  顶部会显示 "系统管理" 标题和描述，右上角有操作按钮。
                </p>
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>

      <!-- 示例 6: 禁用调整 -->
      <ElTabPane label="6. 禁用调整">
        <FuPage
          :left-resizable="false"
          :left-collapsible="false"
          left-width="200px"
          left-title="固定宽度"
          right-title="主内容"
        >
          <template #left>
            <div class="p-4">
              <div class="mb-4 rounded bg-yellow-50 p-3">
                <div class="mb-2 text-sm font-bold">提示</div>
                <div class="text-xs text-gray-600">
                  <p>• 固定宽度 200px</p>
                  <p>• 不可调整大小</p>
                  <p>• 不可折叠</p>
                </div>
              </div>
              <div class="space-y-2">
                <div v-for="i in 5" :key="i" class="rounded bg-gray-100 p-2">
                  导航 {{ i }}
                </div>
              </div>
            </div>
          </template>

          <template #right>
            <div class="p-4">
              <div class="mb-4 text-lg font-bold">主内容区域</div>
              <div class="rounded bg-gray-50 p-4">
                <p>
                  这个示例展示了固定宽度的左侧面板，不可调整大小，也不可折叠。
                </p>
              </div>
            </div>
          </template>
        </FuPage>
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<style scoped>
/* 自定义样式 */
</style>
