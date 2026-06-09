import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections, connections, transaction
from django.utils import timezone

from apps.code_scan.models import ScanResult, ScanResultOccurrence, ShieldApplication


class Command(BaseCommand):
    help = "安全清理已回填到 occurrence 的旧 scan_result 行"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅清理指定扫描项目")
        parser.add_argument("--batch-size", type=int, default=100, help="每批处理的旧结果行数")
        parser.add_argument("--limit", type=int, default=0, help="最多删除多少行，0 表示不限")
        parser.add_argument("--dry-run", action="store_true", help="只输出预计清理结果，不写入")
        parser.add_argument("--sleep-seconds", type=float, default=0, help="每批提交后暂停秒数")
        parser.add_argument("--max-retries", type=int, default=3, help="单批断线后的重试次数")

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        batch_size = max(int(options["batch_size"] or 100), 1)
        limit = max(int(options["limit"] or 0), 0)
        dry_run = bool(options["dry_run"])
        sleep_seconds = max(float(options["sleep_seconds"] or 0), 0)
        max_retries = max(int(options["max_retries"] or 0), 0)

        scanned = 0
        deleted = 0
        linked_applications = 0
        unlinked_applications = 0
        skipped_refs = 0
        last_occurrence_id = 0

        while True:
            remaining = limit - deleted if limit else batch_size
            if limit and remaining <= 0:
                break
            current_batch_size = min(batch_size, remaining) if limit else batch_size
            rows = self._fetch_candidate_rows(
                last_occurrence_id=last_occurrence_id,
                batch_size=current_batch_size,
                project_id=project_id,
                max_retries=max_retries,
            )
            if not rows:
                break

            scanned += len(rows)
            last_occurrence_id = int(rows[-1]["id"])
            result = self._process_candidate_rows(
                rows,
                dry_run=dry_run,
                max_retries=max_retries,
            )
            deleted += result["deleted"]
            linked_applications += result["linked_applications"]
            unlinked_applications += result["unlinked_applications"]
            skipped_refs += result["skipped_refs"]

            self.stdout.write(
                "purge progress: "
                f"scanned_occurrences={scanned}, "
                f"{'would_delete' if dry_run else 'deleted'}={deleted}, "
                f"linked_apps={linked_applications}, "
                f"unlinked_apps={unlinked_applications}, "
                f"skipped_refs={skipped_refs}"
            )

            connections.close_all()
            if sleep_seconds:
                time.sleep(sleep_seconds)

        action = "dry-run finished" if dry_run else "purge finished"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action}, scanned_occurrences={scanned}, "
                f"{'would_delete' if dry_run else 'deleted'}={deleted}, "
                f"linked_apps={linked_applications}, "
                f"unlinked_apps={unlinked_applications}, skipped_refs={skipped_refs}"
            )
        )

    def _fetch_candidate_rows(
        self,
        *,
        last_occurrence_id: int,
        batch_size: int,
        project_id: str | None,
        max_retries: int,
    ) -> list[dict]:
        qs = ScanResultOccurrence.objects.filter(
            legacy_result_id__isnull=False,
        )
        if last_occurrence_id:
            qs = qs.filter(id__gt=last_occurrence_id)
        if project_id:
            qs = qs.filter(task__project_id=project_id)
        qs = qs.order_by("id").values("id", "legacy_result_id")[:batch_size]
        return self._retrying_query(qs, max_retries=max_retries, label="legacy purge candidate load")

    def _process_candidate_rows(
        self,
        rows: list[dict],
        *,
        dry_run: bool,
        max_retries: int,
    ) -> dict[str, int]:
        occurrence_by_result_id = {
            str(row["legacy_result_id"]): int(row["id"])
            for row in rows
            if row.get("legacy_result_id")
        }
        legacy_result_ids = list(occurrence_by_result_id.keys())
        if not legacy_result_ids:
            return {
                "deleted": 0,
                "linked_applications": 0,
                "unlinked_applications": 0,
                "skipped_refs": 0,
            }

        for attempt in range(max_retries + 1):
            try:
                close_old_connections()
                if dry_run:
                    return self._preview_candidate_batch(
                        legacy_result_ids,
                        occurrence_by_result_id,
                    )
                with transaction.atomic():
                    return self._purge_candidate_batch(
                        legacy_result_ids,
                        occurrence_by_result_id,
                    )
            except OperationalError as exc:
                connections.close_all()
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 8)
                self.stderr.write(
                    f"legacy purge batch failed, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)

        return {
            "deleted": 0,
            "linked_applications": 0,
            "unlinked_applications": 0,
            "skipped_refs": 0,
        }

    def _preview_candidate_batch(
        self,
        legacy_result_ids: list[str],
        occurrence_by_result_id: dict[str, int],
    ) -> dict[str, int]:
        app_qs = ShieldApplication.objects.filter(result_id__in=legacy_result_ids)
        linkable_applications = app_qs.filter(
            occurrence__isnull=True,
            result_id__in=occurrence_by_result_id.keys(),
        ).count()
        unlinked_applications = app_qs.filter(
            occurrence__isnull=False,
        ).count() + linkable_applications
        unresolved_result_ids = set(
            app_qs.filter(occurrence__isnull=True)
            .exclude(result_id__in=occurrence_by_result_id.keys())
            .values_list("result_id", flat=True)
        )
        unresolved_result_id_set = {str(item) for item in unresolved_result_ids}
        safe_ids = [
            result_id
            for result_id in legacy_result_ids
            if result_id not in unresolved_result_id_set
        ]
        return {
            "deleted": len(safe_ids),
            "linked_applications": linkable_applications,
            "unlinked_applications": unlinked_applications,
            "skipped_refs": len(unresolved_result_ids),
        }

    def _purge_candidate_batch(
        self,
        legacy_result_ids: list[str],
        occurrence_by_result_id: dict[str, int],
    ) -> dict[str, int]:
        update_time = timezone.now()
        applications = list(
            ShieldApplication.objects.filter(
                result_id__in=legacy_result_ids,
                occurrence__isnull=True,
            )
        )
        linked_applications = 0
        for app in applications:
            occurrence_id = occurrence_by_result_id.get(str(app.result_id))
            if not occurrence_id:
                continue
            app.occurrence_id = occurrence_id
            app.sys_update_datetime = update_time
            linked_applications += 1
        applications_to_update = [app for app in applications if app.occurrence_id]
        if applications_to_update:
            ShieldApplication.objects.bulk_update(
                applications_to_update,
                ["occurrence", "sys_update_datetime"],
            )

        unlinked_applications = ShieldApplication.objects.filter(
            result_id__in=legacy_result_ids,
            occurrence__isnull=False,
        ).update(result_id=None, sys_update_datetime=update_time)

        unresolved_result_ids = {
            str(result_id)
            for result_id in ShieldApplication.objects.filter(
                result_id__in=legacy_result_ids,
                occurrence__isnull=True,
            ).values_list("result_id", flat=True)
        }
        safe_ids = [
            result_id
            for result_id in legacy_result_ids
            if result_id not in unresolved_result_ids
        ]
        if not safe_ids:
            return {
                "deleted": 0,
                "linked_applications": linked_applications,
                "unlinked_applications": unlinked_applications,
                "skipped_refs": len(unresolved_result_ids),
            }

        deleted_count, _ = ScanResult.objects.filter(id__in=safe_ids).delete()
        return {
            "deleted": deleted_count,
            "linked_applications": linked_applications,
            "unlinked_applications": unlinked_applications,
            "skipped_refs": len(unresolved_result_ids),
        }

    def _retrying_query(self, qs, *, max_retries: int, label: str):
        for attempt in range(max_retries + 1):
            try:
                close_old_connections()
                return list(qs)
            except OperationalError as exc:
                connections.close_all()
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 8)
                self.stderr.write(
                    f"{label} failed, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)
        return []
