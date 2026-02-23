<script lang="ts" setup>
import type { UserMessage, UserMessageListParams } from '#/api/core/message';

import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import dayjs from 'dayjs';
import {
  ElButton,
  ElCard,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  deleteInboxMessageApi,
  getInboxMessageListApi,
  markAllMessagesReadApi,
  markMessageReadApi,
} from '#/api/core/message';

defineOptions({ name: 'MessageCenterPage' });

const router = useRouter();
const loading = ref(false);
const messageList = ref<UserMessage[]>([]);

const pager = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
});

const queryForm = reactive<{
  is_read: '' | 'false' | 'true';
  keyword: string;
  message_type: '' | 'announcement' | 'internal' | 'system';
}>({
  is_read: '',
  keyword: '',
  message_type: '',
});

function formatTime(value?: null | string) {
  if (!value) {
    return '-';
  }
  const date = dayjs(value);
  if (!date.isValid()) {
    return value;
  }
  return date.format('YYYY-MM-DD HH:mm:ss');
}

function getPriorityLabel(priority: string) {
  const map: Record<string, string> = {
    high: '高',
    low: '低',
    normal: '普通',
    urgent: '紧急',
  };
  return map[priority] || priority;
}

function getPriorityType(priority: string) {
  const map: Record<
    string,
    'danger' | 'info' | 'primary' | 'success' | 'warning'
  > = {
    high: 'warning',
    low: 'info',
    normal: 'success',
    urgent: 'danger',
  };
  return map[priority] || 'info';
}

function getMessageTypeLabel(messageType: string) {
  const map: Record<string, string> = {
    announcement: '公告',
    internal: '站内信',
    system: '系统',
  };
  return map[messageType] || messageType;
}

async function loadMessages() {
  loading.value = true;
  try {
    const params: UserMessageListParams = {
      page: pager.page,
      pageSize: pager.pageSize,
    };
    if (queryForm.keyword.trim()) {
      params.keyword = queryForm.keyword.trim();
    }
    if (queryForm.message_type) {
      params.message_type = queryForm.message_type;
    }
    if (queryForm.is_read !== '') {
      params.is_read = queryForm.is_read === 'true';
    }

    const result = await getInboxMessageListApi(params);
    messageList.value = result.items || [];
    pager.total = result.total || 0;
  } catch (error) {
    console.error('加载站内信失败:', error);
  } finally {
    loading.value = false;
  }
}

async function handleMarkRead(row: UserMessage) {
  if (row.is_read) {
    return;
  }
  await markMessageReadApi(row.id);
  row.is_read = true;
  row.read_at = dayjs().toISOString();
  ElMessage.success('已标记为已读');
}

async function handleMarkAllRead() {
  await markAllMessagesReadApi();
  messageList.value = messageList.value.map((item) => ({
    ...item,
    is_read: true,
    read_at: item.read_at || dayjs().toISOString(),
  }));
  ElMessage.success('全部消息已标记为已读');
}

function handleDelete(row: UserMessage) {
  ElMessageBox.confirm(`确认删除消息「${row.title}」吗？`, '删除消息', {
    type: 'warning',
  })
    .then(async () => {
      await deleteInboxMessageApi(row.id);
      ElMessage.success('删除成功');
      await loadMessages();
    })
    .catch(() => {});
}

function handleSearch() {
  pager.page = 1;
  loadMessages();
}

function handleReset() {
  queryForm.keyword = '';
  queryForm.message_type = '';
  queryForm.is_read = '';
  pager.page = 1;
  loadMessages();
}

function handlePageChange(page: number) {
  pager.page = page;
  loadMessages();
}

function handlePageSizeChange(pageSize: number) {
  pager.pageSize = pageSize;
  pager.page = 1;
  loadMessages();
}

function handleOpenLink(row: UserMessage) {
  if (!row.link) {
    return;
  }
  router.push(row.link);
}

onMounted(() => {
  loadMessages();
});
</script>

<template>
  <Page auto-content-height>
    <ElCard shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="text-base font-semibold">站内信中心</div>
          <div class="flex gap-2">
            <ElButton type="primary" @click="handleMarkAllRead">
              全部已读
            </ElButton>
            <ElButton @click="loadMessages">刷新</ElButton>
          </div>
        </div>
      </template>

      <ElForm inline @submit.prevent>
        <ElFormItem label="关键词">
          <ElInput
            v-model="queryForm.keyword"
            clearable
            placeholder="标题或内容"
            style="width: 220px"
            @keyup.enter="handleSearch"
          />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElSelect
            v-model="queryForm.message_type"
            clearable
            placeholder="全部"
            style="width: 140px"
          >
            <ElOption label="系统" value="system" />
            <ElOption label="站内信" value="internal" />
            <ElOption label="公告" value="announcement" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect
            v-model="queryForm.is_read"
            clearable
            placeholder="全部"
            style="width: 120px"
          >
            <ElOption label="未读" value="false" />
            <ElOption label="已读" value="true" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" @click="handleSearch">查询</ElButton>
          <ElButton @click="handleReset">重置</ElButton>
        </ElFormItem>
      </ElForm>

      <ElTable :data="messageList" v-loading="loading" border>
        <ElTableColumn label="消息内容" min-width="340">
          <template #default="scope">
            <div v-if="scope?.row" class="message-title">
              <span>{{ scope.row.title }}</span>
              <ElTag
                v-if="!scope.row.is_read"
                class="ml-2"
                size="small"
                type="danger"
              >
                未读
              </ElTag>
            </div>
            <div v-if="scope?.row" class="message-content">
              {{ scope.row.content }}
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="类型" width="110">
          <template #default="scope">
            {{ scope?.row ? getMessageTypeLabel(scope.row.message_type) : '-' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="优先级" width="110">
          <template #default="scope">
            <ElTag
              v-if="scope?.row"
              :type="getPriorityType(scope.row.priority)"
              size="small"
            >
              {{ getPriorityLabel(scope.row.priority) }}
            </ElTag>
            <span v-else>-</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="发送人" min-width="120">
          <template #default="scope">
            {{ scope?.row?.sender_name || '系统' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="接收时间" min-width="180">
          <template #default="scope">
            {{ scope?.row ? formatTime(scope.row.sys_create_datetime) : '-' }}
          </template>
        </ElTableColumn>
        <ElTableColumn fixed="right" label="操作" width="220">
          <template #default="scope">
            <template v-if="scope?.row">
              <ElButton
                :disabled="scope.row.is_read"
                link
                type="primary"
                @click="handleMarkRead(scope.row)"
              >
                标记已读
              </ElButton>
              <ElButton
                v-if="scope.row.link"
                link
                type="primary"
                @click="handleOpenLink(scope.row)"
              >
                查看详情
              </ElButton>
              <ElButton link type="danger" @click="handleDelete(scope.row)">
                删除
              </ElButton>
            </template>
          </template>
        </ElTableColumn>
      </ElTable>

      <div class="mt-4 flex justify-end">
        <ElPagination
          :current-page="pager.page"
          :page-size="pager.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pager.total"
          background
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </ElCard>
  </Page>
</template>

<style scoped>
.message-title {
  display: flex;
  align-items: center;
  font-weight: 600;
}

.message-content {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.4;
  word-break: break-word;
}
</style>
