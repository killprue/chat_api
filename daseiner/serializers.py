from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from .tokens import account_activation_token
from django.utils.encoding import force_bytes
from rest_framework import serializers
from .models import Profile

class UserSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    class Meta:
        model = get_user_model() 
        fields = ('username', 'password', 'email', 'id')

    def create(self, validated_data):
        current_site = get_current_site(self.request)
        subject = 'Activate Your Daseiner Account'
        
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email']
        )
        profile = Profile.objects.create(user=user)
        message = render_to_string('emails/account_activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })

        user.email_user(subject, message)
        return user
