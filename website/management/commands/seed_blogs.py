from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Blog, BlogDetails, TeamMember


class Command(BaseCommand):
    help = "Create the blog content shown in the Blog and Blog Details designs."

    def _attach_image(self, instance, field_name, source_name, target_name):
        """Copy a bundled design asset to media storage only the first time."""
        field = getattr(instance, field_name)
        if field:
            return
        source = Path(settings.BASE_DIR) / source_name
        with source.open("rb") as image_file:
            field.save(target_name, File(image_file), save=False)
        instance.save(update_fields=[field_name])

    def handle(self, *args, **options):
        published_at = timezone.make_aware(datetime(2026, 7, 2, 9, 0))

        gustavo, _ = TeamMember.objects.get_or_create(
            name="Gustavo Culhane",
            designation="Sales head",
            defaults={"bio": "Sales head"},
        )
        self._attach_image(gustavo, "image", "static/images/user-img.jpg", "gustavo-culhane.jpg")

        maria = TeamMember.objects.filter(name="Maria Chen").first()
        alex = TeamMember.objects.filter(name="Alex Johnson").first()
        james = TeamMember.objects.filter(name="James Levin").first()

        article_title = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor"
        article_description = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
            "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
            "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
        )
        featured, _ = Blog.objects.update_or_create(
            slug="local-lead-generation",
            defaults={
                "blog_name": "Local lead generation",
                "title": article_title,
                "short_description": article_description,
                "author": gustavo,
                "read_time_minutes": 10,
                "published_at": published_at,
                "is_featured": True,
                "display_on_website": True,
                "display_order": 0,
            },
        )
        self._attach_image(featured, "image", "static/images/blog-image.png", "local-lead-generation.png")

        details = [
            (1, """
                <p>Local lead generation describes methods and processes for attracting and/or retaining the attention of potential customers/clients who are geographically co-located with the business. Local lead generation offers various advantages including a targeted approach, better ROI, and brand awareness.</p>
                <p>This article will discuss local lead generation, its definition, strategies, and advantages.</p>
                <h3>What is local lead generation?</h3>
                <p>Local business lead generation is a marketing strategy intent on attracting new or repeat customers or clients who are within the locale of a business or service provider. It is designed to drive foot traffic and inquiries or conversions from individuals or businesses within the local area.</p>
                <p>This approach utilizes assorted digital marketing tactics: boosting online presence for local SEO by utilizing local keywords and references in content to emphasize closeness, maintaining up-to-date and relevant business listings on directories, running geo-targeted advertising campaigns, and encouraging customer reviews.</p>
                <p>The goal is to connect with nearby prospects who are actively seeking products or services within their community or to stand out in a crowded field of browsing customers. Let's cover the top five.</p>
                <h3>• Niche directories</h3>
                <p>Niche sector, specialized, or industry-specific directories, are online listing and directory platforms for products or services. These cater to specific interests, demographics, or the specific needs of users. Curated and concentrated content provides resources for finding relevant businesses or information. Niche directories can be a surprisingly valuable and effective part of an online marketing and lead generation strategy.</p>
            """),
            (2, "<h3>• Local SEO</h3><p>Local search engine optimization (SEO) is a very commonly applied digital marketing strategy that can dramatically boost online presence. It seeks to attract and appeal to local customers and generate high-quality leads. The advantages of local SEO in lead generation are enhanced ranking in local searches, higher website traffic, enhanced customer trust through positive reviews, and amplified opportunities to connect with nearby prospects.</p>"),
            (3, "<h3>• Local SEM</h3><p>Local search engine marketing (SEM) is aimed at generating leads and increasing the ranking and resultant connection rate of local businesses as presented in search engine results pages (SERPs). It complements local SEO efforts by committing to paid advertising that targets a region or market sector.</p><h3>• Social media</h3><p>Social media plays a pivotal role in lead generation. It provides a powerful platform to connect with potential customers, build relationships, and drive inquiries or conversions. Social media platforms have enormous user bases. They allow businesses to connect with a broader audience, amplifying brand visibility and awareness.</p><h3>• Hosting local events or webinars</h3><p>Hosting local events and webinars is a great way to establish yourself as an area's go-to resource on a specific topic. Plus, target leads must submit their contact info to attend the event.</p>"),
        ]
        for display_order, content in details:
            BlogDetails.objects.update_or_create(
                blog=featured,
                display_order=display_order,
                defaults={"content": content.strip(), "display_on_website": True},
            )

        card_blogs = [
            ("web-development", "Web development", "Exploring the latest trends in web technologies and frameworks. Stay updated with responsive design and modern development practices.", maria, 5, 1),
            ("graphic-design", "Graphic design", "The art of visual communication through typography, imagery, and color. Learn how to create designs that tell a story.", alex, 6, 2),
            ("product-design-ux", "Product design & UX", "Lorem ipsum dolor sit amet consectetur. Porttitor velit interdum tortor mauris imperdiet.", james, 4, 3),
            ("web-development-trends", "Web development", "Exploring the latest trends in web technologies and frameworks. Stay updated with responsive design and modern development practices.", maria, 5, 4),
            ("graphic-design-basics", "Graphic design", "The art of visual communication through typography, imagery, and color. Learn how to create designs that tell a story.", alex, 6, 5),
            ("product-design-ux-guide", "Product design & UX", "Lorem ipsum dolor sit amet consectetur. Porttitor velit interdum tortor mauris imperdiet.", james, 4, 6),
        ]
        for slug, title, description, author, read_time, order in card_blogs:
            blog, _ = Blog.objects.update_or_create(
                slug=slug,
                defaults={
                    "blog_name": title,
                    "title": title,
                    "short_description": description,
                    "author": author,
                    "read_time_minutes": read_time,
                    "published_at": published_at,
                    "is_featured": False,
                    "display_on_website": True,
                    "display_order": order,
                },
            )
            self._attach_image(blog, "image", "media/insights/test.jpg", f"{slug}.jpg")

        self.stdout.write(self.style.SUCCESS("Seeded 7 blog posts and the featured article details."))
