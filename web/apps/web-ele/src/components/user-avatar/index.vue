<script lang="ts" setup>
import type { User } from '#/api/core/user';

import { computed, ref } from 'vue';

import { ElAvatar, ElPopover, ElSkeleton } from 'element-plus';

import { getFileStreamUrl } from '#/api/core/file';
import { getUserDetailApi } from '#/api/core/user';
import { generateAvatarGradient, generateAvatarText } from '#/utils/avatar';

defineOptions({
  name: 'UserAvatar',
});

const props = withDefaults(defineProps<Props>(), {
  size: 56,
  fontSize: 24,
  shadow: true,
  showPopover: true,
});

interface Props {
  /**
   * 用户对象（包含 id, name, avatar 等信息）
   */
  user?: User;
  /**
   * 用户ID（用于获取详细信息和用户对象）
   */
  userId?: string;
  /**
   * 用户名字或用户名（可选，如果不提供则从 user 或 userId 中获取）
   */
  name?: string;
  /**
   * 头像文件路径（不需要调用 getFileStreamUrl，组件内部处理）
   * @deprecated 建议使用 user 或 userId 代替
   */
  avatar?: string;
  /**
   * 头像尺寸（像素）
   * @default 56
   */
  size?: number;
  /**
   * 文字大小（像素）
   * @default 24
   */
  fontSize?: number;
  /**
   * 是否显示阴影
   * @default true
   */
  shadow?: boolean;
  /**
   * 是否启用悬停显示详细信息
   * @default true
   */
  showPopover?: boolean;
}

// 获取有效的 ID
const effectiveUserId = computed(() => {
  return props.userId || props.user?.id;
});

// 获取有效的用户名
const effectiveUserName = computed(() => {
  return props.name || props.user?.name;
});

// 获取有效的头像 URL（处理 getFileStreamUrl）
const effectiveAvatarUrl = computed(() => {
  const avatarPath = props.avatar || props.user?.avatar;
  if (avatarPath) {
    return getFileStreamUrl(avatarPath);
  }
  return undefined;
});

const userInitials = computed(() => {
  return generateAvatarText(effectiveUserName.value);
});

const avatarGradient = computed(() => {
  return generateAvatarGradient(effectiveUserName.value);
});

// Popover 相关
const popoverVisible = ref(false);
const userDetail = ref<User>();
const loading = ref(false);
const hasLoaded = ref(false);

// 加载用户详细信息
async function loadUserDetail() {
  if (!props.showPopover) return;
  if (hasLoaded.value) return; // 已加载过，不再重复加载

  // 如果已有用户对象，直接使用；否则通过 ID 加载
  if (props.user) {
    userDetail.value = props.user;
    hasLoaded.value = true;
    return;
  }

  if (!effectiveUserId.value) return;

  loading.value = true;
  try {
    userDetail.value = await getUserDetailApi(effectiveUserId.value);
    hasLoaded.value = true;
  } catch (error) {
    console.error('Failed to load user detail:', error);
  } finally {
    loading.value = false;
  }
}

// Popover 显示时加载数据
function handlePopoverShow() {
  if (!hasLoaded.value) {
    loadUserDetail();
  }
}

// 获取性别显示文本
function getGenderText(gender?: number) {
  if (gender === 1) return '男';
  if (gender === 0) return '女';
  return '未知';
}

// 获取状态标签类型
function getStatusType(isActive?: number) {
  return isActive === 1 ? 'success' : 'danger';
}

// 获取状态显示文本
function getStatusText(isActive?: number) {
  return isActive === 1 ? '启用' : '禁用';
}
</script>

<template>
  <ElPopover
    v-if="showPopover && effectiveUserId"
    v-model:visible="popoverVisible"
    placement="right"
    :width="280"
    trigger="hover"
    :show-after="300"
    @show="handlePopoverShow"
  >
    <template #reference>
      <div class="avatar-generator cursor-pointer">
        <div
          v-if="!effectiveAvatarUrl"
          class="avatar-gradient"
          :style="{
            width: `${size}px`,
            height: `${size}px`,
            background: avatarGradient,
            boxShadow: shadow ? '0 2px 8px rgba(0, 0, 0, 0.15)' : 'none',
            fontSize: `${fontSize}px`,
          }"
        >
          <span class="avatar-text">{{ userInitials }}</span>
        </div>
        <ElAvatar
          v-else
          :src="effectiveAvatarUrl"
          :alt="effectiveUserName"
          :size="size"
          :style="{
            boxShadow: shadow ? '0 2px 8px rgba(0, 0, 0, 0.15)' : 'none',
          }"
        />
      </div>
    </template>

    <!-- Popover 内容 -->
    <div class="user-detail-popover">
      <!-- 加载骨架屏 -->
      <ElSkeleton v-if="loading || !userDetail" :rows="5" animated />

      <!-- 用户详细信息 -->
      <div v-if="userDetail && !loading" class="user-detail-content">
        <!-- 头像和基本信息 -->
        <div class="user-header">
          <div class="user-avatar-large">
            <div
              v-if="!userDetail.avatar"
              class="avatar-gradient"
              :style="{
                width: '64px',
                height: '64px',
                background: generateAvatarGradient(userDetail.name),
                fontSize: '24px',
              }"
            >
              <span class="avatar-text">{{
                generateAvatarText(userDetail.name)
              }}</span>
            </div>
            <ElAvatar
              v-else
              :src="getFileStreamUrl(userDetail.avatar || '')"
              :alt="userDetail.name"
              :size="64"
            />
          </div>
          <div class="user-basic-info">
            <div class="user-name">{{ userDetail.name }}</div>
            <div class="user-username">@{{ userDetail.username }}</div>
          </div>
        </div>

        <!-- 详细信息 -->
        <div class="user-details">
          <div v-if="userDetail.email" class="detail-item">
            <span class="detail-label">邮箱：</span>
            <span class="detail-value">{{ userDetail.email }}</span>
          </div>
          <div v-if="userDetail.mobile" class="detail-item">
            <span class="detail-label">手机：</span>
            <span class="detail-value">{{ userDetail.mobile }}</span>
          </div>
          <div v-if="userDetail.city" class="detail-item">
            <span class="detail-label">城市：</span>
            <span class="detail-value">{{ userDetail.city }}</span>
          </div>
          <div v-if="userDetail.dept_name" class="detail-item">
            <span class="detail-label">部门：</span>
            <span class="detail-value">{{ userDetail.dept_name }}</span>
          </div>
          <div
            v-if="userDetail.post_names && userDetail.post_names.length > 0"
            class="detail-item"
          >
            <span class="detail-label">岗位：</span>
            <span class="detail-value">{{
              userDetail.post_names.join(', ')
            }}</span>
          </div>
          <div v-if="userDetail.manager_name" class="detail-item">
            <span class="detail-label">主管：</span>
            <span class="detail-value">{{ userDetail.manager_name }}</span>
          </div>
          <!-- <div class="detail-item">
            <span class="detail-label">性别：</span>
            <span class="detail-value">{{ getGenderText(userDetail.gender) }}</span>
          </div> -->
          <div v-if="userDetail.user_type_display" class="detail-item">
            <span class="detail-label">类型：</span>
            <span class="detail-value">{{ userDetail.user_type_display }}</span>
          </div>
          <!-- <div class="detail-item">
            <span class="detail-label">状态：</span>
            <ElTag :type="getStatusType(userDetail.is_active)" size="small">
              {{ getStatusText(userDetail.is_active) }}
            </ElTag>
          </div> -->
        </div>
      </div>
    </div>
  </ElPopover>

  <!-- 无 Popover 时 -->
  <div v-else class="avatar-generator">
    <div
      v-if="!effectiveAvatarUrl"
      class="avatar-gradient"
      :style="{
        width: `${size}px`,
        height: `${size}px`,
        background: avatarGradient,
        boxShadow: shadow ? '0 2px 8px rgba(0, 0, 0, 0.15)' : 'none',
        fontSize: `${fontSize}px`,
      }"
    >
      <span class="avatar-text">{{ userInitials }}</span>
    </div>
    <ElAvatar
      v-else
      :src="effectiveAvatarUrl"
      :alt="effectiveUserName"
      :size="size"
      :style="{
        boxShadow: shadow ? '0 2px 8px rgba(0, 0, 0, 0.15)' : 'none',
      }"
    />
  </div>
</template>

<style lang="scss" scoped>
.avatar-generator {
  display: inline-flex;
  align-items: center;
  justify-content: center;

  .avatar-gradient {
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    .avatar-text {
      font-weight: 700;
      color: white;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
      white-space: nowrap;
    }
  }

  :deep(.el-avatar) {
    flex-shrink: 0;
  }
}

.user-detail-popover {
  padding: 4px;

  .user-detail-content {
    .user-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-bottom: 16px;
      border-bottom: 1px solid hsl(var(--border));

      .user-avatar-large {
        flex-shrink: 0;

        .avatar-gradient {
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);

          .avatar-text {
            font-weight: 700;
            color: white;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
          }
        }
      }

      .user-basic-info {
        flex: 1;
        min-width: 0;

        .user-name {
          font-size: 16px;
          font-weight: 600;
          color: hsl(var(--foreground));
          margin-bottom: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .user-username {
          font-size: 13px;
          color: hsl(var(--muted-foreground));
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .user-details {
      padding-top: 12px;

      .detail-item {
        display: flex;
        align-items: center;
        padding: 6px 0;
        font-size: 13px;

        .detail-label {
          color: hsl(var(--muted-foreground));
          width: 60px;
          flex-shrink: 0;
        }

        .detail-value {
          color: hsl(var(--foreground));
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
  }
}
</style>
