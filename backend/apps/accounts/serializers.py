from rest_framework import serializers
from django.db import models, transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, InviteCode, UserDeviceSession, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    is_telegram_connected = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'telegram_chat_id',
            'is_telegram_connected',
            'preferred_language',
            'preferred_theme',
            'created_at'
        )
        read_only_fields = ('id', 'username', 'email', 'telegram_chat_id', 'created_at')

    def get_is_telegram_connected(self, obj):
        return bool(obj.telegram_chat_id)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, min_length=3)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    invite_code = serializers.CharField(max_length=50, write_only=True)

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_invite_code(self, value):
        try:
            invite = InviteCode.objects.get(code=value.strip())
        except InviteCode.DoesNotExist:
            raise serializers.ValidationError('Invalid invitation code.')

        if not invite.is_valid():
            raise serializers.ValidationError('Invitation code is expired or maximum uses reached.')

        return invite

    def validate(self, attrs):
        # Only check username/email uniqueness after invite_code is verified to prevent enumeration
        errors = {}
        if User.objects.filter(username__iexact=attrs['username']).exists():
            errors['username'] = ['This username is already taken.']
        if User.objects.filter(email__iexact=attrs['email']).exists():
            errors['email'] = ['This email is already registered.']
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

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
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        # Constant-time lookup: resolve username or email first, then execute PBKDF2 exactly once
        user_obj = User.objects.filter(
            models.Q(username__iexact=username) | models.Q(email__iexact=username)
        ).first()

        if user_obj:
            if not user_obj.is_active:
                if user_obj.check_password(password):
                    raise serializers.ValidationError('User account is deactivated.')
                raise serializers.ValidationError('Invalid username or password.')
            user = authenticate(username=user_obj.username, password=password)
        else:
            # Triggers Django's dummy password hasher once to equalize response time
            user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        try:
            django_validate_password(value, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class UserDeviceSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserDeviceSession
        fields = ('id', 'device_name', 'ip_address', 'last_active_at', 'is_revoked', 'is_current', 'created_at')

    def get_is_current(self, obj):
        current_session_id = self.context.get('current_session_id')
        return str(obj.id) == str(current_session_id)


class InviteCodeSerializer(serializers.ModelSerializer):
    used_by_username = serializers.CharField(source='used_by.username', read_only=True, default=None)

    class Meta:
        model = InviteCode
        fields = ('id', 'code', 'uses_count', 'max_uses', 'is_active', 'used_by_username', 'expires_at', 'created_at')
        read_only_fields = ('id', 'uses_count', 'max_uses', 'used_by_username', 'created_at')


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
