from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, InviteCode, UserDeviceSession, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    is_telegram_connected = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'telegram_chat_id', 'is_telegram_connected', 'created_at')
        read_only_fields = ('id', 'telegram_chat_id', 'created_at')

    def get_is_telegram_connected(self, obj):
        return bool(obj.telegram_chat_id)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, min_length=3)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    invite_code = serializers.CharField(max_length=50, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_invite_code(self, value):
        try:
            invite = InviteCode.objects.get(code=value)
        except InviteCode.DoesNotExist:
            raise serializers.ValidationError('Invalid invitation code.')

        if not invite.is_valid():
            raise serializers.ValidationError('Invitation code is expired or maximum uses reached.')

        return invite

    @transaction.atomic
    def create(self, validated_data):
        invite_input = validated_data['invite_code']
        # Concurrency safety: Lock the invite code row during registration
        invite = InviteCode.objects.select_for_update().get(id=invite_input.id)
        if not invite.is_valid():
            raise serializers.ValidationError({'invite_code': 'Invitation code is expired or maximum uses reached.'})

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            invited_by=invite.created_by
        )
        # Update invitation code usage
        invite.uses_count += 1
        invite.used_by = user
        if invite.uses_count >= invite.max_uses:
            invite.is_active = False
        invite.save(update_fields=['uses_count', 'used_by', 'is_active'])

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Supports login by username or email
        user = authenticate(username=username, password=password)
        if not user:
            try:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj:
                    user = authenticate(username=user_obj.username, password=password)
            except Exception:
                pass

        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        if not user.is_active:
            raise serializers.ValidationError('User account is deactivated.')

        attrs['user'] = user
        return attrs


class UserDeviceSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserDeviceSession
        fields = ('id', 'device_name', 'ip_address', 'last_active_at', 'is_revoked', 'is_current', 'created_at')

    def get_is_current(self, obj):
        current_session_id = self.context.get('current_session_id')
        return str(obj.id) == str(current_session_id)


class InviteCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InviteCode
        fields = ('id', 'code', 'uses_count', 'max_uses', 'is_active', 'expires_at', 'created_at')
        read_only_fields = ('id', 'uses_count', 'created_at')


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = (
            'id',
            'category',
            'action',
            'description',
            'ip_address',
            'device_name',
            'status',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')
