import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import User, Translation, Payment
from .serializers import UserSerializer
from rest_framework.permissions import IsAdminUser
from django.conf import settings
import deepl
import json
import pandas as pd
from django.http import JsonResponse
from .services.email import send_translation_email
import logging
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)
from .services.wayforpay import WayForPay
from datetime import datetime
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView


class GoogleAuthView(APIView):
    def post(self, request):
        try:
            # 1. Отримуємо credential (JWT) від клієнта
            credential = request.data.get('credential')  # Зверніть увагу - тепер 'credential'
            if not credential:
                return Response({'error': 'Google credential is required'}, status=400)

            # 2. Відправляємо запит до Google для перевірки
            google_response = requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': credential}
            )

            # 3. Перевіряємо відповідь
            if google_response.status_code != 200:
                error_detail = f"Google API error: {google_response.status_code}"
                if google_response.text:
                    error_detail += f" - {google_response.text}"
                return Response({'error': error_detail}, status=400)

            user_data = google_response.json()

            # 4. Перевіряємо обов'язкові поля
            if 'email' not in user_data:
                return Response({'error': 'Email not provided by Google'}, status=400)

            # 5. Обробка користувача
            User = get_user_model()
            email = user_data['email']

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': user_data.get('given_name', ''),
                    'last_name': user_data.get('family_name', '')
                }
            )

            # 6. Створюємо/оновлюємо токен
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': {
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)

class TranslationCreateView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        try:
            with transaction.atomic():
                # Отримуємо дані з запиту
                source_text = request.data.get('text')
                source_lang = request.data.get('source_lang', 'EN')
                target_lang = request.data.get('target_lang', 'UK')
                user_id = request.data.get('user_id')
                email = request.data.get('email')

                # Перевірка обов’язкових полів
                if not source_text or not user_id:
                    return Response(
                        {"error": "Необхідні поля 'text' та 'user_id'"},
                        status=400
                    )

                # Отримуємо користувача
                user = User.objects.get(id=user_id)

                translator = deepl.Translator(settings.DEEPL_API_KEY)
                result = translator.translate_text(
                    source_text,
                    target_lang=target_lang.upper(),
                    source_lang=source_lang.upper() if source_lang else None
                )

                # Зберігаємо результат переклад

                # Створюємо переклад
                translation = Translation.objects.create(
                    user=user,
                    source_text=source_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    translated_text=result.text,
                )

                if email:
                    send_translation_email(
                        to_email=email,
                        source_text=translation.source_text,
                        source_lang=translation.source_lang,
                        target_lang=translation.target_lang,
                        translated_text=translation.translated_text
                    )
                    logger.info(f"Translation email sent to {email}")

                # Повертаємо результат без оплати
                return Response({
                    "translation_id": translation.id,
                    "message": "Переклад успішно створено (без оплати)"
                }, status=201)

        except User.DoesNotExist:
            return Response({"error": "Користувача не знайдено"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def get_user(request):
    user = request.user
    return user

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def accept_callback(request):
    try:
        raw_data = next(iter(request.data.keys()), '{}')
        data = json.loads(raw_data)
        now = datetime.now()

        logger.info(f"Received callback data: {data}")

        if data.get("reasonCode") == 1100:
            try:
                # Отримуємо дані платежу
                order_reference = data.get("orderReference")
                payment = Payment.objects.get(external_id=order_reference)

                # Перевіряємо чи платіж не був оброблений раніше
                if payment.status == 'completed':
                    logger.info(f"Payment {order_reference} already processed")
                    return JsonResponse({"status": "already processed"})

                # Оновлюємо статус платежу
                payment.status = 'completed'
                payment.closed_at = now
                payment.save()

                # Отримуємо та виконуємо переклад
                try:
                    translation = Translation.objects.get(payment=payment)

                    # Виконуємо переклад
                    translator = deepl.Translator(settings.DEEPL_API_KEY)
                    result = translator.translate_text(
                        translation.source_text,
                        target_lang=translation.target_lang.upper(),
                        source_lang=translation.source_lang.upper() if translation.source_lang else None
                    )

                    # Зберігаємо результат перекладу
                    translation.translated_text = result.text
                    translation.save()

                    # Відправляємо email з результатом
                    if data.get("email"):
                        send_translation_email(
                            to_email=data["email"],
                            source_text=translation.source_text,
                            source_lang=translation.source_lang,
                            target_lang=translation.target_lang,
                            translated_text=translation.translated_text
                        )
                        logger.info(f"Translation email sent to {data['email']}")

                except Translation.DoesNotExist:
                    logger.error(f"Translation not found for payment {order_reference}")
                except Exception as e:
                    logger.error(f"Translation error: {str(e)}")

            except Payment.DoesNotExist:
                logger.error(f"Payment not found: {order_reference}")
        else:
            # Неуспішний платіж
            order_reference = data.get("orderReference")
            try:
                payment = Payment.objects.get(external_id=order_reference)
                payment.status = 'failed'
                payment.closed_at = now
                payment.save()
            except Payment.DoesNotExist:
                logger.error(f"Payment not found: {order_reference}")

        # Формуємо відповідь для WayForPay
        answer = {
            "orderReference": data.get("orderReference", ""),
            "status": "accept",
            "time": int(now.timestamp())
        }

        # Додаємо підпис
        answer["signature"] = WayForPay.get_answer_signature(
            settings.WAYFORPAY_SECRET_KEY,
            answer
        )

        logger.info(f"Sending response to WayForPay: {answer}")
        return JsonResponse(answer)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET', 'POST'])  # Додаємо POST
@permission_classes([AllowAny])
def success_payment(request):
    # Перевіряємо дані з обох типів запитів
    order_id = request.GET.get('orderReference') or request.POST.get('orderReference') or request.data.get('orderReference')
    if not order_id:
        return JsonResponse({"error": "Відсутній orderReference"}, status=400)

    try:
        payment = Payment.objects.get(external_id=order_id)
        translation = Translation.objects.get(payment=payment)

        return JsonResponse({
            "status": payment.status,
            "order_id": order_id,
            "translation_id": translation.id
        })
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Платіж не знайдено"}, status=404)
    except Translation.DoesNotExist:
        return JsonResponse({"error": "Переклад не знайдено"}, status=404)

@api_view(['GET', 'POST'])  # Додаємо POST
@permission_classes([AllowAny])
def me(request):
    user = request.user
    return Response({'id': user.id, 'username': user.username, 'email': user.email})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)
    
    user = User.objects.all()




class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,  # додаємо тут
            }
        })



class StatsView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    def list(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Forbidden"}, status=403)

        # Отримуємо дані через ORM
        payments = Payment.objects.all().values()
        translations = Translation.objects.all().values()
        users = User.objects.all().values()

        # Конвертуємо в DataFrame
        df_payments = pd.DataFrame.from_records(payments)
        df_translations = pd.DataFrame.from_records(translations)
        df_users = pd.DataFrame.from_records(users)

        # Основна статистика
        stats = {
            "total_translations": len(df_translations),
            "total_revenue": df_payments[df_payments['status'] == 'completed']['amount'].sum(),
            "avg_order_value": df_payments[df_payments['status'] == 'completed']['amount'].mean(),
            "total_users": len(df_users),
            "active_users": df_translations['user_id'].nunique()
        }

        # Фільтрація даних (приклад)
        filtered_data = request.GET.get('filter')
        if filtered_data:
            df_payments = df_payments.query(filtered_data)

        # Сортування (приклад)
        sort_by = request.GET.get('sort', '-created_at')
        df_payments = df_payments.sort_values(sort_by.replace('-', ''), ascending=sort_by.startswith('-'))

        # Додаткові дані для таблиці
        stats['payments_data'] = df_payments.to_dict('records')

        return Response(stats)

