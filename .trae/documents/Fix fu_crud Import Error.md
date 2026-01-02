# Implementation Plan: Fix `fu_crud` Import Error

The backend is failing with `ImportError: cannot import name 'fu_crud' from 'common.utils'`.
This is because `common.utils` does not expose `fu_crud`. `fu_crud.py` is located directly under `common/`, not `common/utils/`.

The correct import path should be `common.fu_crud`, not `common.utils.fu_crud` (assuming `fu_crud` is a module), or `from common.fu_crud import ...` if we want specific functions.
Looking at the file structure:
- `backend-django/common/fu_crud.py` exists.
- `backend-django/common/utils/` exists but `fu_crud.py` is NOT in there.

Therefore, the import statement `from common.utils import fu_crud` in the service files is incorrect. It should be `import common.fu_crud as fu_crud` or `from common import fu_crud`.

## 1. Fix Project Service
- **File**: `apps/project_manager/project/project_service.py`
- **Action**: Change `from common.utils import fu_crud` to `from common import fu_crud`.

## 2. Fix Milestone Service
- **File**: `apps/project_manager/milestone/milestone_service.py`
- **Action**: Change `from common.utils import fu_crud` to `from common import fu_crud`.

## 3. Fix Iteration Service
- **File**: `apps/project_manager/iteration/iteration_service.py`
- **Action**: Change `from common.utils import fu_crud` to `from common import fu_crud`.

## 4. Fix Code Quality Service
- **File**: `apps/project_manager/code_quality/code_quality_service.py`
- **Action**: Change `from common.utils import fu_crud` to `from common import fu_crud`.

## Execution
I will apply these fixes sequentially using `SearchReplace`.