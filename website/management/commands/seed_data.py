from django.core.management.base import BaseCommand
from website.models import (
    Industry, Department, Service, TeamMember,
    CompanyContact, SocialMediaHandle, CaseStudy, Insight, FAQ
)
from django.utils.text import slugify
from django.utils import timezone

class Command(BaseCommand):
    help = "Seed database with initial useful data"

    def handle(self, *args, **kwargs):

        industries = [
            ("fintech", "Fintech"),
            ("saas-technology", "SaaS & Technology"),
            ("ecommerce", "E-commerce"),
            ("edtech", "Edtech"),
            ("healthcare", "Healthcare"),
            ("enterprise-b2b", "Enterprise & B2B"),
            ("food-beverage", "Food & Beverage"),
        ]

        for slug, name in industries:
            Industry.objects.get_or_create(name=name, slug=slug)

        departments = [
            ("Engineering", "engineering"),
            ("Design", "design"),
            ("Marketing", "marketing"),
            ("Operations", "operations"),
        ]

        for name, slug in departments:
            Department.objects.get_or_create(name=name, slug=slug)

        services = [
            ("Product Design & Ux", "product-design-and-ux","User-focused design that improves experience, engagement, and conversion."),
            ("Web & mobile Development", "web-and-mobile-development","User-focused design that improves experience, engagement, and conversion."),
            ("Custom Software Development", "custom-software-development","Robust backend systems and integrations tailored to business needs."),
            ("Growth & Performance Marketing", "growth-and-performance-marketing","Data-driven strategies to acquire users and accelerate growth."),
            ("Web Development", "web-development","Building and maintaining websites, ensuring functionality and aesthetic appeal."),
            ("Brand Strategy", "brand-strategy","Crafting a unique identity and positioning for a product to resonate with target audiences."),
        ]

        for name, slug, description in services:
            Service.objects.get_or_create(name=name, slug=slug, description=description)
        TeamMember.objects.get_or_create(
            name="XYZ",
            designation="Full Stack Developer",
            bio="Leads technology and architecture decisions."
        )

        CompanyContact.objects.get_or_create(
            email="info@codigomantra.com",
            phone="+91 9779111611",
            address="QUARK ATRIUM, Industrial Area, Sector 74, Sahibzada Ajit Singh Nagar, Punjab 160072"
        )

        SocialMediaHandle.objects.get_or_create(
            platform="LinkedIn",
            url="https://linkedin.com/company/codigomantra"
        )

        author = TeamMember.objects.first()

        insights_data = [
            {
                "title": "How AI is Transforming Modern Businesses",
                "content": "Artificial Intelligence is revolutionizing industries by automating workflows and improving decision making.",
                "read_time_minutes": 6,
            },
            {
                "title": "Why UX Design Matters for Startup Success",
                "content": "User experience plays a crucial role in determining product adoption and retention.",
                "read_time_minutes": 4,
            },
            {
                "title": "Scaling Web Applications with Cloud Infrastructure",
                "content": "Cloud platforms enable startups to scale quickly without worrying about infrastructure limitations.",
                "read_time_minutes": 7,
            },
            {
                "title": "Top Web Development Trends in 2026",
                "content": "Modern frameworks, serverless architecture, and AI integrations are reshaping web development.",
                "read_time_minutes": 5,
            },
        ]

        for data in insights_data:
            title = data["title"]

            Insight.objects.get_or_create(
                slug=slugify(title),
                defaults={
                    "title": title,
                    "content": data["content"],
                    "author": author,
                    "read_time_minutes": data["read_time_minutes"],
                    "published_at": timezone.now(),
                }
            )



            faqs = [
                {
                    "question": "What services do you offer?",
                    "answer": "We offer web development, mobile app development, and cloud solutions."
                },
                {
                    "question": "How can I contact support?",
                    "answer": "You can contact us via the contact form or email us at support@example.com."
                },
                {
                    "question": "Do you provide custom solutions?",
                    "answer": "Yes, we tailor our solutions based on client requirements."
                },
                {
                    "question": "What is your pricing model?",
                    "answer": "Our pricing depends on project scope and complexity."
                },
                {
                    "question": "How long does a project take?",
                    "answer": "Timelines vary depending on requirements, but we ensure timely delivery."
                }
            ]

            created_count = 0

            for faq in faqs:
                _, created= FAQ.objects.get_or_create(
                    question=faq["question"],
                    defaults={"answer": faq["answer"]}
                )
        self.stdout.write(self.style.SUCCESS("Dummy data created successfully"))