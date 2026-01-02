# Implementation Plan: Fix ImportError for GlobalAuth

The user reported an `ImportError` in the backend application: `cannot import name 'GlobalAuth' from 'common.fu_auth'`. My research confirmed that the correct class name in `common/fu_auth.py` is `BearerAuth`, not `GlobalAuth`. I need to fix this import error in all API files where `GlobalAuth` was incorrectly used.

## 1. Fix Project API
- **File**: `backend-django/apps/project_manager/project/project_api.py`
- **Action**: Replace `from common.fu_auth import GlobalAuth` with `from common.fu_auth import BearerAuth as GlobalAuth`.
- **Reason**: Using `as GlobalAuth` minimizes code changes in the router instantiation line (`auth=GlobalAuth()`). Alternatively, I can rename it to `BearerAuth` everywhere, but aliasing is cleaner for now given the previous instructions.

## 2. Fix Milestone API
- **File**: `backend-django/apps/project_manager/milestone/milestone_api.py`
- **Action**: Replace `from common.fu_auth import GlobalAuth` with `from common.fu_auth import BearerAuth as GlobalAuth`.

## 3. Fix Iteration API
- **File**: `backend-django/apps/project_manager/iteration/iteration_api.py`
- **Action**: Replace `from common.fu_auth import GlobalAuth` with `from common.fu_auth import BearerAuth as GlobalAuth`.

## 4. Fix Code Quality API
- **File**: `backend-django/apps/project_manager/code_quality/code_quality_api.py`
- **Action**: Replace `from common.fu_auth import GlobalAuth` with `from common.fu_auth import BearerAuth as GlobalAuth`.

## Execution
I will apply these fixes sequentially using `SearchReplace`. I will alias `BearerAuth` as `GlobalAuth` to maintain consistency with the existing router definitions which expect `auth=GlobalAuth()`.