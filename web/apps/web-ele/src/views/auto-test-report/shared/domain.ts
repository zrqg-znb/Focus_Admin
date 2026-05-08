import { computed, ref } from 'vue';

export type AutoTestReportDomain = 'cockpit' | 'vehicle';

export const AUTO_TEST_REPORT_DOMAINS: AutoTestReportDomain[] = [
  'cockpit',
  'vehicle',
];

export const AUTO_TEST_REPORT_VIU_CODES = [
  'viu0',
  'viu1',
  'viu2',
  'viu3',
  'viu4',
] as const;

const DOMAIN_LABEL_MAP: Record<
  AutoTestReportDomain,
  {
    badge: string;
    platformLabel: string;
    platformPanelHint: string;
    platformPanelTitle: string;
    selectorLabel: string;
    selectorPlaceholder: string;
    switchLabel: string;
  }
> = {
  cockpit: {
    badge: '座舱领域',
    platformLabel: 'MCU平台',
    platformPanelTitle: 'MCU平台配置',
    platformPanelHint: '维护座舱场景下的 MCU 平台、车型与测试用例。',
    selectorLabel: 'MCU 平台 / 车型',
    selectorPlaceholder: '选择 MCU 平台 / 车型',
    switchLabel: '座舱视图',
  },
  vehicle: {
    badge: '车控领域',
    platformLabel: 'VIU平台',
    platformPanelTitle: 'VIU平台配置',
    platformPanelHint: '维护车控场景下的 VIU 平台、车型与可用 VIU 编号。',
    selectorLabel: 'VIU 平台 / 车型',
    selectorPlaceholder: '选择 VIU 平台 / 车型',
    switchLabel: '车控视图',
  },
};

export const AUTO_TEST_REPORT_DOMAIN_OPTIONS = AUTO_TEST_REPORT_DOMAINS.map(
  (value) => ({
    label: DOMAIN_LABEL_MAP[value].switchLabel,
    value,
  }),
);

const AUTO_TEST_REPORT_DOMAIN_STORAGE_KEY = 'auto-test-report-domain';

function getStoredDomain(): AutoTestReportDomain {
  if (typeof window === 'undefined') {
    return 'cockpit';
  }
  return normalizeAutoTestReportDomain(
    window.sessionStorage.getItem(AUTO_TEST_REPORT_DOMAIN_STORAGE_KEY),
  );
}

const sharedDomain = ref<AutoTestReportDomain>(getStoredDomain());

export function normalizeAutoTestReportDomain(
  value?: null | string,
): AutoTestReportDomain {
  return value === 'vehicle' ? 'vehicle' : 'cockpit';
}

export function getAutoTestReportDomainMeta(domain: AutoTestReportDomain) {
  return {
    domain,
    ...DOMAIN_LABEL_MAP[domain],
  };
}

export function useAutoTestReportDomain() {
  const domainMeta = computed(() =>
    getAutoTestReportDomainMeta(sharedDomain.value),
  );

  function setDomain(next: AutoTestReportDomain) {
    const normalized = normalizeAutoTestReportDomain(next);
    if (normalized === sharedDomain.value) {
      return;
    }
    sharedDomain.value = normalized;
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(
        AUTO_TEST_REPORT_DOMAIN_STORAGE_KEY,
        normalized,
      );
    }
  }

  return {
    domain: sharedDomain,
    domainMeta,
    setDomain,
  };
}
