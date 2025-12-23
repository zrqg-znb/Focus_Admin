<script lang="ts" setup>
import { computed } from 'vue';

import { ElCheckbox } from 'element-plus';

import { UserAvatar } from '../user-avatar';

defineOptions({
  name: 'UserCard',
});

const props = withDefaults(defineProps<Props>(), {
  selected: false,
  multiple: false,
});

const emit = defineEmits<{
  select: [userId: string];
}>();

interface Props {
  user: {
    avatar?: string;
    id: string;
    name?: string;
    username: string;
  };
  selected?: boolean;
  multiple?: boolean;
}

const handleClick = () => {
  emit('select', props.user.id);
};

const displayName = computed(() => {
  const name = props.user.name || props.user.username;
  if (name && name.length > 10) {
    return `${name.slice(0, 10)}...`;
  }
  return name;
});
</script>

<template>
  <div class="user-card" :class="{ selected }" @click="handleClick">
    <!-- 选择框（仅多选模式） -->
    <div v-if="multiple" class="user-card-checkbox">
      <ElCheckbox :model-value="selected" @click.stop />
    </div>

    <!-- 内容 -->
    <div class="user-card-content">
      <!-- 头像 -->
      <div class="user-card-avatar">
        <UserAvatar
          :user="user"
          :size="56"
          :font-size="24"
          :shadow="true"
        />
      </div>

      <!-- 用户信息 -->
      <div class="user-card-info">
        <!-- 用户名 -->
        <div class="user-card-username">
          {{ displayName }}
        </div>

        <!-- 名称（小号、次要颜色） -->
        <div class="user-card-realname">
          {{ user.username }}
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.user-card {
  position: relative;
  padding: 16px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  background-color: hsl(var(--background));
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;

  &:hover {
    border-color: hsl(var(--primary));
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  &.selected {
    border: 1px solid hsl(var(--primary));
    background: linear-gradient(
      135deg,
      hsl(var(--primary) / 0.1) 0%,
      hsl(var(--primary) / 0.05) 100%
    );
    box-shadow:
      0 0 0 3px hsl(var(--primary) / 0.15),
      0 2px 12px hsl(var(--primary) / 0.2);

    .user-card-username,
    .user-card-realname {
      color: hsl(var(--primary));
      font-weight: 500;
    }

    .user-card-avatar {
      transform: scale(1.05);
    }
  }

  &-checkbox {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 2;

    :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
      background-color: hsl(var(--primary));
      border-color: hsl(var(--primary));
    }
  }

  &-content {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    transition: transform 0.3s ease;
  }

  &-avatar {
    width: 100%;
    display: flex;
    justify-content: center;
    transition: transform 0.3s ease;
  }

  &-info {
    width: 100%;
    text-align: center;
  }

  &-username {
    font-size: 14px;
    font-weight: 500;
    color: hsl(var(--foreground));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition:
      color 0.3s ease,
      font-weight 0.3s ease;
  }

  &-realname {
    font-size: 12px;
    color: hsl(var(--muted-foreground));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
    transition:
      color 0.3s ease,
      font-weight 0.3s ease;
  }
}
</style>

