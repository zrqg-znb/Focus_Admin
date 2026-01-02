# Implementation Plan: Create Project Manager App

## 1. Directory Structure Setup
Create the following directory structure for the new `project_manager` app, following the `core` app's pattern:
```
backend-django/apps/project_manager/
├── __init__.py
├── apps.py                  # App configuration
├── router.py                # Main router for the app
├── models/
│   └── __init__.py          # Export all models
├── project/
│   ├── __init__.py
│   ├── project_model.py     # Project model
│   ├── project_schema.py    # Project schemas
│   └── project_api.py       # Project API endpoints
├── milestone/
│   ├── __init__.py
│   ├── milestone_model.py   # Milestone model
│   ├── milestone_schema.py  # Milestone schemas
│   └── milestone_api.py     # Milestone API endpoints
├── iteration/
│   ├── __init__.py
│   ├── iteration_model.py   # Iteration & IterationMetric models
│   ├── iteration_schema.py  # Iteration schemas
│   └── iteration_api.py     # Iteration API endpoints
└── code_quality/
    ├── __init__.py
    ├── code_quality_model.py # CodeModule & CodeMetric models
    ├── code_quality_schema.py # CodeQuality schemas
    └── code_quality_api.py   # CodeQuality API endpoints
```

## 2. Model Implementation
Implement models in their respective files, all inheriting from `common.fu_model.RootModel`.
*   **`project_model.py`**: `Project` (with `managers` M2M to `core.User`, `sys_creator`/`sys_modifier` inherited).
*   **`milestone_model.py`**: `Milestone` (OneToOne to `Project`).
*   **`iteration_model.py`**: `Iteration` (FK to `Project`), `IterationMetric` (FK to `Iteration`).
*   **`code_quality_model.py`**: `CodeModule` (FK to `Project`, Owner FK to `core.User`), `CodeMetric` (FK to `CodeModule`).

*Note: Ensure all models are imported in `apps/project_manager/models/__init__.py`.*

## 3. Schema & API Implementation
*   Create basic CRUD schemas (Schema, In, Out) in `*_schema.py` files.
*   Create `Router` instances in `*_api.py` files and implement basic CRUD endpoints.

## 4. Router Configuration
*   In `apps/project_manager/router.py`, create a main router and register sub-routers (`project`, `milestone`, `iteration`, `code_quality`).
*   In `apps/router.py`, register the `project_manager` router under the path `/project_manager`.

## 5. App Registration
*   Add `'apps.project_manager'` to `INSTALLED_APPS` in `backend-django/application/settings.py`.
