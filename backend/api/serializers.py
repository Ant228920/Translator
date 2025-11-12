from rest_framework import serializers
from .models import Translation, Payment
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator


class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name', 'token']
        extra_kwargs = {'password': {'write_only': True, 'required': True}}

    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key


    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Token.objects.create(user=user)  # Створюємо токен
        return user


class TranslationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Translation
        fields = '__all__'

    def validate(self, data):
        if data['source_lang'] == data['target_lang']:
            raise serializers.ValidationError("Source and target languages must be different")
        return data


class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'closed_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value
