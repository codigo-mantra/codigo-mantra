from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Blog


class Command(BaseCommand):
    help = (
        "Recalculate and save read_time_minutes for every Blog in the database "
        "based on the actual word count of its visible BlogDetails content "
        "(238 words per minute, rounded up). Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        blogs = Blog.objects.all().prefetch_related("details")
        total = blogs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No blogs found in the database."))
            return

        wpm = Blog.READING_WORDS_PER_MINUTE
        updated = 0
        unchanged = 0

        for blog in blogs:
            old_rt = blog.read_time_minutes
            word_count = blog.get_total_word_count()
            new_rt = blog.calculate_reading_time_minutes()

            if new_rt == old_rt:
                unchanged += 1
                self.stdout.write(
                    f"  OK    {blog.slug}: {old_rt} min "
                    f"({word_count} words, {wpm} WPM) — unchanged"
                )
                continue

            if not dry_run:
                blog.read_time_minutes = new_rt
                blog.save(update_fields=["read_time_minutes"])

            updated += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  UPDATE {blog.slug}: {old_rt} -> {new_rt} min "
                    f"({word_count} words, {wpm} WPM)"
                    + (" [DRY RUN]" if dry_run else "")
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Scanned {total} blog(s): "
                f"updated {updated}, left {unchanged} unchanged."
                + (" (DRY RUN — nothing was saved)" if dry_run else "")
            )
        )
