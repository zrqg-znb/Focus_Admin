<script lang="ts" setup>
import type { PlGroup } from '#/api/core/pl';
import type { CardListOptions } from '#/components/card-list';

import { onMounted, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';

import {
  ElButton,
  ElMessage,
  ElMessageBox,
  ElPopover,
  ElTag,
  ElTooltip,
} from 'element-plus';

import { deletePlApi, getPlListApi } from '#/api/core/pl';
import { CardList } from '#/components/card-list';

import PlFormModal from './pl-form-modal.vue';

const emit = defineEmits<{
  select: [plGroup: PlGroup | undefined];
}>();

const plList = ref<PlGroup[]>([]);
const loading = ref(false);
const selectedPlId = ref<string>();
const searchKeyword = ref('');
const hoveredPlId = ref<string>();

const [PlFormModalComponent, plFormModalApi] = useVbenModal({
  connectedComponent: PlFormModal,
  destroyOnClose: true,
});

const cardListOptions: CardListOptions<PlGroup> = {
  searchFields: [
    { field: 'name' },
    { field: 'code' },
    { field: 'pl_user_name' },
  ],
  titleField: 'name',
};

function emitSelectionById(plId?: string) {
  selectedPlId.value = plId;
  emit(
    'select',
    plList.value.find((item) => item.id === plId),
  );
}

async function fetchPlList(preferredId?: string) {
  try {
    loading.value = true;
    const response = await getPlListApi({ page: 1, pageSize: 1000 });
    plList.value = response.items || [];
    let targetId = preferredId;
    if (targetId && !plList.value.some((item) => item.id === targetId)) {
      targetId = undefined;
    }
    if (!targetId && selectedPlId.value) {
      targetId = plList.value.some((item) => item.id === selectedPlId.value)
        ? selectedPlId.value
        : undefined;
    }
    if (!targetId) {
      targetId = plList.value.at(0)?.id;
    }
    emitSelectionById(targetId);
  } finally {
    loading.value = false;
  }
}

function onPlSelect(plId: string | undefined) {
  emitSelectionById(plId);
}

function onAddPl() {
  plFormModalApi.setData(null).open();
}

function onEditPl(pl: PlGroup, e?: Event) {
  e?.stopPropagation();
  plFormModalApi.setData(pl).open();
}

async function onDeletePl(pl: PlGroup, e?: Event) {
  e?.stopPropagation();

  ElMessageBox.confirm(
    $t('ui.actionMessage.deleteConfirm', [pl.name]),
    $t('common.delete'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
      showClose: false,
    },
  )
    .then(async () => {
      try {
        await deletePlApi(pl.id);
        ElMessage.success($t('ui.actionMessage.deleteSuccess', [pl.name]));
        await fetchPlList(
          selectedPlId.value === pl.id ? undefined : selectedPlId.value,
        );
      } catch {
        ElMessage.error($t('ui.actionMessage.deleteError'));
      }
    })
    .catch(() => {});
}

async function onPlFormSuccess() {
  ElMessage.success($t('ui.actionMessage.createSuccess', [$t('pl.name')]));
  await fetchPlList(selectedPlId.value);
}

async function reload(preferredId?: string) {
  await fetchPlList(preferredId);
}

onMounted(() => {
  fetchPlList();
});

defineExpose({
  reload,
});
</script>

<template>
  <CardList
    :items="plList"
    :loading="loading"
    :selected-id="selectedPlId"
    :hovered-id="hoveredPlId"
    :search-keyword="searchKeyword"
    :options="cardListOptions"
    @select="onPlSelect"
    @update:search-keyword="(v) => (searchKeyword = v)"
    @update:hovered-id="(v) => (hoveredPlId = v)"
    @add="onAddPl"
    @edit="onEditPl"
    @delete="onDeletePl"
  >
    <template #item="{ item }">
      <div class="flex items-center justify-between gap-2">
        <div class="truncate text-sm" :title="item.name">
          {{ item.name }}
        </div>
        <ElTag size="small" :type="item.status ? 'success' : 'info'">
          {{ item.status ? $t('common.enabled') : $t('common.disabled') }}
        </ElTag>
      </div>
    </template>

    <template #details="{ item }">
      <div class="flex items-center gap-2 text-xs opacity-70">
        <span class="truncate" :title="item.code || '-'">
          {{ item.code || '-' }}
        </span>
        <span class="text-gray-400">|</span>
        <span
          class="truncate"
          :title="item.pl_user_name || item.pl_user_username"
        >
          {{ item.pl_user_name || item.pl_user_username }}
        </span>
        <span class="text-gray-400">|</span>
        <span>{{ item.member_count }}</span>
      </div>
    </template>

    <template #actions="{ item }">
      <div class="flex flex-shrink-0" @click.stop>
        <ElTooltip :content="$t('pl.edit')" placement="top">
          <ElButton
            type="primary"
            text
            size="small"
            circle
            @click="onEditPl(item, $event)"
          >
            <IconifyIcon icon="ep:edit" class="size-4" />
          </ElButton>
        </ElTooltip>

        <ElButton
          type="danger"
          text
          size="small"
          circle
          style="margin-left: 0"
          :title="$t('common.delete')"
          @click="onDeletePl(item, $event)"
        >
          <IconifyIcon icon="ep:delete" class="size-4" />
        </ElButton>

        <ElPopover placement="right" :width="300">
          <template #reference>
            <ElButton
              type="info"
              text
              size="small"
              style="margin-left: 0"
              circle
            >
              <IconifyIcon icon="ep:info-filled" class="size-4" />
            </ElButton>
          </template>
          <div class="space-y-2 p-3 text-sm">
            <div class="flex justify-between gap-2">
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.groupName') }}:
              </span>
              <span class="font-medium">{{ item.name || '-' }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.groupCode') }}:
              </span>
              <span class="font-medium">{{ item.code || '-' }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.plUser') }}:
              </span>
              <span class="font-medium">
                {{ item.pl_user_name || item.pl_user_username }}
              </span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.memberCount') }}:
              </span>
              <span class="font-medium">{{ item.member_count }}</span>
            </div>
            <div class="flex justify-between gap-2">
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.status') }}:
              </span>
              <span class="font-medium">
                {{ item.status ? $t('common.enabled') : $t('common.disabled') }}
              </span>
            </div>
            <div
              v-if="item.description"
              class="border-t border-gray-200 pt-2 dark:border-gray-700"
            >
              <span class="text-gray-600 dark:text-gray-400">
                {{ $t('pl.description') }}:
              </span>
              <div
                class="mt-1 max-h-32 overflow-y-auto break-words rounded bg-gray-100 p-2 text-xs dark:bg-gray-800"
              >
                {{ item.description }}
              </div>
            </div>
          </div>
        </ElPopover>
      </div>
    </template>

    <template #modal>
      <PlFormModalComponent @success="onPlFormSuccess" />
    </template>
  </CardList>
</template>
