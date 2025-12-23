<script setup lang="ts">
import { ref } from 'vue';
import { ElTabs, ElTabPane, ElCard, ElAlert } from 'element-plus';
import { JsonEditor } from './index';

// 示例 1: 基础用法
const basicJson = ref('{\n  "name": "John Doe",\n  "age": 30,\n  "email": "john@example.com",\n  "active": true\n}');
const basicIsValid = ref(true);

// 示例 2: 对象初始化
const objectJson = ref({
  id: 1,
  username: 'alice',
  roles: ['admin', 'user'],
  metadata: {
    lastLogin: '2025-11-13',
    loginCount: 42
  }
});

// 示例 3: 只读模式
const readOnlyJson = ref({
  status: 'success',
  code: 200,
  message: 'Operation completed successfully',
  data: {
    id: 123,
    title: 'Example Data'
  }
});

// 示例 4: 配置编辑
const configJson = ref({
  theme: 'dark',
  language: 'zh-CN',
  notifications: {
    enabled: true,
    sound: false,
    desktop: true
  },
  privacy: {
    profilePublic: false,
    showOnlineStatus: true
  }
});

// 事件处理
function handleValid() {
  basicIsValid.value = true;
}

function handleInvalid(error: string) {
  basicIsValid.value = false;
  console.error('JSON 无效:', error);
}
</script>

<template>
  <div class="json-editor-example">
    <h1>JSON Editor 组件示例</h1>
    
    <ElTabs>
      <!-- 示例 1: 基础用法 -->
      <ElTabPane label="基础用法">
        <ElCard class="box-card">
          <template #header>
            <div class="card-header">
              <span>简单的 JSON 编辑器</span>
              <span class="status" :class="{ valid: basicIsValid }">
                {{ basicIsValid ? '✓ 有效' : '✗ 无效' }}
              </span>
            </div>
          </template>

          <JsonEditor 
            v-model="basicJson"
            placeholder="输入或粘贴 JSON 内容"
            @valid="handleValid"
            @invalid="handleInvalid"
          />
        </ElCard>
      </ElTabPane>

      <!-- 示例 2: 对象初始化 -->
      <ElTabPane label="对象初始化">
        <ElCard class="box-card">
          <template #header>
            <span>直接传入对象进行初始化</span>
          </template>

          <p class="description">
            直接传入 JavaScript 对象，组件会自动转换为 JSON 字符串，并以指定的缩进格式显示。
          </p>

          <JsonEditor 
            :model-value="objectJson"
            :indent="2"
            @change="(json) => console.log('Changed:', json)"
          />
        </ElCard>
      </ElTabPane>

      <!-- 示例 3: 只读模式 -->
      <ElTabPane label="只读模式">
        <ElCard class="box-card">
          <template #header>
            <span>只读模式 - 用于展示 API 响应</span>
          </template>

          <p class="description">
            设置 readonly 属性为 true，可以创建只读的 JSON 查看器，适合展示 API 响应或配置信息。
          </p>

          <JsonEditor 
            :model-value="readOnlyJson"
            readonly
            :show-format-button="false"
            line-numbers
          />
        </ElCard>
      </ElTabPane>

      <!-- 示例 4: 配置编辑 -->
      <ElTabPane label="配置编辑">
        <ElCard class="box-card">
          <template #header>
            <span>应用配置编辑</span>
          </template>

          <p class="description">
            用于编辑应用配置文件。支持格式化、压缩等功能。
          </p>

          <JsonEditor 
            :model-value="configJson"
            :min-height="300"
            :max-height="500"
            placeholder="编辑配置信息"
            highlight-syntax
          />
        </ElCard>
      </ElTabPane>

      <!-- 示例 5: 功能介绍 -->
      <ElTabPane label="功能介绍">
        <div class="features">
          <h3>🎯 主要功能</h3>
          
          <div class="feature-group">
            <h4>✨ 编辑功能</h4>
            <ul>
              <li>📝 实时 JSON 编辑</li>
              <li>🔍 JSON 验证与错误提示</li>
              <li>🎨 语法高亮显示</li>
              <li>📊 行号显示</li>
            </ul>
          </div>

          <div class="feature-group">
            <h4>🛠️ 工具功能</h4>
            <ul>
              <li>✂️ 格式化 JSON (Ctrl+Shift+F)</li>
              <li>📦 压缩 JSON</li>
              <li>📋 复制到剪贴板</li>
              <li>🗑️ 清空内容</li>
            </ul>
          </div>

          <div class="feature-group">
            <h4>⚙️ 配置选项</h4>
            <ul>
              <li>🔒 只读模式</li>
              <li>🚫 禁用编辑</li>
              <li>📏 自定义高度</li>
              <li>🎛️ 缩进控制</li>
            </ul>
          </div>

          <div class="feature-group">
            <h4>📡 事件系统</h4>
            <ul>
              <li>✅ valid - JSON 有效时触发</li>
              <li>❌ invalid - JSON 无效时触发</li>
              <li>🔄 change - 内容变化时触发</li>
              <li>📤 update:modelValue - v-model 更新</li>
            </ul>
          </div>

          <ElAlert 
            title="快捷键"
            type="info"
            :closable="false"
            description="按下 Ctrl+Shift+F (Windows/Linux) 或 Cmd+Shift+F (Mac) 快速格式化 JSON"
          />
        </div>
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<style scoped lang="scss">
.json-editor-example {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;

  h1 {
    margin-bottom: 20px;
    color: hsl(var(--foreground));
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;

    .status {
      font-size: 12px;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 4px;
      background-color: hsl(var(--destructive) / 0.1);
      color: hsl(var(--destructive));
      transition: all 0.2s ease;

      &.valid {
        background-color: hsl(var(--primary) / 0.1);
        color: hsl(var(--primary));
      }
    }
  }

  .box-card {
    margin-bottom: 20px;

    :deep(.el-card__body) {
      padding: 20px;
    }
  }

  .description {
    color: hsl(var(--muted-foreground));
    margin-bottom: 16px;
    font-size: 14px;
  }

  .features {
    padding: 20px;

    h3 {
      font-size: 18px;
      margin-bottom: 20px;
      color: hsl(var(--foreground));
    }

    .feature-group {
      margin-bottom: 24px;

      h4 {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        color: hsl(var(--primary));
      }

      ul {
        list-style: none;
        padding-left: 0;

        li {
          padding: 8px 0;
          color: hsl(var(--foreground));
          font-size: 14px;

          &:before {
            content: '';
            margin-right: 8px;
          }
        }
      }
    }

    :deep(.el-alert) {
      margin-top: 20px;
    }
  }
}
</style>

