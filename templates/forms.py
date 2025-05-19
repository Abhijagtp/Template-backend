from django import forms
from .models import Template
from .fields import MultipleFileField  
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)


class TemplateAdminForm(forms.ModelForm):
    image_upload = forms.FileField(
        label="Upload Main Image",
        required=False
    )
    additional_images_upload = MultipleFileField(
        label="Upload Additional Images",
        required=False
    )

    class Meta:
        model = Template
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        image_upload = cleaned_data.get('image_upload')
        if image_upload:
            try:
                result = cloudinary.uploader.upload(
                    image_upload,
                    folder="templates/",
                    resource_type="image"
                )
                cleaned_data['image'] = result['public_id']
                logger.info(f"Successfully uploaded image to Cloudinary: {result['public_id']}")
            except Exception as e:
                logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
                raise forms.ValidationError(f"Failed to upload image to Cloudinary: {str(e)}")
        return cleaned_data

    def clean_additional_images_upload(self):
        files = self.files.getlist('additional_images_upload')
        uploaded_urls = []
        if files:
            for file in files:
                try:
                    result = cloudinary.uploader.upload(
                        file,
                        folder="templates/",
                        resource_type="image"
                    )
                    uploaded_urls.append(result['public_id'])
                    logger.info(f"Successfully uploaded additional image to Cloudinary: {result['public_id']}")
                except Exception as e:
                    logger.error(f"Failed to upload additional image to Cloudinary: {str(e)}")
                    raise forms.ValidationError(f"Failed to upload additional image to Cloudinary: {str(e)}")
        return uploaded_urls

    def save(self, commit=True):
        instance = super().save(commit=False)
        additional_images = self.cleaned_data.get('additional_images_upload', [])
        if additional_images:
            instance.additional_images = additional_images
        if commit:
            instance.save()
        return instance