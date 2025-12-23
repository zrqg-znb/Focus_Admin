<script lang="ts" setup>
import { computed } from 'vue';
import { ElCheckbox } from 'element-plus';
import { UserAvatar } from '../user-avatar';

defineOptions({
  name: 'UserListItem',
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
    email?: string;
    phone?: string;
  };
  selected?: boolean;
  multiple?: boolean;
}

const handleClick = () => {
  emit('select', props.user.id);
};

const displayName = computed(() => {
  return props.user.name || props.user.username;
});
</script>

<template>
  <div class="user-list-item" :class="{ selected }" @click="handleClick">
    <!-- 选择框（仅多选模式） -->
    <div v-if="multiple" class="user-list-item-checkbox">
      <ElCheckbox :model-value="selected" @click.stop />
    </div>

    <!-- 头像 -->
    <div class="user-list-item-avatar">
      <UserAvatar
        :user="user"
        :size="40"
        :font-size="16"
        :shadow="false"
      />
    </div>

    <!-- 用户信息 -->
    <div class="user-list-item-info">
      <div class="user-list-item-main">
        <span class="user-list-item-name">{{ displayName }}</span>
        <span class="user-list-item-username">@{{ user.username }}</span>
      </div>
      <div v-if="user.email || user.phone" class="user-list-item-contact">
        <span v-if="user.email" class="contact-item">{{ user.email }}</span>
        <span v-if="user.phone" class="contact-item">{{ user.phone }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.user-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  background-color: hsl(var(--background));
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background-color: hsl(var(--accent));
  }

  &.selected {
    background: linear-gradient(
      90deg,
      hsl(var(--primary) / 0.1) 0%,
      hsl(var(--primary) / 0.05) 100%
    );
    border: 1px solid hsl(var(--primary));
    padding-left: 13px;

    .user-list-item-name {
      color: hsl(var(--primary));
      font-weight: 600;
    }
  }

  &-checkbox {
    flex-shrink: 0;

    :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
      background-color: hsl(var(--primary));
      border-color: hsl(var(--primary));
    }
  }

  &-avatar {
    flex-shrink: 0;
  }

  &-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  &-main {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &-name {
    font-size: 14px;
    font-weight: 500;
    color: hsl(var(--foreground));
    transition: all 0.2s ease;
  }

  &-username {
    font-size: 12px;
    color: hsl(var(--muted-foreground));
  }

  &-contact {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: hsl(var(--muted-foreground));

    .contact-item {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}
</style>
