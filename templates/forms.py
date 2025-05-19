from django import forms
from .models import Template
from .fields import MultipleFileField  
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

class TemplateAdminForm(forms.ModelForm):
    additional_images_upload = MultipleFileField(
        label="Upload Additional Images",
        required=False
    )

    class Meta:
        model = Template
        fields = '__all__'

    def clean_image(self):
        image_file = self.cleaned_data.get('image')
        if image_file and hasattr(image_file, 'file'):  # Check if a new file is uploaded
            try:
                # Upload the image to Cloudinary
                result = cloudinary.uploader.upload(
                    image_file,
                    folder="templates/",
                    resource_type="image"
                )
                # Store the public_id (e.g., "templates/image_name")
                self.cleaned_data['image'] = result['public_id']
                logger.info(f"Successfully uploaded image to Cloudinary: {result['public_id']}")
            except Exception as e:
                logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
                raise forms.ValidationError(f"Failed to upload image to Cloudinary: {str(e)}")
        return self.cleaned_data['image']

    def clean_additional_images_upload(self):
        files = self.files.getlist('additional_images_upload')
        uploaded_urls = []
        if files:
            for file in files:
                try:
                    # Upload each file to Cloudinary
                    result = cloudinary.uploader.upload(
                        file,
                        folder="templates/",
                        resource_type="image"
                    )
                    uploaded_urls.append(result['public_id'])  # e.g., "templates/extra1"
                    logger.info(f"Successfully uploaded additional image to Cloudinary: {result['public_id']}")
                except Exception as e:
                    logger.error(f"Failed to upload additional image to Cloudinary: {str(e)}")
                    raise forms.ValidationError(f"Failed to upload additional image to Cloudinary: {str(e)}")
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