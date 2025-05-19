# backend/views.py
import requests
import hmac
import hashlib
import base64
import time
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Category, Template, Review, Payment, SupportInquiry
from .serializers import CategorySerializer, TemplateSerializer, ReviewSerializer, PaymentSerializer, SupportInquirySerializer
from django.db.models import Q
import json
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import os 

# Set up logging
logger = logging.getLogger(__name__)

# Function to send email with Google Drive link
def send_template_email(payment):
    try:
        template = payment.template
        user_email = payment.user_email

        # Prepare email content using a template
        context = {
            'user_email': user_email,
            'template_title': template.title,
            'amount': payment.amount,
            'order_id': payment.order_id,
            'company_name': 'TemplateHub',  # Replace with your company name
            'support_email': 'support@templatehub.com',  # Replace with your support email
            'download_url': template.zip_file_url if template.zip_file_url else None,
        }
        email_subject = f'Your Template Purchase - {template.title}'
        email_body = render_to_string('email_template.html', context)

        # Create email message
        email = EmailMessage(
            subject=email_subject,
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        email.content_subtype = 'html'

        # Send the email
        email.send()
        logger.info(f"Email sent to {user_email} with download link for template {template.title}")

    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {str(e)}")

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category').prefetch_related('reviews')
        category_id = self.request.query_params.get('category')
        search_query = self.request.query_params.get('search')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )
        return queryset

    @action(detail=True, methods=['post'], url_path='initiate-payment')
    def initiate_payment(self, request, pk=None):
        logger.info(f"Starting initiate_payment for pk={pk}")
        try:
            template = self.get_object()
            user_email = request.data.get('email')
            user_phone = request.data.get('phone', '')

            logger.info(f"Template: {template.id}, Email: {user_email}, Phone: {user_phone}")

            if not user_email or '@' not in user_email:
                return Response({'error': 'A valid email is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create a payment record
            order_id = f"order_{template.id}_{int(timezone.now().timestamp())}"
            payment = Payment.objects.create(
                template=template,
                order_id=order_id,
                user_email=user_email,
                user_phone=user_phone,
                amount=template.price,
                status='PENDING'
            )
            logger.info(f"Payment created: {payment.id}, Amount: {template.price}")

            # Prepare Cashfree order payload
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')  # Use environment variable
            payload = {
                "order_id": order_id,
                "order_amount": float(template.price),
                "order_currency": "INR",
                "customer_details": {
                    "customer_id": f"cust_{user_email.split('@')[0]}",
                    "customer_email": user_email,
                    "customer_phone": user_phone or "9999999999",
                },
                "order_meta": {
                    "return_url": f"{frontend_url}/payment-status?order_id={order_id}",
                    "notify_url": os.getenv('WEBHOOK_URL', 'https://template-backend-4i5o.onrender.com/api/webhook/'),
                }
            }
            logger.info(f"Payload: {payload}")

            # Make API call to Cashfree
            headers = {
                "x-api-version": "2023-08-01",
                "x-client-id": settings.CASHFREE_APP_ID,
                "x-client-secret": settings.CASHFREE_SECRET_KEY,
                "Content-Type": "application/json",
            }
            logger.info(f"Headers (excluding secret): { {k: v for k, v in headers.items() if k != 'x-client-secret'} }")

            response = requests.post(
                f"{settings.CASHFREE_BASE_URL}/pg/orders",
                json=payload,
                headers=headers
            )
            logger.info(f"Cashfree Response Status: {response.status_code}")
            logger.info(f"Cashfree Response: {response.json()}")

            if response.status_code == 200:
                payment_data = response.json()
                payment_session_id = payment_data.get("payment_session_id")
                if not payment_session_id:
                    logger.error("No payment_session_id in Cashfree response")
                    return Response(
                        {'cashfree_error': 'Failed to generate payment session'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                payment.order_id = order_id
                payment.save()
                return Response({
                    'payment_session_id': payment_session_id,
                    'order_id': order_id
                }, status=status.HTTP_200_OK)
            else:
                payment.status = 'FAILED'
                payment.save()
                logger.error(f"Cashfree Error: {response.json()}")
                return Response({
                    'error': 'Failed to initiate payment.',
                    'cashfree_error': response.json().get('message', 'Unknown error')
                }, status=response.status_code)
        except Exception as e:
            logger.error(f"Error in initiate_payment: {str(e)}")
            return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    @action(detail=False, methods=['post'], url_path='submit')
    def submit_review(self, request):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            template = Template.objects.get(id=request.data['template'])
            template_serializer = TemplateSerializer(template)
            return Response({
                'review': serializer.data,
                'template': template_serializer.data
            }, status=201)
        return Response(serializer.errors, status=400)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def retrieve(self, request, pk=None):
        try:
            payment = Payment.objects.get(order_id=pk)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)


logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
@api_view(['POST'])
def payment_webhook(request):
    logger.info("Webhook endpoint reached")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request body: {request.body}")

    # Handle both 'event' and 'type' fields for compatibility
    event = request.data.get('type') or request.data.get('event')
    if not event:
        logger.error("No event or type specified in webhook payload")
        return Response({'error': 'No event or type specified'}, status=status.HTTP_400_BAD_REQUEST)

    order_id = request.data.get('data', {}).get('order', {}).get('order_id')
    if not order_id:
        logger.error("No order_id found in webhook payload")
        return Response({'error': 'No order_id found'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(order_id=order_id)
    except Payment.DoesNotExist:
        logger.error(f"Payment with order_id {order_id} not found")
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

    # Map Cashfree's webhook type to internal status
    if event == 'PAYMENT_SUCCESS_WEBHOOK':
        payment.status = 'SUCCESS'
        payment.save()
        logger.info(f"Updated payment status for order {order_id} to SUCCESS")
        send_template_email(payment)
    elif event in ['PAYMENT_FAILED_WEBHOOK', 'PAYMENT_CANCELLED_WEBHOOK']:
        payment.status = 'FAILED'
        payment.save()
        logger.info(f"Updated payment status for order {order_id} to FAILED")
    else:
        logger.warning(f"Unknown event type: {event}")
        return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

    return Response({'status': 'success'}, status=status.HTTP_200_OK)




def send_support_email(inquiry):
    try:
        # User confirmation email
        user_context = {
            'inquiry_id': inquiry.inquiry_id,
            'email': inquiry.email,
            'inquiry_type': inquiry.get_inquiry_type_display(),
            'description': inquiry.description,
            'order_id': inquiry.order_id or 'N/A',
            'company_name': 'TemplateHub',
            'support_email': 'support@templatehub.com',
        }
        user_email_body = render_to_string('support_confirmation.html', user_context)
        user_email = EmailMessage(
            subject=f'Your Support Inquiry - {inquiry.inquiry_id}',
            body=user_email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[inquiry.email],
        )
        user_email.content_subtype = 'html'
        user_email.send()
        logger.info(f"Confirmation email sent to {inquiry.email} for inquiry {inquiry.inquiry_id}")

        # Support team alert
        support_context = {
            'inquiry_id': inquiry.inquiry_id,
            'email': inquiry.email,
            'inquiry_type': inquiry.get_inquiry_type_display(),
            'description': inquiry.description,
            'order_id': inquiry.order_id or 'N/A',
            'company_name': 'TemplateHub',
        }
        support_email_body = render_to_string('support_alert.html', support_context)
        support_email = EmailMessage(
            subject=f'New Support Inquiry - {inquiry.inquiry_id}',
            body=support_email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['support@templatehub.com'],  # Configure in settings.py
        )
        support_email.content_subtype = 'html'
        support_email.send()
        logger.info(f"Support alert sent for inquiry {inquiry.inquiry_id}")

    except Exception as e:
        logger.error(f"Failed to send support emails for inquiry {inquiry.inquiry_id}: {str(e)}", exc_info=True)

def send_response_email(inquiry):
    try:
        context = {
            'inquiry_id': inquiry.inquiry_id,
            'email': inquiry.email,
            'inquiry_type': inquiry.get_inquiry_type_display(),
            'response': inquiry.response,
            'company_name': 'TemplateHub',
            'support_email': 'support@templatehub.com',
        }
        email_body = render_to_string('support_response.html', context)
        email = EmailMessage(
            subject=f'Update on Your Support Inquiry - {inquiry.inquiry_id}',
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[inquiry.email],
        )
        email.content_subtype = 'html'
        email.send()
        logger.info(f"Response email sent to {inquiry.email} for inquiry {inquiry.inquiry_id}")
    except Exception as e:
        logger.error(f"Failed to send response email for inquiry {inquiry.inquiry_id}: {str(e)}", exc_info=True)

class SupportInquiryViewSet(viewsets.ModelViewSet):
    queryset = SupportInquiry.objects.all()
    serializer_class = SupportInquirySerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            inquiry = serializer.save()
            send_support_email(inquiry)
            return Response({
                'inquiry_id': inquiry.inquiry_id,
                'message': 'Inquiry submitted successfully. You will receive a confirmation email.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='track')
    def track(self, request):
        inquiry_id = request.data.get('inquiry_id')
        email = request.data.get('email')
        if not inquiry_id or not email:
            return Response({'error': 'Inquiry ID and email are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            inquiry = SupportInquiry.objects.get(inquiry_id=inquiry_id, email=email)
            serializer = self.get_serializer(inquiry)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except SupportInquiry.DoesNotExist:
            return Response({'error': 'Inquiry not found or email does not match.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='respond')
    def respond(self, request, pk=None):
        inquiry = self.get_object()
        response_text = request.data.get('response')
        status_update = request.data.get('status', 'RESOLVED')
        if not response_text:
            return Response({'error': 'Response is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if status_update not in ['OPEN', 'IN_PROGRESS', 'RESOLVED']:
            return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        inquiry.response = response_text
        inquiry.status = status_update
        inquiry.save()
        send_response_email(inquiry)
        return Response({'message': 'Response saved and emailed to user.'}, status=status.HTTP_200_OK)