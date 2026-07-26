import type { CmcPersonRecord } from '#/api/cmc-contribution';
import type { ZqTableGridOptions } from '#/components/zq-table';

function formatPercent(value: null | number | undefined) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`;
}

function formatDensity(value: null | number | undefined) {
  return value === null || value === undefined ? '--' : value.toFixed(4);
}

/**
 * CMC 人员明细列定义；数值列均由后端排序，避免仅对当前页排序。
 */
export function useCmcPersonColumns(): ZqTableGridOptions<CmcPersonRecord>['columns'] {
  return [
    {
      field: 'user',
      minWidth: 140,
      slots: { header: 'header-user' },
      title: '人员',
    },
    {
      align: 'center',
      field: 'cnt_total',
      sortable: 'custom',
      title: '合入MR',
    },
    {
      align: 'center',
      field: 'zero_comment_mr_count',
      sortable: 'custom',
      title: '零检视MR',
    },
    {
      align: 'center',
      field: 'zero_comment_rate',
      formatter: (_row, _column, cellValue) => formatPercent(cellValue),
      sortable: 'custom',
      title: '零检视占比',
    },
    {
      align: 'center',
      field: 'effective_comment_count',
      sortable: 'custom',
      title: '有效检视意见',
    },
    {
      align: 'center',
      field: 'effective_comment_density',
      formatter: (_row, _column, cellValue) => formatDensity(cellValue),
      sortable: 'custom',
      title: '意见密度',
    },
    {
      align: 'center',
      field: 'major_comments_cnt',
      sortable: 'custom',
      title: '严重',
    },
    {
      align: 'center',
      field: 'fatal_comments_cnt',
      sortable: 'custom',
      title: '致命',
    },
    {
      align: 'center',
      field: 'minor_comments_cnt',
      sortable: 'custom',
      title: '一般',
    },
    {
      align: 'center',
      field: 'sugge_comments_cnt',
      sortable: 'custom',
      title: '建议',
    },
    { align: 'center', field: 'cmt_issue', sortable: 'custom', title: 'Issue' },
    {
      align: 'center',
      field: 'checked_mr_lines',
      sortable: 'custom',
      title: '检视代码行',
    },
    {
      align: 'center',
      field: 'cmt_lines',
      sortable: 'custom',
      title: '提交MR代码量',
    },
  ];
}
