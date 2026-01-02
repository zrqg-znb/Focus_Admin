# Implementation Plan: Self-Review Fixes

Based on the self-review findings, I will implement the following fixes and optimizations:

## 1. Backend Optimization (N+1 Query Fixes)
- **File**: `apps/project_manager/iteration/iteration_api.py`
    - **Issue**: `get_iteration_overview` iterates projects and queries iteration/metrics for each.
    - **Fix**: Use `prefetch_related` or `Subquery` to fetch data in fewer queries. Since `is_current` is a boolean flag, we can filter easily. I will rewrite the logic to fetch projects with their current iteration and its latest metric more efficiently.
- **File**: `apps/project_manager/code_quality/code_quality_api.py`
    - **Issue**: `get_project_quality_details` iterates modules and queries metrics for each.
    - **Fix**: Fetch all relevant metrics for the project in one query, then group by module in Python (which is often faster than N queries) or use `prefetch_related`. Given the requirement for "last 30 days history", fetching all metrics for the project's modules in that range and grouping is efficient.

## 2. Frontend Fixes
- **File**: `web/apps/web-ele/src/views/project-manager/quality/detail.vue`
    - **Issue**: Potential null pointer if `metrics_history` is empty.
    - **Fix**: Add a check `if (metrics.length === 0)` before rendering charts or handle empty data gracefully in `updateCharts`.
- **File**: `web/apps/web-ele/src/router/routes/modules/project-manager.ts`
    - **Issue**: Ensure `currentActiveMenu` is correctly set for hidden detail routes.
    - **Check**: Review shows it is set to `/project-manager/iteration` and `/project-manager/quality` respectively. This looks correct.

## 3. General Polish
- Ensure `GlobalAuth` and `transaction.atomic` are correctly applied (Review confirmed they are present).
- Verify Mock interfaces (Review confirmed logic is sound).

## Execution
I will apply the backend optimizations first, then the frontend safeguards.