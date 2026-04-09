import uuid
from django.db import models
from ckeditor.fields import RichTextField
from django.core.validators import RegexValidator

class TimeStamp(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ContactUs(TimeStamp):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )])
    message = models.TextField()


    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class CompanyContact(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    google_map_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.email


class SocialMediaHandle(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=100)
    url = models.URLField()
    icon = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.platform


class Industry(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    svg_icon = models.TextField()

    def __str__(self):
        return self.name
    

class Technology(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name
    

class Department(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    

class Service(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.FileField(upload_to="services/icons/", blank=True, null=True)
    cover_image = models.FileField(upload_to="services/covers/", blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    display_order = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.display_order:
            self.display_order = Service.objects.count() + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CaseStudy(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    about = models.TextField(blank=True, null=True)
    goal = models.TextField(blank=True, null=True)
    challenge = models.TextField(blank=True, null=True)
    outcome = models.TextField(blank=True, null=True)
    timeline = models.CharField(max_length=255, blank=True)
    team = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True, null=True)
    cover_image = models.ImageField(upload_to="case_studies/", blank=True, null=True)

    services = models.ManyToManyField(Service, through="CaseStudyService")
    industries = models.ManyToManyField(Industry, through="CaseStudyIndustry")
    technologies = models.ManyToManyField(Technology, through="CaseStudyTechnology")

    def __str__(self):
        return self.title


class CaseStudyImage(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_study = models.ForeignKey(
        CaseStudy,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="case_studies/images/")

    def __str__(self):
        return f"{self.case_study.title} Image"


class CaseStudyService(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    case_study = models.ForeignKey(CaseStudy, on_delete=models.CASCADE)


class CaseStudyIndustry(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE)
    case_study = models.ForeignKey(CaseStudy, on_delete=models.CASCADE)


class CaseStudyTechnology(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    technology = models.ForeignKey(Technology, on_delete=models.CASCADE)
    case_study = models.ForeignKey(CaseStudy, on_delete=models.CASCADE)


class Testimonial(TimeStamp):

    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video")
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_name = models.CharField(max_length=255)
    client_image = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    client_designation = models.CharField(max_length=255, blank=True)
    organisation_name = models.CharField(max_length=255)
    message = models.TextField()

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES
    )

    review_image = models.ImageField(upload_to="testimonials/reviews/", blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    platform_image = models.FileField(upload_to="testimonials/platform/", blank=True, null=True)

    def __str__(self):
        return self.client_name


class TeamMember(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to="team/")
    linkedin_url = models.URLField(blank=True, null=True)
    display_order = models.IntegerField(default=0)
    display_on_website = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CompanyEventImage(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="company_events/")
    event = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Insight(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    image = models.ImageField(upload_to="insights/", blank=True, null=True)

    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="insights"
    )
    read_time_minutes = models.IntegerField(default=5)
    published_at = models.DateTimeField()

    def __str__(self):
        return self.title


class Newsletter(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class JobOpening(TimeStamp):

    JOB_TYPE_CHOICES = [
        ("Full Time", "Full Time"),
        ("Part Time", "Part Time"),
        ("Contract", "Contract"),
        ("Internship", "Internship"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name="job_openings"
    )
    short_description = models.CharField(max_length=500)
    location = models.CharField(max_length=255)
    description = RichTextField()
    is_active = models.BooleanField(default=True)
    count = models.IntegerField(default=1)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    package = models.CharField(max_length=100)
    experience = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class Application(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(
        JobOpening,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to="resumes/")
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.job.title}"


class FAQ(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.CharField(max_length=500)
    answer = models.TextField()

    def __str__(self):
        return self.question

class PrivacyPolicy(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField()
    content = RichTextField(blank=True, null = True)
    pdf = models.FileField(upload_to="documents/privacy_policy/", blank=True, null=True)

    def __str__(self):
        return self.title



class TermsofService(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.TextField()
    content = RichTextField(blank=True, null = True)
    pdf = models.FileField(upload_to="documents/terms_of_service/", blank=True, null=True)

    def __str__(self):
        return self.title


class User(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)   # e.g., "client" or "consultant"
    status = models.CharField(max_length=100) # e.g., "active", "inactive"

    def __str__(self):
        return self.name


# ===========================
# BOOKINGS TABLE
# ===========================
class Booking(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="client_bookings"
    )
    consultant = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="consultant_bookings"
    )

    booking_date = models.DateField()
    start_time = models.TimeField()
    meet_link = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=100)
    service_requested = models.CharField(max_length=255)
    project_brief = models.TextField()

    # NEW FIELDS
    is_attended_by_admin = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "booking_date", "start_time"],
                name="unique_client_booking"
            ),
        ]

    def __str__(self):
        return f"Booking - {self.client.name} with {self.consultant.name}"