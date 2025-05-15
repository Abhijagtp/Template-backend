from time import timezone
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Template(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='templates/')
    additional_images = models.JSONField(default=list)  # List of additional image URLs
    features = models.JSONField(default=list)  # List of features, e.g., ["Responsive Design", "SEO Optimized"]
    tech_stack = models.JSONField(default=list)  # List of tech stack, e.g., ["React", "Tailwind CSS"]
    live_preview_url = models.URLField(max_length=500, blank=True, null=True)  # URL for live preview
    zip_file_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0

class Review(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='reviews')
    user = models.CharField(max_length=100)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.template.title}"
    


class Payment(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='payments')
    order_id = models.CharField(max_length=100, unique=True)  # Cashfree order ID
    user_email = models.EmailField()
    user_phone = models.CharField(max_length=15, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='PENDING')  # PENDING, SUCCESS, FAILED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.order_id} for {self.template.title}"
    



# Inquiry model for user inquiries

class SupportInquiry(models.Model):
    INQUIRY_TYPES = (
        ('PAYMENT_FAILURE', 'Payment Failure'),
        ('PAYMENT_STATUS', 'Payment Status'),
        ('TEMPLATE_DOWNLOAD', 'Template Download Issue'),
        ('GENERAL', 'General'),
    )
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    )

    inquiry_id = models.CharField(max_length=20, unique=True, editable=False)
    email = models.EmailField()
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES)
    description = models.TextField()
    order_id = models.CharField(max_length=50, blank=True, null=True)  # Optional, links to Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    response = models.TextField(blank=True, null=True)  # Admin response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.inquiry_id:
            # Generate unique inquiry ID (e.g., SUPP-123456)
            self.inquiry_id = f"SUPP-{int(timezone.now().timestamp())}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inquiry_id} - {self.email} - {self.status}"

    class Meta:
        ordering = ['-created_at']