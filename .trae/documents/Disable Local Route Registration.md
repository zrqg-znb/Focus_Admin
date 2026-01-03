# Implementation Plan: Hide Static Routes for Project Manager

The user is experiencing an issue where the `project-manager` menu appears automatically, even though they expect it to be registered manually via the backend admin panel.
My research confirms that `src/router/routes/modules/project-manager.ts` is being automatically picked up by `import.meta.glob` in `src/router/routes/index.ts` as a **dynamic route**.

In Vben Admin (and similar admin templates), routes in `router/routes/modules/*.ts` are typically treated as "local static routes" that are loaded **in addition** to backend routes, or they are used as a fallback/development feature.
Since the user wants **purely backend-driven routing** for this module, we should **remove or comment out** this local route definition file so that it doesn't get auto-registered. The frontend components exist, and the backend will serve the menu structure pointing to these component paths.

However, completely deleting it might make development harder (no easy way to test without backend config). A better approach is to simply **comment out the default export** or delete the file if the user is strictly following backend-driven RBAC. Given the user's explicit question "why did it appear directly", the answer is "because it's defined in the local modules directory".

To fix this and strictly follow "backend registration only":
1.  **Explanation**: Explain that Vben auto-loads files in `src/router/routes/modules/` as local routes.
2.  **Action**: Rename or modify `src/router/routes/modules/project-manager.ts` to stop it from being auto-loaded. Usually, renaming it to `project-manager.ts.bak` or just commenting out the code is enough. But a cleaner way for a "backend-driven" system is to remove this file from the auto-load path, or ensure the backend *replaces* it.
    *   Actually, if the backend returns the *same* route path, it might merge or duplicate.
    *   The user wants to register it *manually*. So this local file **should not exist** as an active route module.
    *   I will rename `src/router/routes/modules/project-manager.ts` to `src/router/routes/modules/project-manager.ts.bak` (or just delete it, but renaming is safer for reference).
    *   Wait, if I rename/delete it, Vben won't know the **Component Mapping** if it uses `component: 'Layout'` string from backend.
    *   **Crucial Detail**: In backend-driven routing, the frontend usually needs a map of "Component String -> Actual Component". Vben 5 might handle this dynamically, or it might rely on these local route definitions to map components.
    *   **Correction**: In Vben, backend routing usually sends a `component` string like `/project-manager/project/index`. The frontend needs a way to resolve this string to `() => import(...)`.
    *   If `project-manager.ts` is removed, does Vben still find the components?
        *   Standard Vben behavior: It often uses `VIEW_COMPONENTS` map or auto-resolves `src/views/**/*.vue`.
        *   If the backend sends `component: '/project-manager/project/index'`, Vben's permission guard typically resolves this against `import.meta.glob('../views/**/*.vue')`.
        *   So, the **Route Configuration File** (`project-manager.ts`) itself is what creates the menu item locally. The **Components** (`src/views/...`) are what's needed for the backend route to work.
        *   **Conclusion**: The route definition file `project-manager.ts` is indeed creating the "hardcoded" menu. It is safe to remove/disable it if the backend is providing the menu structure.

## Plan
1.  **Rename** `web/apps/web-ele/src/router/routes/modules/project-manager.ts` to `_project-manager.ts` (or similar) to prevent auto-loading, OR simply explain that this file is the cause and should be deleted/ignored in production if backend routing is used.
    *   I will chose to **comment out the export** or rename the file to `.bak` so it stops taking effect immediately, verifying the user's expectation.

## Execution
I will rename the file to `project-manager.ts.bak`. This effectively "deletes" it from the auto-loader while preserving the code for the user's reference (e.g., for copying paths to the backend).