<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import { getIterationOverview, type IterationOverview } from '#/api/project-manager/iteration';
import { ElRow, ElCol, ElCard, ElProgress, ElButton, ElEmpty, ElTag } from 'element-plus';
import { ArrowRight } from '@vben/icons';

defineOptions({ name: 'IterationOverview' });

const router = useRouter();
const loading = ref(false);
const overviewList = ref<IterationOverview[]>([]);

async function fetchData() {
  loading.value = true;
  try {
    overviewList.value = await getIterationOverview();
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function goToDetail(projectId: string) {
  router.push(`/project-manager/iteration/detail/${projectId}`);
}

onMounted(() => {
  fetchData();
});
</script>

<template>
  <Page auto-content-height>
    <div v-loading="loading" class="h-full">
      <ElEmpty v-if="!loading && overviewList.length === 0" description="暂无开启迭代管理的项目" />

      <ElRow :gutter="16" v-else>
        <ElCol
          v-for="item in overviewList"
          :key="item.project_id"
          :xs="24" :sm="12" :md="8" :lg="6"
          class="mb-4"
        >
          <ElCard shadow="hover" class="h-full flex flex-col">
            <template #header>
              <div class="flex justify-between items-center">
                <span class="font-bold truncate" :title="item.project_name">{{ item.project_name }}</span>
                <ElButton text type="primary" @click="goToDetail(item.project_id)">
                  详情 <ArrowRight class="ml-1 size-4" />
                </ElButton>
              </div>
            </template>

            <div class="flex-1">
              <div class="mb-4">
                <div class="text-gray-500 text-sm mb-1">当前迭代</div>
                <div class="flex items-center">
                  <span v-if="item.current_iteration" class="font-medium mr-2">
                    {{ item.current_iteration.name }}
                  </span>
                  <span v-else class="text-gray-400">未配置</span>
                  <ElTag v-if="item.current_iteration?.is_healthy" type="success" size="small" effect="plain">健康</ElTag>
                  <ElTag v-else-if="item.current_iteration" type="danger" size="small" effect="plain">风险</ElTag>
                </div>
              </div>

              <div class="mb-4">
                <div class="text-gray-500 text-sm mb-1">需求完成率</div>
                <ElProgress
                  :percentage="item.latest_metric?.req_completion_rate || 0"
                  :status="!item.current_iteration ? 'warning' : (item.latest_metric?.req_completion_rate === 100 ? 'success' : '')"
                />
              </div>

              <div class="flex justify-between items-center text-sm">
                <div>
                  <div class="text-gray-500 mb-1">需求游离率</div>
                  <div class="font-medium">{{ item.latest_metric?.req_drift_rate || 0 }}%</div>
                </div>
                <div>
                  <div class="text-gray-500 mb-1">剩余工作量</div>
                  <div class="font-medium">
                    {{ (item.latest_metric?.req_workload || 0) - (item.latest_metric?.completed_workload || 0) }}
                  </div>
                </div>
              </div>
            </div>
          </ElCard>
        </ElCol>
      </ElRow>
    </div>
  </Page>
</template>
