<script setup lang="ts">
import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElSplitter,
  ElSplitterPanel,
  ElSwitch,
  ElTabPane,
  ElTabs,
} from 'element-plus';

defineOptions({ name: 'SplitterDemo' });

// 基础示例
const basicPanelSize = ref('30%');

// 可折叠示例
const isCollapsible = ref(true);

// 禁用拖拽示例
const resizable = ref(true);

// 双向绑定示例
const bindingSize = ref(200);

// 实用场景使用的变量已在下方定义

// 事件监听示例
const eventLogs = ref<string[]>([]);
const eventPanelSize = ref(200);

const handleResizeStart = (index: number, sizes: number[]) => {
  addLog(`开始拖拽 - 分隔条索引: ${index}, 尺寸: [${sizes.join(', ')}]`);
};

const handleResize = (index: number, sizes: number[]) => {
  addLog(`拖拽中 - 分隔条索引: ${index}, 尺寸: [${sizes.join(', ')}]`);
};

const handleResizeEnd = (index: number, sizes: number[]) => {
  addLog(`拖拽结束 - 分隔条索引: ${index}, 尺寸: [${sizes.join(', ')}]`);
};

const addLog = (message: string) => {
  const timestamp = new Date().toLocaleTimeString();
  eventLogs.value.unshift(`[${timestamp}] ${message}`);
  if (eventLogs.value.length > 10) {
    eventLogs.value = eventLogs.value.slice(0, 10);
  }
};

const clearLogs = () => {
  eventLogs.value = [];
};

// 实用场景：代码编辑器布局
const fileTreeSize = ref(250);
const terminalSize = ref(200);
const debugPanelSize = ref(300);
</script>

<template>
  <Page auto-content-height>
    <div class="space-y-6 p-4">
      <ElTabs type="border-card">
        <!-- 基础用法 -->
        <ElTabPane label="1. 基础用法">
          <div class="demo-section">
            <h3 class="demo-title">水平分割（默认）</h3>
            <p class="demo-desc">
              最基本的用法，第一个面板占 30%，第二个面板自动占剩余空间
            </p>
            <div class="demo-container" style="height: 300px">
              <ElSplitter>
                <ElSplitterPanel :size="basicPanelSize">
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">左侧面板</div>
                      <div class="text-sm text-gray-500">
                        占据 {{ basicPanelSize }}
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>
                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">右侧面板</div>
                      <div class="text-sm text-gray-500">自动填充剩余空间</div>
                    </div>
                  </div>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>

          <div class="demo-section mt-6">
            <h3 class="demo-title">垂直分割</h3>
            <p class="demo-desc">设置 layout="vertical" 实现垂直分割</p>
            <div class="demo-container" style="height: 300px">
              <ElSplitter layout="vertical">
                <ElSplitterPanel size="40%">
                  <div class="panel-content">
                    <div class="text-lg font-bold">顶部面板</div>
                  </div>
                </ElSplitterPanel>
                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">底部面板</div>
                  </div>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>

        <!-- 可折叠功能 -->
        <ElTabPane label="2. 可折叠">
          <div class="demo-section">
            <div class="mb-4">
              <ElSwitch
                v-model="isCollapsible"
                active-text="启用折叠"
                inactive-text="禁用折叠"
                inline-prompt
              />
            </div>

            <div class="demo-container" style="height: 400px">
              <ElSplitter>
                <ElSplitterPanel
                  :collapsible="isCollapsible"
                  size="250px"
                  :min="50"
                >
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">左侧面板</div>
                      <div class="text-sm text-gray-500">可折叠</div>
                      <div class="mt-2 text-xs text-gray-400">
                        点击分隔条上的折叠按钮
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel :collapsible="isCollapsible">
                  <div class="panel-content">
                    <div class="text-lg font-bold">中间面板</div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">右侧面板</div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel :collapsible="isCollapsible" size="200px">
                  <ElSplitter layout="vertical">
                    <ElSplitterPanel :collapsible="isCollapsible">
                      <div class="panel-content">
                        <div class="text-sm font-bold">嵌套面板 1</div>
                      </div>
                    </ElSplitterPanel>
                    <ElSplitterPanel :collapsible="isCollapsible">
                      <div class="panel-content">
                        <div class="text-sm font-bold">嵌套面板 2</div>
                      </div>
                    </ElSplitterPanel>
                  </ElSplitter>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>

        <!-- 尺寸控制 -->
        <ElTabPane label="3. 尺寸控制">
          <div class="demo-section">
            <h3 class="demo-title">双向绑定面板大小</h3>
            <div class="mb-4 space-x-2">
              <span>当前大小: {{ bindingSize }}px</span>
              <ElButton size="small" @click="bindingSize = 150">
                设置为 150px
              </ElButton>
              <ElButton size="small" @click="bindingSize = 250">
                设置为 250px
              </ElButton>
              <ElButton size="small" @click="bindingSize = 350">
                设置为 350px
              </ElButton>
            </div>

            <div class="demo-container" style="height: 300px">
              <ElSplitter>
                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">面板 1</div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel
                  v-model:size="bindingSize"
                  :min="100"
                  :max="400"
                >
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">面板 2</div>
                      <div class="font-mono text-2xl">{{ bindingSize }}px</div>
                      <div class="mt-2 text-xs text-gray-400">
                        最小 100px，最大 400px
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">面板 3</div>
                  </div>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>

        <!-- 禁用拖拽 -->
        <ElTabPane label="4. 禁用拖拽">
          <div class="demo-section">
            <div class="mb-4">
              <ElSwitch
                v-model="resizable"
                active-text="启用拖拽"
                inactive-text="禁用拖拽"
                inline-prompt
              />
            </div>

            <div class="demo-container" style="height: 300px">
              <ElSplitter>
                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">面板 1</div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel :resizable="resizable">
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">面板 2</div>
                      <div
                        class="text-sm"
                        :class="resizable ? 'text-green-500' : 'text-red-500'"
                      >
                        拖拽 {{ resizable ? '启用' : '禁用' }}
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">面板 3</div>
                  </div>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>

        <!-- 事件监听 -->
        <ElTabPane label="5. 事件监听">
          <div class="demo-section">
            <div class="mb-4">
              <ElButton size="small" @click="clearLogs">清空日志</ElButton>
            </div>

            <div class="demo-container" style="height: 300px">
              <ElSplitter
                @resize-start="handleResizeStart"
                @resize="handleResize"
                @resize-end="handleResizeEnd"
              >
                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="mb-4 text-lg font-bold">拖拽日志</div>
                    <div class="event-logs">
                      <div
                        v-for="(log, index) in eventLogs"
                        :key="index"
                        class="log-item"
                      >
                        {{ log }}
                      </div>
                      <div
                        v-if="eventLogs.length === 0"
                        class="text-sm text-gray-400"
                      >
                        拖拽分隔条查看事件日志
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel
                  v-model:size="eventPanelSize"
                  :min="100"
                  :max="400"
                >
                  <div class="panel-content">
                    <div class="text-center">
                      <div class="mb-2 text-lg font-bold">可拖拽面板</div>
                      <div class="font-mono text-2xl">
                        {{ eventPanelSize }}px
                      </div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <ElSplitterPanel>
                  <div class="panel-content">
                    <div class="text-lg font-bold">面板 3</div>
                  </div>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>

        <!-- 实用场景 -->
        <ElTabPane label="6. 实用场景">
          <div class="demo-section">
            <h3 class="demo-title">代码编辑器布局</h3>
            <p class="demo-desc">模拟 VS Code 的布局结构</p>

            <div class="demo-container" style="height: 600px">
              <ElSplitter>
                <!-- 左侧：文件树 -->
                <ElSplitterPanel
                  v-model:size="fileTreeSize"
                  collapsible
                  :min="200"
                  :max="400"
                >
                  <div class="panel-content bg-gray-50">
                    <div class="mb-2 text-sm font-bold">📁 文件浏览器</div>
                    <div class="text-xs text-gray-500">
                      <div>📂 src</div>
                      <div class="ml-4">📂 components</div>
                      <div class="ml-4">📂 views</div>
                      <div class="ml-4">📄 main.ts</div>
                    </div>
                  </div>
                </ElSplitterPanel>

                <!-- 中间：编辑区 + 终端 -->
                <ElSplitterPanel>
                  <ElSplitter layout="vertical">
                    <!-- 编辑器 -->
                    <ElSplitterPanel>
                      <div class="panel-content bg-white">
                        <div class="mb-2 text-sm font-bold">📝 代码编辑器</div>
                        <div class="font-mono text-xs text-gray-600">
                          <div>&lt;template&gt;</div>
                          <div class="ml-4">
                            &lt;div&gt;Hello World&lt;/div&gt;
                          </div>
                          <div>&lt;/template&gt;</div>
                        </div>
                      </div>
                    </ElSplitterPanel>

                    <!-- 终端 -->
                    <ElSplitterPanel
                      v-model:size="terminalSize"
                      collapsible
                      :min="150"
                    >
                      <div class="panel-content bg-gray-900 text-white">
                        <div class="mb-2 text-sm font-bold">💻 终端</div>
                        <div class="font-mono text-xs">
                          <div>$ npm run dev</div>
                          <div class="text-green-400">✓ Server running...</div>
                        </div>
                      </div>
                    </ElSplitterPanel>
                  </ElSplitter>
                </ElSplitterPanel>

                <!-- 右侧：调试面板 -->
                <ElSplitterPanel
                  v-model:size="debugPanelSize"
                  collapsible
                  :min="250"
                >
                  <ElSplitter layout="vertical">
                    <ElSplitterPanel collapsible>
                      <div class="panel-content bg-gray-50">
                        <div class="mb-2 text-sm font-bold">🔍 变量监视</div>
                        <div class="text-xs text-gray-600">
                          <div>count: 0</div>
                          <div>isActive: true</div>
                        </div>
                      </div>
                    </ElSplitterPanel>

                    <ElSplitterPanel collapsible>
                      <div class="panel-content bg-gray-50">
                        <div class="mb-2 text-sm font-bold">📊 调用堆栈</div>
                        <div class="text-xs text-gray-600">
                          <div>main.ts:10</div>
                          <div>app.vue:25</div>
                        </div>
                      </div>
                    </ElSplitterPanel>
                  </ElSplitter>
                </ElSplitterPanel>
              </ElSplitter>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>

<style scoped>
.demo-section {
  padding: 20px;
}

.demo-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.demo-desc {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 16px;
}

.demo-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.panel-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
  background: var(--el-bg-color);
}

.event-logs {
  max-height: 200px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
}

.log-item {
  padding: 4px 8px;
  margin-bottom: 4px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  color: var(--el-text-color-regular);
}

/* 自定义滚动条 */
.event-logs::-webkit-scrollbar {
  width: 6px;
}

.event-logs::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.event-logs::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
}
</style>
