# Implementation Plan: Project Manager Frontend Views

This plan focuses on creating the View layer for the `project_manager` app, specifically the Project List and Milestone Board pages.

## 1. Project List (`views/project-manager/project/index.vue`)
- **Structure**: Use `<Page>` wrapper with `<Grid>` (via `useVbenVxeGrid`).
- **Data Configuration (`views/project-manager/project/data.ts`)**:
    - `useColumns`: Define columns for name, code, domain, type, managers (custom slot/formatter), and toggle flags (tags).
    - `useSearchFormSchema`: Define search fields (keyword, domain, type, is_closed).
- **Component**:
    - Implement `index.vue` handling Grid events and Toolbar actions (Create).
    - Implement `modules/project-drawer.vue` using `useVbenDrawer` + `useVbenForm`.
        - Form Schema: Basic info inputs + 3 Switches for toggles.
- **Actions**:
    - Create: Open Drawer.
    - Edit: Open Drawer with row data.
    - Delete: Call `deleteProject` API with confirmation.

## 2. Milestone Board (`views/project-manager/milestone/index.vue`)
- **Structure**: Use `<Page>` wrapper with `<Grid>`.
- **Data Configuration (`views/project-manager/milestone/data.ts`)**:
    - `useColumns`: Project Name (fixed), Managers, QG1-QG8 Dates.
    - `useSearchFormSchema`: Keyword, Project Type.
- **Component**:
    - Implement `index.vue`.
    - Implement `modules/milestone-dialog.vue` using `useVbenModal` (or Dialog) + `useVbenForm`.
        - Form Schema: 8 DatePickers for QG nodes.
- **Actions**:
    - Edit: Open Dialog to modify dates.

## Execution
I will implement the `data.ts` and `index.vue` (plus modules) for Project first, then for Milestone.

**Note on Components**: The user mentioned `ZqTable`, `ZqForm` etc., but my research showed they don't exist in the provided codebase paths. I will strictly follow the pattern found in `_core/user/index.vue` which uses `useVbenVxeGrid` and `useVbenDrawer`/`useVbenForm`, as this is the actual pattern in the project. I will ignore the `Zq*` component instruction to ensure the code works with the existing infrastructure.