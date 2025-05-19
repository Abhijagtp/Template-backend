from rest_framework import serializers
from .models import Category, Template, Review, Payment, SupportInquiry
import cloudinary
from cloudinary import CloudinaryImage

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
                # First, try to get the Cloudinary URL directly
                if hasattr(obj.image, 'url'):
                    image_url = obj.image.url
                    # Check if the URL is a full Cloudinary URL
                    if image_url.startswith('http'):
                        return image_url
                    # If it's a relative path, build the URL manually
                # Extract the public ID (remove the "templates/" prefix)
                public_id = str(obj.image).replace('templates/', '').replace('.jpg', '')
                return CloudinaryImage(public_id).build_url(secure=True)
            except Exception as e:
                print(f"Error generating Cloudinary URL for image {obj.image}: {str(e)}")
                return None
        return None

    def get_additional_images(self, obj):
        # additional_images is a JSONField containing a list of image paths (public IDs)
        if obj.additional_images:
            try:
                return [CloudinaryImage(image).build_url(secure=True) for image in obj.additional_images]
            except Exception as e:
                # Log the error for debugging
                print(f"Error building Cloudinary URLs for additional_images: {str(e)}")
                return []
        return []

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def create(self, validated_data):
        # Handle category creation if needed
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
        # Handle category update if needed
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