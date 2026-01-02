# Implementation Plan: Fix NameError for Optional

The user reported a `NameError: name 'Optional' is not defined` in `apps/project_manager/iteration/iteration_api.py`.
My research confirmed that `Optional` is used in type hints (e.g., `Optional[IterationOut]`) but is not imported from `typing`.

## 1. Fix Iteration API
- **File**: `backend-django/apps/project_manager/iteration/iteration_api.py`
- **Action**: Change `from typing import List` to `from typing import List, Optional`.

## Execution
I will apply this fix using `SearchReplace`. I will also perform a quick check on other API files to ensure no similar issues exist, although the error log only pointed to this one.

*Self-correction*: I should check `milestone_api.py` as well, as it uses `Optional` in `get_milestone_board` parameters.
Wait, `milestone_api.py` has `from typing import List, Optional`.
`project_api.py` has `from typing import List`. It uses `Optional` in schema file, but in API file... let me check if it uses Optional.
`code_quality_api.py` has `from typing import List, Dict`. Let me check if it uses Optional.

I will start by fixing the reported error in `iteration_api.py`. Then I will quickly verify `code_quality_api.py` just in case.

`code_quality_api.py`: `from typing import List, Dict`. It does NOT use `Optional` in the code I wrote previously (checked memory).
So only `iteration_api.py` needs fixing.