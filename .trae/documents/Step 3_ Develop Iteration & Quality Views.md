# Implementation Plan: Iteration & Quality Views

This plan focuses on creating the Overview and Detail views for Iteration and Code Quality management, utilizing `EchartsUI` and `useEcharts` as identified in the codebase.

## 1. Iteration Management (`views/project-manager/iteration/`)
- **Overview (`overview.vue`)**:
    - Layout: `ElRow` + `ElCol` grid layout.
    - Components: Loop through `getIterationOverview` data to render project cards using `ElCard`.
    - Content: Display Project Name, Current Iteration Name, Progress Bar (Req Completion Rate), and DI Value (Drift Rate).
    - Action: Button to navigate to Detail page.
- **Detail (`detail.vue`)**:
    - Layout: `Page` wrapper. Header info section using `ElDescriptions`. Tabs for "Iteration List" and "Trend Analysis".
    - **Tab 1 (List)**: `<Grid>` using `useVbenVxeGrid`. Columns: Name, Code, Dates, Tags (Current, Healthy). Toolbar: "Create Iteration" (Drawer).
    - **Tab 2 (Trend)**: `<EchartsUI>` component. Line chart with dual Y-axes (Completion Rate %, Workload).
    - **Mock Action**: Button to open Dialog -> Input Form -> `recordIterationMetric` API -> Refresh Chart.
- **Modules**:
    - `iteration-drawer.vue`: For creating new iterations.
    - `metric-modal.vue`: For recording mock metrics.

## 2. Code Quality Management (`views/project-manager/quality/`)
- **Overview (`overview.vue`)**:
    - Component: `<Grid>` using `useVbenVxeGrid`.
    - Columns: Project Name, Module Count, Total LOC, Avg Duplication Rate, Dangerous Func Count (Red highlight).
    - Actions: "Details" (Navigate), "Config Modules" (Drawer).
- **Detail (`detail.vue`)**:
    - Layout: Split view. Left: Module List (Menu). Right: Charts.
    - Content:
        - **Chart 1**: Code Scale Trend (Date vs LOC).
        - **Chart 2**: Quality Issues Trend (Date vs Duplication Rate & Dangerous Funcs).
    - **Mock Action**: Button -> Dialog -> `recordModuleMetric` API -> Refresh Charts.
- **Modules**:
    - `module-drawer.vue`: For configuring project modules.
    - `metric-modal.vue`: For recording mock metrics.

## Execution
I will implement the Iteration views first (Overview, Detail, and Modules), followed by the Code Quality views. I will use the established patterns for `useVbenVxeGrid`, `useVbenDrawer`, `useVbenModal`, and `useEcharts`.