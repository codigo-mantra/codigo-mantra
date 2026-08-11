from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Blog, BlogDetails


class Command(BaseCommand):
    help = (
        "Copy BlogDetails from the featured blog (or the blog with the most details) "
        "to every other public blog that has no visible BlogDetails of its own. "
        "Safe to re-run: blogs that already have at least one visible BlogDetails "
        "row are never overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-slug",
            type=str,
            default=None,
            help="Copy details from this specific blog slug instead of auto-detecting.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace destination BlogDetails even if the target blog already has some.",
        )

    def _pick_source(self):
        public = Blog.objects.filter(display_on_website=True).prefetch_related("details")
        featured = public.filter(is_featured=True).first()
        if featured and any(d.display_on_website for d in featured.details.all()):
            return featured
        recent = public.order_by("-published_at").first()
        if recent and any(d.display_on_website for d in recent.details.all()):
            return recent
        best = None
        best_count = -1
        for blog in public:
            visible = [d for d in blog.details.all() if d.display_on_website]
            if len(visible) > best_count:
                best = blog
                best_count = len(visible)
        if best_count > 0:
            return best
        return None

    @transaction.atomic
    def handle(self, *args, **options):
        source_slug = options.get("source_slug")
        overwrite = options.get("overwrite")

        if source_slug:
            try:
                source = Blog.objects.prefetch_related("details").get(slug=source_slug)
            except Blog.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"No blog found with slug '{source_slug}'."))
                return
        else:
            source = self._pick_source()
            if source is None:
                self.stderr.write(
                    self.style.ERROR(
                        "No source blog with visible BlogDetails found. "
                        "Seed blogs first, or pass --source-slug."
                    )
                )
                return

        source_details = [d for d in source.details.all() if d.display_on_website]
        if not source_details:
            self.stderr.write(self.style.ERROR(f"Source blog '{source.slug}' has no visible BlogDetails."))
            return

        self.stdout.write(f"Source blog: {source.slug} ({len(source_details)} visible detail blocks)")

        targets = Blog.objects.filter(display_on_website=True).exclude(pk=source.pk).prefetch_related("details")

        created_total = 0
        deleted_total = 0
        skipped = 0

        for target in targets:
            has_own = any(d.display_on_website for d in target.details.all())
            if has_own and not overwrite:
                skipped += 1
                self.stdout.write(f"  SKIP  {target.slug} — already has visible details (use --overwrite to replace)")
                continue

            if has_own and overwrite:
                removed, _ = target.details.all().delete()
                deleted_total += removed
                self.stdout.write(f"  CLEAR {target.slug} — removed {removed} existing detail blocks")

            for src_detail in source_details:
                BlogDetails.objects.create(
                    blog=target,
                    content=src_detail.content,
                    image=src_detail.image,
                    display_order=src_detail.display_order,
                    display_on_website=True,
                )
                created_total += 1
            self.stdout.write(f"  CLONE {target.slug} — copied {len(source_details)} detail blocks")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_total} BlogDetails rows across "
                f"{targets.count() - skipped} target blog(s). "
                f"Skipped {skipped} blog(s) with existing content. "
                f"Deleted {deleted_total} stale row(s)."
            )
        )
