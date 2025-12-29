I will fix the API routing issues by reordering the route definitions. In Django Ninja (and similar frameworks), routes are matched in order. Dynamic routes like `/indicators/{id}` or `/user/{user_id}` can "shadow" specific routes like `/indicators/import` or `/user/search` if they are defined first, causing 405 Method Not Allowed or 404 Not Found errors.

### Plan:

1.  **Fix Performance Import API (Issue 1)**
    *   Modify `backend-django/apps/performance/api.py`.
    *   Move the `import_indicators` (`POST /indicators/import`) endpoint to the top of the file, specifically before any `/indicators/{id}` routes (DELETE, PUT).

2.  **Fix User Search API (Issue 2)**
    *   Modify `backend-django/core/user/user_api.py`.
    *   Reorganize the file to ensure all specific static routes (e.g., `/user/search`, `/user/all`, `/user/profile/me`, `/user/batch/...`) are defined **before** the generic dynamic routes (`/user/{user_id}`).
    *   This will prevent `{user_id}` from capturing requests meant for `search` or `all`.

### Implementation Steps:
1.  **Edit `backend-django/apps/performance/api.py`**:
    *   Move `@router.post("/indicators/import")` block to appear before `@router.delete("/indicators/{id}")`.

2.  **Edit `backend-django/core/user/user_api.py`**:
    *   Identify all routes with specific paths (containing static segments after `/user/`).
    *   Move them above the CRUD operations for single users (`DELETE /user/{user_id}`, `PUT /user/{user_id}`, `PATCH /user/{user_id}`, `GET /user/{user_id}`).
    *   Keep `POST /user` and `GET /user` at the top as they don't conflict.

This reordering ensures that the router checks for specific matches (like "import" or "search") before falling back to the generic ID matching.