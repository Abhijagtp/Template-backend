from rest_framework import serializers
from .models import Category, Template, Review, Payment, SupportInquiry
import cloudinary
from cloudinary import CloudinaryImage
import logging
from django.conf import settings

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'template', 'user', 'rating', 'comment', 'date']
        read_only_fields = ['date']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


logger = logging.getLogger(__name__)

class TemplateSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    additional_images = serializers.SerializerMethodField()

    class Meta:
        model = Template
        fields = [
            'id', 'title', 'description', 'category', 'price', 'image',
            'additional_images', 'features', 'tech_stack', 'reviews',
            'average_rating', 'live_preview_url', 'zip_file_url'
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0

    def get_image(self, obj):
        if obj.image:
            try:
                # Ensure public_id starts with "templates/"
                public_id = obj.image
                if not public_id.startswith('templates/'):
                    logger.warning(f"Invalid public_id format for image: {public_id}. Expected to start with 'templates/'.")
                    return None

                # Keep the full public_id including "templates/" for Cloudinary URL
                # No need to remove "templates/" since it's part of the actual path
                url = CloudinaryImage(public_id).build_url(
                    version='v1',  # Fixed version to 'v1'
                    secure=True,
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME
                )
                logger.debug(f"Generated Cloudinary URL for image {public_id}: {url}")
                return url
            except Exception as e:
                logger.error(f"Error generating Cloudinary URL for image {obj.image}: {str(e)}")
                return None
        return None

    def get_additional_images(self, obj):
        if obj.additional_images:
            try:
                urls = []
                for public_id in obj.additional_images:
                    # Ensure public_id starts with "templates/"
                    if not public_id.startswith('templates/'):
                        logger.warning(f"Invalid public_id format for additional image: {public_id}. Expected to start with 'templates/'.")
                        continue

                    # Keep the full public_id including "templates/" for Cloudinary URL
                    url = CloudinaryImage(public_id).build_url(
                        version='v1',  # Fixed version to 'v1'
                        secure=True,
                        cloud_name=settings.CLOUDINARY_CLOUD_NAME
                    )
                    logger.debug(f"Generated Cloudinary URL for additional image {public_id}: {url}")
                    urls.append(url)
                return urls
            except Exception as e:
                logger.error(f"Error generating Cloudinary URLs for additional_images {obj.additional_images}: {str(e)}")
                return []
        return []

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and 'category' in request.data:
            category_data = request.data.get('category')
            if isinstance(category_data, dict) and 'name' in category_data:
                category, _ = Category.objects.get_or_create(name=category_data['name'])
                validated_data['category'] = category
            else:
                raise serializers.ValidationError("Invalid category data. Must provide 'name'.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and 'category' in request.data:
            category_data = request.data.get('category')
            if isinstance(category_data, dict) and 'name' in category_data:
                category, _ = Category.objects.get_or_create(name=category_data['name'])
                validated_data['category'] = category
            else:
                raise serializers.ValidationError("Invalid category data. Must provide 'name'.")
        return super().update(instance, validated_data) 


class PaymentSerializer(serializers.ModelSerializer):
    template = TemplateSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'template', 'order_id', 'user_email', 'user_phone',
            'amount', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['order_id', 'status', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate_user_email(self, value):
        if '@' not in value:
            raise serializers.ValidationError("A valid email is required.")
        return value

class SupportInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportInquiry
        fields = [
            'inquiry_id', 'email', 'inquiry_type', 'description',
            'order_id', 'status', 'response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['inquiry_id', 'status', 'response', 'created_at', 'updated_at']

    def validate_email(self, value):
        if '@' not in value:
            raise serializers.ValidationError("A valid email address is required.")
        return value

    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value

    def validate_order_id(self, value):
        if value:
            if not Payment.objects.filter(order_id=value).exists():
                raise serializers.ValidationError("Invalid order ID. No payment found with this ID.")
        return value

    def validate_inquiry_type(self, value):
        valid_types = [choice[0] for choice in SupportInquiry.INQUIRY_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Inquiry type must be one of: {', '.join(valid_types)}.")
        return value