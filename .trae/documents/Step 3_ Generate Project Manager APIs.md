# Implementation Plan: Project Manager APIs

This plan covers the creation of the API layer for the `project_manager` app, adhering to the specified standards for response format, authentication, and pagination.

## 1. Project API (`project_api.py`)
- **Router**: `Router(tags=["Project"], auth=GlobalAuth())`
- **Endpoints**:
    - `POST /`: Create project using `project_service.create_project`.
    - `PUT /{id}`: Update project using `project_service.update_project`.
    - `DELETE /{id}`: Delete project using `project_service.delete_project`.
    - `GET /`: List projects with filtering (`ProjectFilterSchema`) and pagination (`MyPagination`).

## 2. Milestone API (`milestone_api.py`)
- **Router**: `Router(tags=["Milestone"], auth=GlobalAuth())`
- **Endpoints**:
    - `GET /overview`: Get milestone board data. Accepts filters via `Query` parameters.
    - `PUT /project/{project_id}`: Update milestone using `milestone_service.update_milestone`.

## 3. Iteration API (`iteration_api.py`)
- **Router**: `Router(tags=["Iteration"], auth=GlobalAuth())`
- **Endpoints**:
    - `GET /overview`: Custom logic to fetch projects with enabled iterations and their current iteration details.
    - `GET /project/{project_id}`: Get project iterations using `iteration_service.get_project_iterations`.
    - `POST /`: Create iteration using `iteration_service.create_iteration`.
    - `POST /{iteration_id}/metrics`: Record metric using `iteration_service.record_daily_metric`.

## 4. Code Quality API (`code_quality_api.py`)
- **Router**: `Router(tags=["CodeQuality"], auth=GlobalAuth())`
- **Endpoints**:
    - `GET /overview`: Get quality overview using `code_quality_service.get_quality_overview`.
    - `POST /modules`: Config module using `code_quality_service.config_module`.
    - `GET /project/{project_id}/details`: Custom logic to fetch modules and their metric history (last 30 days).
    - `POST /module/{module_id}/metrics`: Record metric using `code_quality_service.record_module_metric`.

## 5. Main Router (`router.py`)
- Aggregate all sub-routers under `/projects`, `/milestones`, `/iterations`, and `/code_quality`.

## Execution
I will write these 5 files sequentially.