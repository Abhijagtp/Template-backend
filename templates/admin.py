from django.contrib import admin

# Register your models here.
from .models import Category, Template, Review, Payment, SupportInquiry


admin.site.site_header = "Template Admin"
admin.site.register(Category)
admin.site.register(Template)
admin.site.register(Review)
admin.site.register(Payment)


@admin.register(SupportInquiry)
class SupportInquiryAdmin(admin.ModelAdmin):
    list_display = ['inquiry_id', 'email', 'inquiry_type', 'status', 'created_at']
    list_filter = ['inquiry_type', 'status', 'created_at']
    search_fields = ['inquiry_id', 'email', 'description', 'order_id']
    readonly_fields = ['inquiry_id', 'email', 'inquiry_type', 'description', 'order_id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('inquiry_id', 'email', 'inquiry_type', 'order_id', 'description')
        }),
        ('Response', {
            'fields': ('status', 'response')
        }),
    )

    def save_model(self, request, obj, form, change):
        if change and 'response' in form.changed_data or 'status' in form.changed_data:
            from .views import send_response_email
            send_response_email(obj)
        super().save_model(request, obj, form, change)