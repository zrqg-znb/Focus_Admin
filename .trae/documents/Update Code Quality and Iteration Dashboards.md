# Update Code Quality & Iteration Dashboards

I will update the Code Quality and Iteration Health dashboards to support new visualization requirements, data synchronization logic, and read-only metric enforcement.

## 1. Backend Implementation (Django)

### Code Quality Module (`apps/project_manager/code_quality/`)
*   **Update Sync Logic (`quality_sync.py`)**:
    *   Ensure `sync_project_quality_metrics` fetches the latest data for all configured modules from the mock platform.
*   **Update APIs (`code_quality_api.py`)**:
    *   **`POST /refresh/{project_id}`**: Trigger immediate synchronization for a project.
    *   **`GET /overview`**: Return a list of projects with their *aggregated* latest quality metrics (for the main dashboard).
    *   **`GET /project/{id}/history`**: Return paginated historical data (List of Modules with their latest metrics). *Note: Per requirement, this view will support merging cells for `oem_name`.*
    *   **Remove/Deprecate**: `POST /module/{id}/metrics` (Manual entry) to enforce read-only policy.

### Iteration Module (`apps/project_manager/iteration/`)
*   **Create Sync Logic (`iteration_sync.py`)**:
    *   Implement `IterationMockPlatform` to simulate fetching iteration lists and metrics.
    *   Implement `sync_project_iterations(project)`:
        *   Fetch remote iterations list.
        *   Compare with local DB (by `code`). Update details if changed.
        *   Identify and set `is_current` iteration.
        *   Fetch and save metrics for the *current* iteration.
*   **Update APIs (`iteration_api.py`)**:
    *   **`POST /refresh/{project_id}`**: Trigger immediate synchronization.
    *   **`GET /overview`**: Return list of projects with their *current* iteration's metrics.
    *   **`GET /project/{id}/history`**: Return list of *all* iterations for the project (paginated).
    *   **Remove/Deprecate**: Manual metric creation endpoints.

## 2. Frontend Implementation (Vue 3)

### Code Quality Views (`views/project-manager/code-quality/`)
*   **Dashboard (`index.vue`)**:
    *   Table displaying all projects with aggregated metrics.
    *   Filters: Domain, Type, Name, Date.
    *   Clicking "Project Name" navigates to the Detail page.
*   **Detail Page (`detail.vue`)**:
    *   Table displaying **Modules** (OEM, Module Name, Owner, Metrics).
    *   **Feature**: Merge `oem_name` cells for modules with the same OEM.
    *   **Action**: "Refresh Data" button to call the backend sync API.

### Iteration Views (`views/project-manager/iteration/`)
*   **Dashboard (`index.vue`)**:
    *   Table displaying projects and their **Current Iteration** status (Progress, Drift, etc.).
    *   Clicking "Project Name" navigates to the Detail page.
*   **Detail Page (`detail.vue`)**:
    *   Table displaying **All Iterations** for the selected project.
    *   **Action**: "Refresh Data" button to call the backend sync API.

### API Clients
*   Update `api/project-manager/code_quality.ts` and `api/project-manager/iteration.ts` with the new endpoints.

## 3. Read-Only Enforcement
*   The UI will not provide forms for entering metric data (LOC, Bug Counts, etc.).
*   All data updates will be driven strictly by the "Refresh" action or initial project creation.
