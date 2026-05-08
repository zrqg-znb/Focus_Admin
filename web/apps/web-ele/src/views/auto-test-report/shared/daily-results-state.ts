import type { AutoTestReportDomain } from './domain';

export type AutoTestReportDailyResultsView = 'overview' | 'vehicle';

export interface AutoTestReportDailyResultsState {
  activeView: AutoTestReportDailyResultsView;
  vehicleId: string;
}

const DAILY_RESULTS_STATE_STORAGE_PREFIX = 'auto-test-report:daily-results';

const DEFAULT_DAILY_RESULTS_STATE: AutoTestReportDailyResultsState = {
  activeView: 'overview',
  vehicleId: '',
};

function getStorageKey(domain: AutoTestReportDomain) {
  return `${DAILY_RESULTS_STATE_STORAGE_PREFIX}:${domain}`;
}

function readStoredState(domain: AutoTestReportDomain) {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_DAILY_RESULTS_STATE };
  }

  const rawState = window.sessionStorage.getItem(getStorageKey(domain));
  if (!rawState) {
    return { ...DEFAULT_DAILY_RESULTS_STATE };
  }

  try {
    const parsed = JSON.parse(
      rawState,
    ) as Partial<AutoTestReportDailyResultsState>;
    return {
      activeView: parsed.activeView === 'vehicle' ? 'vehicle' : 'overview',
      vehicleId: typeof parsed.vehicleId === 'string' ? parsed.vehicleId : '',
    };
  } catch {
    return { ...DEFAULT_DAILY_RESULTS_STATE };
  }
}

function writeStoredState(
  domain: AutoTestReportDomain,
  state: Partial<AutoTestReportDailyResultsState>,
) {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_DAILY_RESULTS_STATE, ...state };
  }

  const currentState = readStoredState(domain);
  const nextState = {
    ...currentState,
    ...state,
    activeView:
      state.activeView === 'vehicle' || state.activeView === 'overview'
        ? state.activeView
        : currentState.activeView,
    vehicleId:
      typeof state.vehicleId === 'string'
        ? state.vehicleId
        : currentState.vehicleId,
  };
  window.sessionStorage.setItem(
    getStorageKey(domain),
    JSON.stringify(nextState),
  );
  return nextState;
}

export function getAutoTestReportDailyResultsState(
  domain: AutoTestReportDomain,
) {
  return readStoredState(domain);
}

export function setAutoTestReportDailyResultsState(
  domain: AutoTestReportDomain,
  state: Partial<AutoTestReportDailyResultsState>,
) {
  return writeStoredState(domain, state);
}

export function setAutoTestReportDailyResultsView(
  domain: AutoTestReportDomain,
  activeView: AutoTestReportDailyResultsView,
) {
  return writeStoredState(domain, { activeView });
}

export function setAutoTestReportDailyResultsVehicleId(
  domain: AutoTestReportDomain,
  vehicleId: string,
) {
  return writeStoredState(domain, { vehicleId });
}
