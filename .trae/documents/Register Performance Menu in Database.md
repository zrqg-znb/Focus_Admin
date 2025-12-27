# Manual Menu Registration Guide

I have reverted the backend auto-registration code and deleted the static router file as requested.

Please go to **System -> Menu Management** in your Vben Admin interface and create the following 3 items in order.

## 1. Root Directory (Performance)
Create this first.
- **Type**: Directory (目录)
- **Parent Menu**: Root (根目录)
- **Menu Name**: `Performance` (or 性能监控)
- **Route Path**: `/performance`
- **Component**: `BasicLayout`
- **Icon**: `lucide:bar-chart-3` (or any icon you prefer)
- **Order**: 100

## 2. Dashboard Page
Create this as a child of "Performance".
- **Type**: Menu (菜单)
- **Parent Menu**: Select the "Performance" directory you just created
- **Menu Name**: `PerformanceDashboard` (or 数据看板)
- **Route Path**: `/performance/dashboard`
- **Component**: `/performance/dashboard/index`
  - *Note: This maps to `src/views/performance/dashboard/index.vue`*

## 3. Configuration Page
Create this as a child of "Performance".
- **Type**: Menu (菜单)
- **Parent Menu**: Select the "Performance" directory you just created
- **Menu Name**: `PerformanceConfig` (or 指标配置)
- **Route Path**: `/performance/config`
- **Component**: `/performance/config/index`
  - *Note: This maps to `src/views/performance/config/index.vue`*

After creating these, refresh your page, and the new menus should appear in the sidebar.
