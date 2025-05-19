from django import forms
from .models import Template
from .fields import MultipleFileField  

class TemplateAdminForm(forms.ModelForm):
    additional_images_upload = MultipleFileField(
        label="Upload Additional Images",
        required=False
    )

    class Meta:
        model = Template
        fields = '__all__'

    def clean_additional_images_upload(self):
        files = self.files.getlist('additional_images_upload')
        uploaded_urls = []
        if files:
            import cloudinary.uploader
            for file in files:
                # Upload each file to Cloudinary
                result = cloudinary.uploader.upload(file, folder="templates/")
                uploaded_urls.append(result['public_id'])  # e.g., "templates/extra1"
        return uploaded_urls

    def save(self, commit=True):
        instance = super().save(commit=False)
        additional_images = self.cleaned_data.get('additional_images_upload', [])
        if additional_images:
            # Update additional_images JSONField
            instance.additional_images = additional_images
        if commit:
            instance.save()
        return instance