<script lang="ts" setup>
import type { AutoTestReportDomain } from '../shared/domain';

import { computed } from 'vue';

import { ElSegmented } from 'element-plus';

import {
  AUTO_TEST_REPORT_DOMAIN_OPTIONS,
  useAutoTestReportDomain,
} from '../shared/domain';

const { domain, domainMeta, setDomain } = useAutoTestReportDomain();

const segmentedValue = computed<AutoTestReportDomain>({
  get: () => domain.value,
  set: (value) => setDomain(value),
});
</script>

<template>
  <div class="flex items-center gap-3">
    <div class="text-sm font-medium text-gray-500">
      {{ domainMeta.badge }}
    </div>
    <ElSegmented
      v-model="segmentedValue"
      :options="AUTO_TEST_REPORT_DOMAIN_OPTIONS"
      size="large"
    />
  </div>
</template>
