# DTS Statistics

## Page Route (Register In Backend Menu)

- route path: `/project-manager/dts-statistics`
- component key: `/project-manager/dts-statistics/index`

Notes:
- This is a single page with Tabs (List + Dashboard). You only need **one** menu page.

## Backend APIs

- `POST /api/project-manager/dts-statistics/list`
- `POST /api/project-manager/dts-statistics/summary`
- `POST /api/project-manager/dts-statistics/low-level-issues`
- `POST /api/project-manager/dts-statistics/save-extension/{defect_no}`

## Behavior Notes

- Multi-project query is grouped by `Project.version_c` (each group calls upstream once).
- Upstream paging results and scan results are cached in Redis via Django cache (`common/fu_cache.py::CacheManager`).
- Only upstream base fields are cached; extension fields are merged from DB in realtime.
