<script lang="ts" setup>
import type {
  AnnouncementItem,
  AnnouncementListParams,
  MessagePriority,
} from '#/api/core/message';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';
import dayjs from 'dayjs';
import {
  ElAlert,
  ElButton,
  ElCard,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';

import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';
import {
  createAnnouncementApi,
  deleteAnnouncementApi,
  getAnnouncementListApi,
  publishAnnouncementApi,
  revokeAnnouncementApi,
  sendInternalMessageApi,
  updateAnnouncementApi,
} from '#/api/core/message';

defineOptions({ name: 'AnnouncementSettingsPage' });

const userStore = useUserStore();
const isSuperAdmin = computed(() =>
  Boolean((userStore.userInfo as any)?.is_superuser),
);

const announcementLoading = ref(false);
const announcementSubmitting = ref(false);
const announcementDialogVisible = ref(false);
const announcementList = ref<AnnouncementItem[]>([]);
const announcementEditingId = ref<null | string>(null);

const announcementPager = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
});

const announcementFilter = reactive<{
  status: '' | number;
  title: string;
}>({
  status: '',
  title: '',
});

const announcementForm = reactive<{
  content: string;
  expire_at: '' | null | string;
  priority: MessagePriority;
  title: string;
}>({
  content: '',
  expire_at: '',
  priority: 'normal',
  title: '',
});

const sendSubmitting = ref(false);
const sendForm = reactive<{
  content: string;
  link: string;
  priority: MessagePriority;
  receiver_ids: string[];
  title: string;
}>({
  content: '',
  link: '',
  priority: 'normal',
  receiver_ids: [],
  title: '',
});

const receiverIdsModel = computed<string | string[] | undefined>({
  get() {
    return sendForm.receiver_ids;
  },
  set(value) {
    if (Array.isArray(value)) {
      sendForm.receiver_ids = value;
      return;
    }
    if (typeof value === 'string' && value) {
      sendForm.receiver_ids = [value];
      return;
    }
    sendForm.receiver_ids = [];
  },
});

function formatDate(value?: null | string) {
  if (!value) {
    return '-';
  }
  const date = dayjs(value);
  if (!date.isValid()) {
    return value;
  }
  return date.format('YYYY-MM-DD HH:mm:ss');
}

function getStatusLabel(status: number) {
  const map: Record<number, string> = {
    0: '草稿',
    1: '已发布',
    2: '已撤回',
  };
  return map[status] || `${status}`;
}

function getStatusType(status: number) {
  const map: Record<
    number,
    'danger' | 'info' | 'primary' | 'success' | 'warning'
  > = {
    0: 'info',
    1: 'success',
    2: 'warning',
  };
  return map[status] || 'info';
}

function getPriorityLabel(priority: MessagePriority) {
  const map: Record<MessagePriority, string> = {
    high: '高',
    low: '低',
    normal: '普通',
    urgent: '紧急',
  };
  return map[priority];
}

function getPriorityType(priority: MessagePriority) {
  const map: Record<
    MessagePriority,
    'danger' | 'info' | 'primary' | 'success' | 'warning'
  > = {
    high: 'warning',
    low: 'info',
    normal: 'success',
    urgent: 'danger',
  };
  return map[priority] || 'info';
}

async function loadAnnouncementList() {
  if (!isSuperAdmin.value) {
    return;
  }
  announcementLoading.value = true;
  try {
    const params: AnnouncementListParams = {
      page: announcementPager.page,
      pageSize: announcementPager.pageSize,
    };
    if (announcementFilter.title.trim()) {
      params.title = announcementFilter.title.trim();
    }
    if (announcementFilter.status !== '') {
      params.status = announcementFilter.status;
    }
    const result = await getAnnouncementListApi(params);
    announcementList.value = result.items || [];
    announcementPager.total = result.total || 0;
  } catch (error) {
    console.error('加载公告列表失败:', error);
  } finally {
    announcementLoading.value = false;
  }
}

function resetAnnouncementForm() {
  announcementEditingId.value = null;
  announcementForm.title = '';
  announcementForm.content = '';
  announcementForm.priority = 'normal';
  announcementForm.expire_at = '';
}

function handleCreateAnnouncement() {
  resetAnnouncementForm();
  announcementDialogVisible.value = true;
}

function handleEditAnnouncement(row: AnnouncementItem) {
  announcementEditingId.value = row.id;
  announcementForm.title = row.title;
  announcementForm.content = row.content;
  announcementForm.priority = row.priority;
  announcementForm.expire_at = row.expire_at || '';
  announcementDialogVisible.value = true;
}

async function handleSubmitAnnouncement() {
  if (!announcementForm.title.trim() || !announcementForm.content.trim()) {
    ElMessage.warning('请填写完整的公告标题和内容');
    return;
  }
  announcementSubmitting.value = true;
  try {
    const payload = {
      content: announcementForm.content.trim(),
      expire_at: announcementForm.expire_at || null,
      priority: announcementForm.priority,
      title: announcementForm.title.trim(),
    };
    if (announcementEditingId.value) {
      await updateAnnouncementApi(announcementEditingId.value, payload);
      ElMessage.success('公告更新成功');
    } else {
      await createAnnouncementApi(payload);
      ElMessage.success('公告创建成功');
    }
    announcementDialogVisible.value = false;
    await loadAnnouncementList();
  } catch (error) {
    console.error('保存公告失败:', error);
  } finally {
    announcementSubmitting.value = false;
  }
}

function handlePublishAnnouncement(row: AnnouncementItem) {
  ElMessageBox.confirm(`确认发布公告「${row.title}」吗？`, '发布公告', {
    type: 'warning',
  })
    .then(async () => {
      const result = await publishAnnouncementApi(row.id);
      ElMessage.success(`${result.msg}${result.count ? `（推送${result.count}人）` : ''}`);
      await loadAnnouncementList();
    })
    .catch(() => {});
}

function handleRevokeAnnouncement(row: AnnouncementItem) {
  ElMessageBox.confirm(`确认撤回公告「${row.title}」吗？`, '撤回公告', {
    type: 'warning',
  })
    .then(async () => {
      await revokeAnnouncementApi(row.id);
      ElMessage.success('公告已撤回');
      await loadAnnouncementList();
    })
    .catch(() => {});
}

function handleDeleteAnnouncement(row: AnnouncementItem) {
  ElMessageBox.confirm(`确认删除公告「${row.title}」吗？`, '删除公告', {
    type: 'warning',
  })
    .then(async () => {
      await deleteAnnouncementApi(row.id);
      ElMessage.success('公告已删除');
      await loadAnnouncementList();
    })
    .catch(() => {});
}

function handleAnnouncementSearch() {
  announcementPager.page = 1;
  loadAnnouncementList();
}

function handleAnnouncementReset() {
  announcementFilter.title = '';
  announcementFilter.status = '';
  announcementPager.page = 1;
  loadAnnouncementList();
}

function handleAnnouncementPageChange(page: number) {
  announcementPager.page = page;
  loadAnnouncementList();
}

function handleAnnouncementPageSizeChange(pageSize: number) {
  announcementPager.pageSize = pageSize;
  announcementPager.page = 1;
  loadAnnouncementList();
}

async function handleSendMessage() {
  if (!sendForm.receiver_ids.length) {
    ElMessage.warning('请选择接收用户');
    return;
  }
  if (!sendForm.title.trim() || !sendForm.content.trim()) {
    ElMessage.warning('请填写完整的消息标题和内容');
    return;
  }
  sendSubmitting.value = true;
  try {
    const result = await sendInternalMessageApi({
      content: sendForm.content.trim(),
      link: sendForm.link.trim() || null,
      priority: sendForm.priority,
      receiver_ids: sendForm.receiver_ids,
      title: sendForm.title.trim(),
    });
    ElMessage.success(
      `${result.msg}${result.count ? `（成功发送${result.count}条）` : ''}`,
    );
    sendForm.title = '';
    sendForm.content = '';
    sendForm.link = '';
    sendForm.priority = 'normal';
    sendForm.receiver_ids = [];
  } catch (error) {
    console.error('发送站内信失败:', error);
  } finally {
    sendSubmitting.value = false;
  }
}

onMounted(async () => {
  await loadAnnouncementList();
});
</script>

<template>
  <Page auto-content-height>
    <ElCard shadow="never">
      <template #header>
        <div class="text-base font-semibold">公告设置与站内通信</div>
      </template>

      <ElAlert
        v-if="!isSuperAdmin"
        description="当前账号不是超级管理员，仅可在消息中心查看通知。"
        show-icon
        title="权限不足"
        type="warning"
      />

      <ElTabs v-else>
        <ElTabPane label="公告管理">
          <div class="mb-4 flex items-center justify-between">
            <ElForm inline @submit.prevent>
              <ElFormItem label="标题">
                <ElInput
                  v-model="announcementFilter.title"
                  clearable
                  placeholder="公告标题"
                  style="width: 220px"
                  @keyup.enter="handleAnnouncementSearch"
                />
              </ElFormItem>
              <ElFormItem label="状态">
                <ElSelect
                  v-model="announcementFilter.status"
                  clearable
                  placeholder="全部"
                  style="width: 140px"
                >
                  <ElOption :value="0" label="草稿" />
                  <ElOption :value="1" label="已发布" />
                  <ElOption :value="2" label="已撤回" />
                </ElSelect>
              </ElFormItem>
              <ElFormItem>
                <ElButton type="primary" @click="handleAnnouncementSearch">
                  查询
                </ElButton>
                <ElButton @click="handleAnnouncementReset">重置</ElButton>
              </ElFormItem>
            </ElForm>
            <ElButton type="primary" @click="handleCreateAnnouncement">
              新建公告
            </ElButton>
          </div>

            <ElTable :data="announcementList" v-loading="announcementLoading" border>
              <ElTableColumn label="公告标题" min-width="260" prop="title" />
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
              <ElTableColumn label="状态" width="110">
                <template #default="scope">
                  <ElTag
                    v-if="scope?.row"
                    :type="getStatusType(scope.row.status)"
                    size="small"
                  >
                    {{ getStatusLabel(scope.row.status) }}
                  </ElTag>
                  <span v-else>-</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="发布时间" min-width="180">
                <template #default="scope">
                  {{ scope?.row ? formatDate(scope.row.publish_at) : '-' }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="失效时间" min-width="180">
                <template #default="scope">
                  {{ scope?.row ? formatDate(scope.row.expire_at) : '-' }}
                </template>
              </ElTableColumn>
              <ElTableColumn fixed="right" label="操作" width="320">
                <template #default="scope">
                  <template v-if="scope?.row">
                    <ElButton
                      link
                      type="primary"
                      @click="handleEditAnnouncement(scope.row)"
                    >
                      编辑
                    </ElButton>
                    <ElButton
                      :disabled="scope.row.status === 1"
                      link
                      type="success"
                      @click="handlePublishAnnouncement(scope.row)"
                    >
                      发布
                    </ElButton>
                    <ElButton
                      :disabled="scope.row.status !== 1"
                      link
                      type="warning"
                      @click="handleRevokeAnnouncement(scope.row)"
                    >
                      撤回
                    </ElButton>
                    <ElButton
                      link
                      type="danger"
                      @click="handleDeleteAnnouncement(scope.row)"
                    >
                      删除
                    </ElButton>
                  </template>
                </template>
              </ElTableColumn>
            </ElTable>

          <div class="mt-4 flex justify-end">
            <ElPagination
              :current-page="announcementPager.page"
              :page-size="announcementPager.pageSize"
              :page-sizes="[10, 20, 50]"
              :total="announcementPager.total"
              background
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="handleAnnouncementPageChange"
              @size-change="handleAnnouncementPageSizeChange"
            />
          </div>
        </ElTabPane>

        <ElTabPane label="站内信发送">
          <div class="send-card">
            <ElForm label-width="100px">
              <ElFormItem label="接收用户">
                <UserSelector
                  v-model="receiverIdsModel"
                  :multiple="true"
                  placeholder="请选择接收用户"
                />
              </ElFormItem>
              <ElFormItem label="消息标题">
                <ElInput v-model="sendForm.title" placeholder="请输入标题" />
              </ElFormItem>
              <ElFormItem label="优先级">
                <ElSelect v-model="sendForm.priority" style="width: 160px">
                  <ElOption label="低" value="low" />
                  <ElOption label="普通" value="normal" />
                  <ElOption label="高" value="high" />
                  <ElOption label="紧急" value="urgent" />
                </ElSelect>
              </ElFormItem>
              <ElFormItem label="跳转链接">
                <ElInput
                  v-model="sendForm.link"
                  placeholder="可选，例如 /message/center"
                />
              </ElFormItem>
              <ElFormItem label="消息内容">
                <ElInput
                  v-model="sendForm.content"
                  :rows="6"
                  placeholder="请输入站内信内容"
                  type="textarea"
                />
              </ElFormItem>
              <ElFormItem>
                <ElButton
                  :loading="sendSubmitting"
                  type="primary"
                  @click="handleSendMessage"
                >
                  发送站内信
                </ElButton>
              </ElFormItem>
            </ElForm>
          </div>
        </ElTabPane>
      </ElTabs>
    </ElCard>

    <ElDialog
      v-model="announcementDialogVisible"
      :title="announcementEditingId ? '编辑公告' : '新建公告'"
      width="620px"
    >
      <ElForm label-width="90px">
        <ElFormItem label="公告标题" required>
          <ElInput v-model="announcementForm.title" maxlength="200" show-word-limit />
        </ElFormItem>
        <ElFormItem label="优先级">
          <ElSelect v-model="announcementForm.priority" style="width: 180px">
            <ElOption label="低" value="low" />
            <ElOption label="普通" value="normal" />
            <ElOption label="高" value="high" />
            <ElOption label="紧急" value="urgent" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="失效时间">
          <ElDatePicker
            v-model="announcementForm.expire_at"
            clearable
            placeholder="不设置则永久有效"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </ElFormItem>
        <ElFormItem label="公告内容" required>
          <ElInput
            v-model="announcementForm.content"
            :rows="8"
            maxlength="4000"
            show-word-limit
            type="textarea"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="announcementDialogVisible = false">取消</ElButton>
        <ElButton
          :loading="announcementSubmitting"
          type="primary"
          @click="handleSubmitAnnouncement"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped>
.send-card {
  max-width: 860px;
}
</style>
