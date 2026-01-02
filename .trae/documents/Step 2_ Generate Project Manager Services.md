# Implementation Plan: Project Manager Services

This plan covers the creation of the Service layer for the `project_manager` app, adhering to the strict `common.utils` usage requirements and business logic specified.

## 1. Project Service (`project_service.py`)
- **Dependencies**: `fu_crud`, `transaction`, `fu_user_query`.
- **Logic**:
    - `create_project`: Handle M2M `managers` manually after `fu_crud.create`. Trigger `Milestone` creation if `enable_milestone=True`.
    - `update_project`: Handle M2M updates. Trigger `Milestone` creation if toggled on.
    - `delete_project`: Soft delete via `fu_crud`.

## 2. Milestone Service (`milestone_service.py`)
- **Dependencies**: `fu_crud`.
- **Logic**:
    - `get_milestone_board`: Complex query with `select_related` and filtering logic. Flatten data for `MilestoneBoardSchema`.
    - `update_milestone`: Direct update of QG dates.

## 3. Iteration Service (`iteration_service.py`)
- **Dependencies**: `fu_crud`, `transaction`.
- **Logic**:
    - `create_iteration`: Mutex logic for `is_current`.
    - `get_project_iterations`: Fetch iterations and manually attach the latest `IterationMetric` to populate `IterationDetailSchema`.
    - `record_daily_metric`: Use `update_or_create` for metrics.

## 4. Code Quality Service (`code_quality_service.py`)
- **Dependencies**: `fu_crud`.
- **Logic**:
    - `get_quality_overview`: Aggregate metrics (LOC, duplication, dangerous funcs) from the latest `CodeMetric` of each module under enabled projects.
    - `config_module`: CRUD for modules.
    - `record_module_metric`: `update_or_create` for metrics.

## Execution
I will implement these services sequentially and then perform a final check to ensure all imports are correct and circular dependencies are avoided.