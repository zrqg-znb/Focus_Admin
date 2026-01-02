# Implementation Plan: Project Manager App - Step 1: Schemas

This plan focuses on generating the Pydantic Schemas for the `project_manager` app as requested. We will create schema files for each module ensuring they meet the specific business requirements.

## 1. Project Module Schemas
**File:** `apps/project_manager/project/project_schema.py`
- **`ProjectCreateSchema`**: Base fields + feature toggles + `manager_ids`.
- **`ProjectUpdateSchema`**: Similar to create but optional fields.
- **`ProjectFilterSchema`**: Search filters including `keyword` (for name/code), `domain`, `type`, `manager_id`, `is_closed`, and toggles.
- **`ProjectOut`**: ModelSchema for standard output.

## 2. Milestone Module Schemas
**File:** `apps/project_manager/milestone/milestone_schema.py`
- **`MilestoneBoardSchema`**: Flattened structure for the board view (Project Name, Managers, Domain, QG Dates).
- **`MilestoneUpdateSchema`**: Fields for updating QG dates.

## 3. Iteration Module Schemas
**File:** `apps/project_manager/iteration/iteration_schema.py`
- **`IterationCreateSchema`**: Basic info + `is_current`.
- **`IterationMetricSchema`**: For metric data entry (Date, DI values, rates).
- **`IterationDetailSchema`**: Composite schema containing Iteration info + Latest Metric.
- **`IterationOut`**: ModelSchema for standard output.

## 4. Code Quality Module Schemas
**File:** `apps/project_manager/code_quality/code_quality_schema.py`
- **`ModuleConfigSchema`**: For configuring code modules (`name`, `owner_id`).
- **`CodeMetricSchema`**: For recording daily metrics (`loc`, `duplication_rate`, etc.).
- **`ProjectQualitySummarySchema`**: Aggregated data for project overview.

## Execution
I will write these 4 files sequentially. After completion, I will wait for your confirmation before proceeding to Services and APIs.