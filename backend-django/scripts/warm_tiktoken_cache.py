#!/usr/bin/env python3
"""
Warm and optionally archive tiktoken encoder cache files for DeepAudit production.

Examples:
  python scripts/warm_tiktoken_cache.py
  python scripts/warm_tiktoken_cache.py --cache-dir /srv/focus/tiktoken-cache
  python scripts/warm_tiktoken_cache.py --cache-dir /srv/focus/tiktoken-cache --archive /tmp/tiktoken-cache.tar.gz
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
import tempfile
from pathlib import Path


ENCODER_URLS = {
    "cl100k_base": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
    "o200k_base": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
    "p50k_base": "https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken",
    "r50k_base": "https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken",
}

DEFAULT_ENCODINGS = ["cl100k_base", "o200k_base"]
DEFAULT_MODELS = ["gpt-4", "gpt-4o", "gpt-5", "text-embedding-3-small"]


def _default_cache_dir() -> str:
    for env_name in ("TIKTOKEN_CACHE_DIR", "DATA_GYM_CACHE_DIR"):
        value = str(os.environ.get(env_name, "") or "").strip()
        if value:
            return value
    return str(Path(tempfile.gettempdir()) / "data-gym-cache")


def _cache_file_for_encoding(cache_dir: Path, encoding_name: str) -> Path | None:
    blob_url = ENCODER_URLS.get(encoding_name)
    if not blob_url:
        return None
    cache_key = hashlib.sha1(blob_url.encode("utf-8")).hexdigest()
    return cache_dir / cache_key


def _archive_cache(cache_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(cache_dir, arcname=cache_dir.name)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Warm DeepAudit tiktoken cache files for offline/private-network deployments.",
    )
    parser.add_argument(
        "--cache-dir",
        default=_default_cache_dir(),
        help="Directory used for TIKTOKEN_CACHE_DIR / DATA_GYM_CACHE_DIR.",
    )
    parser.add_argument(
        "--encodings",
        nargs="*",
        default=list(DEFAULT_ENCODINGS),
        help="Encoding names to warm. Default: %(default)s",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=list(DEFAULT_MODELS),
        help="Models to resolve via tiktoken.encoding_for_model. Default: %(default)s",
    )
    parser.add_argument(
        "--archive",
        default="",
        help="Optional .tar.gz output path for packaging the warmed cache directory.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Do not download; only verify whether the requested cache files already exist.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache_dir)
    os.environ["DATA_GYM_CACHE_DIR"] = str(cache_dir)

    try:
        import tiktoken
    except ImportError:
        print(
            "ERROR: tiktoken is not installed in the current interpreter.\n"
            "Use the backend virtualenv, for example:\n"
            "  source /srv/focus/venv/bin/activate\n"
            "  python scripts/warm_tiktoken_cache.py --cache-dir /srv/focus/tiktoken-cache",
            file=sys.stderr,
        )
        return 2

    requested_encodings = [item for item in args.encodings if str(item or "").strip()]
    requested_models = [item for item in args.models if str(item or "").strip()]

    warmed_encodings: set[str] = set()
    failures: list[str] = []

    print(f"Cache directory: {cache_dir}")
    print(f"Verify only: {args.verify_only}")

    for model in requested_models:
        try:
            encoder = tiktoken.encoding_for_model(model)
            encoding_name = getattr(encoder, "name", "") or "unknown"
            if not args.verify_only:
                encoder.encode("DeepAudit cache warm-up")
            warmed_encodings.add(encoding_name)
            print(f"[OK] model={model} -> encoding={encoding_name}")
        except Exception as exc:
            failures.append(f"model={model}: {exc}")
            print(f"[ERR] model={model}: {exc}", file=sys.stderr)

    for encoding_name in requested_encodings:
        try:
            cache_file = _cache_file_for_encoding(cache_dir, encoding_name)
            if args.verify_only:
                if cache_file is not None and cache_file.exists():
                    warmed_encodings.add(encoding_name)
                    print(f"[OK] encoding={encoding_name} already cached at {cache_file}")
                else:
                    raise FileNotFoundError(f"cache file missing for {encoding_name}")
            else:
                encoder = tiktoken.get_encoding(encoding_name)
                encoder.encode("DeepAudit cache warm-up")
                warmed_encodings.add(encoding_name)
                if cache_file is not None:
                    print(f"[OK] encoding={encoding_name} cached at {cache_file}")
                else:
                    print(f"[OK] encoding={encoding_name} warmed")
        except Exception as exc:
            failures.append(f"encoding={encoding_name}: {exc}")
            print(f"[ERR] encoding={encoding_name}: {exc}", file=sys.stderr)

    if args.archive:
        archive_path = Path(args.archive).expanduser().resolve()
        _archive_cache(cache_dir, archive_path)
        print(f"Archive written: {archive_path}")

    print("")
    print("Recommended runtime environment:")
    print(f"  TIKTOKEN_CACHE_DIR={cache_dir}")
    print(f"  DATA_GYM_CACHE_DIR={cache_dir}")
    print("  DEEPAUDIT_TIKTOKEN_MODE=local")

    if failures:
        print("")
        print("Failures:")
        for item in failures:
            print(f"  - {item}")
        return 1

    if warmed_encodings:
        print("")
        print("Ready encodings:")
        for item in sorted(warmed_encodings):
            print(f"  - {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
