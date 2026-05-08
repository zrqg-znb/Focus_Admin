#!/usr/bin/env python3
import argparse
import json
import random
from datetime import datetime, timedelta

import requests


DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
DEFAULT_API_PATH = '/api/auto-test-report/report/daily-results'
RESULT_CHOICES = ['success', 'failed', 'timeout']


def build_payload(
    vehicle_code: str,
    execute_date: str,
    case_no: str,
    result: str,
    duration_seconds: int,
    log_url: str | None,
    start_time: str | None,
    viu_code: str | None = None,
):
    if not start_time:
        start_time = f'{execute_date} 09:00:00'
    result_item = {
        'case_no': case_no,
        'start_time': start_time,
        'duration_seconds': duration_seconds,
        'result': result,
        'log_url': log_url,
    }
    if viu_code is not None:
        result_item['viu_code'] = viu_code
    return {
        'vehicle_code': vehicle_code,
        'execute_date': execute_date,
        'results': [
            result_item,
        ],
    }


def build_mock_payload(
    vehicle_code: str,
    execute_date: str,
    case_prefix: str,
    case_count: int,
    base_log_url: str | None,
    viu_codes: list[str] | None = None,
):
    base_dt = datetime.strptime(f'{execute_date} 09:00:00', '%Y-%m-%d %H:%M:%S')
    results = []
    normalized_viu_codes = [code.strip().lower() for code in (viu_codes or []) if code.strip()]
    for index in range(1, case_count + 1):
        case_no = f'{case_prefix}{index:03d}'
        result = random.choices(RESULT_CHOICES, weights=[0.75, 0.2, 0.05], k=1)[0]
        start_time = (base_dt + timedelta(minutes=index * 3)).strftime('%Y-%m-%d %H:%M:%S')
        duration_seconds = random.randint(20, 900)
        log_url = (
            f'{base_log_url.rstrip("/")}/{vehicle_code}/{case_no}/{execute_date}'
            if base_log_url
            else None
        )
        results.append(
            {
                'case_no': case_no,
                'start_time': start_time,
                'duration_seconds': duration_seconds,
                'result': result,
                'log_url': log_url,
                **(
                    {'viu_code': normalized_viu_codes[(index - 1) % len(normalized_viu_codes)]}
                    if normalized_viu_codes
                    else {}
                ),
            }
        )
    return {
        'vehicle_code': vehicle_code,
        'execute_date': execute_date,
        'results': results,
    }


def post_report(base_url: str, payload: dict, timeout: int):
    url = f'{base_url.rstrip("/")}{DEFAULT_API_PATH}'
    print(f'[auto-test-report] POST {url}')
    print('[auto-test-report] payload:')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    response = requests.post(url, json=payload, timeout=timeout)
    print(f'[auto-test-report] status={response.status_code}')
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)
    response.raise_for_status()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='上报自动化测试每日执行结果到 Focus Admin',
    )
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL, help='服务地址，默认 http://127.0.0.1:8000')
    parser.add_argument('--vehicle-code', required=True, help='车型编号，例如 mcu20-veh-1')
    parser.add_argument('--execute-date', required=True, help='执行日期，例如 2026-04-08')
    parser.add_argument('--timeout', type=int, default=20, help='HTTP 超时秒数')

    parser.add_argument('--case-no', help='单用例模式：用例编号')
    parser.add_argument('--result', choices=RESULT_CHOICES, help='单用例模式：结果 success/failed/timeout')
    parser.add_argument('--duration-seconds', type=int, default=120, help='单用例模式：执行时长，默认 120')
    parser.add_argument('--log-url', default='', help='单用例模式：日志链接')
    parser.add_argument('--start-time', default='', help='单用例模式：开始时间，例如 2026-04-08 09:00:00')
    parser.add_argument('--viu-code', default='', help='单用例模式：VIU编号，例如 viu0')

    parser.add_argument('--mock-batch', action='store_true', help='批量模拟上报')
    parser.add_argument('--case-prefix', default='CASE-', help='批量模拟：用例前缀，默认 CASE-')
    parser.add_argument('--case-count', type=int, default=5, help='批量模拟：用例数量，默认 5')
    parser.add_argument('--base-log-url', default='https://mock.example.com/logs', help='批量模拟：日志 URL 前缀')
    parser.add_argument('--seed', type=int, default=20260408, help='批量模拟：随机种子')
    parser.add_argument('--viu-codes', default='', help='批量模拟：VIU编号列表，逗号分隔，例如 viu0,viu1,viu2')

    args = parser.parse_args()

    if args.mock_batch:
        random.seed(args.seed)
        payload = build_mock_payload(
            vehicle_code=args.vehicle_code,
            execute_date=args.execute_date,
            case_prefix=args.case_prefix,
            case_count=args.case_count,
            base_log_url=args.base_log_url,
            viu_codes=[item.strip() for item in args.viu_codes.split(',')] if args.viu_codes else [],
        )
    else:
        if not args.case_no or not args.result:
            parser.error('单用例模式下必须传 --case-no 和 --result')
        payload = build_payload(
            vehicle_code=args.vehicle_code,
            execute_date=args.execute_date,
            case_no=args.case_no,
            result=args.result,
            duration_seconds=max(args.duration_seconds, 0),
            log_url=args.log_url or None,
            start_time=args.start_time or None,
            viu_code=args.viu_code.strip().lower() or None,
        )

    post_report(args.base_url, payload, args.timeout)
