# Implementation Plan: Project Manager Frontend

This plan focuses on creating the frontend structure for the `project_manager` app, covering API definitions and Routing configuration as the first step.

## 1. API Definitions (`src/api/project-manager/*.ts`)
We will create a structured API layer mirroring the backend endpoints.
- **`project.ts`**: CRUD for projects (list, create, update, delete).
- **`milestone.ts`**: Milestone board overview and updates.
- **`iteration.ts`**: Iteration overview, project iterations, create, and metric recording.
- **`quality.ts`**: Quality overview, module config, and metric recording.

**Key considerations:**
- Use `defHttp` from `@/utils/http/axios` (or equivalent based on Vben 5).
- Define strict TypeScript interfaces matching backend Snake Case fields (e.g., `enable_milestone`).

## 2. Route Configuration (`src/router/routes/modules/project-manager.ts`)
We will configure the routing for the new module.
- **Path**: `/project-manager`
- **Layout**: `BasicLayout`
- **Children**:
    - `project`: Project Management (Table)
    - `milestone`: Milestone Board
    - `iteration`: Iteration Overview
    - `iteration-detail`: Iteration Detail (Hidden in menu)
    - `quality`: Code Quality Overview
    - `quality-detail`: Quality Detail (Hidden in menu)

**Key considerations:**
- Use `LAYOUT` constant for the component wrapper.
- Configure `meta` fields properly (`title`, `icon`, `order`, etc.).
- Ensure hidden routes (`detail`) have `currentActiveMenu` pointing to their parent list to maintain menu highlight.

## Execution
I will generate the API files first, followed by the route configuration file. After this is confirmed and completed, we can proceed to View development in the next turn.