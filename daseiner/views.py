from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, views, mixins
from rest_framework.response import Response
from .models import Room, Profile, ParticipantConnection, Question, JudgeConnection, ParticipantConnection, WaitingJudge
from django.contrib.auth.models import User
from django.db.models import Q
from . import serializers
from .tokens import account_activation_token
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponseRedirect
from rest_framework.exceptions import ValidationError
from django.conf import settings

class UserViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (permissions.AllowAny,)

class RoomValidationView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request, room_code):
        room_is_valid = False
        activated_date = None
        try:
            room_code_deconstructed = room_code.split('--')
            room_id = room_code_deconstructed[0]
            requesting_user = request.user.id
            requesting_user_type = int(room_code_deconstructed[1])
            query = Q(id=room_id)
            if requesting_user_type == 1:
                query.add(Q(participantconnection__user=requesting_user), Q.AND)
            else:
                query.add(Q(judgeconnection__user=requesting_user), Q.AND)
            room = Room.objects.filter(query)
            room_count = room.count()
            if room_count == 1:
                activated_date = room.get().activated_date
                room_is_valid = True if not room.get().termination_date else False
        except:
            room_is_valid = False
        finally:
            return Response({"isValid": room_is_valid, "activatedDate": activated_date})

class UserSettingsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        email_is_confirmed = False
        try:
            user = User.objects.get(pk=request.user.id)
            user_name = user.username
            if user:
                email_is_confirmed = user.profile.email_is_verified
            else:
                email_is_confirmed = False
            profile = Profile.objects.get(user=user)
            profile_pic = profile.profile_pic_url
            biography = profile.bio
            score = profile.upvote_score
        except:
            email_is_confirmed = False
        finally:
            return Response({
                "username":user_name,
                "isConfirmed": email_is_confirmed,
                "profilePicURL":profile_pic,
                "bio":biography,
                "upvoteScore":score
                })

class ActivateAccount(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            if user is not None and account_activation_token.check_token(user, token):
                user.profile.verify_email()
            return HttpResponseRedirect(redirect_to=settings.REDIRECT_URL)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            raise ValidationError

class ChatTurnView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, room_id):
        try:
            users_turn = None
            user_id = request.user.id
            user_connection = ParticipantConnection.objects.get(user=user_id, room=room_id)
            users_turn = user_connection.is_current_speaker
            return Response({"isUsersTurn": users_turn})
        except:
            raise ValidationError

class QuestionView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, room_id):
            room = Room.objects.get(id=room_id)
            question_title = room.question.title
            return Response({"question":question_title})

class CheckForMatchView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        room_info = {}
        has_match = False
        is_queued = False
        user = User.objects.get(pk=request.user.id)

        waiting_judge = WaitingJudge.objects.filter(user=user)
        queued_as_judge = waiting_judge.count() != 0
        participant = ParticipantConnection.objects.filter(user=user,room__is_open=True)
        queued_as_participant = participant.count() != 0

        if queued_as_judge:
            is_queued = True
            room_info['userType'] = 'judge'
        elif queued_as_participant:
            is_queued = True
            room_info['userType'] = 'participant'
        
        if not is_queued:
            judge_connection = JudgeConnection.objects.filter(
                user=user, 
                room__termination_date=None,
                room__is_open=False
            )

            if not judge_connection.count():
                participant_connection = ParticipantConnection.objects.filter(
                    user=user, 
                    room__termination_date=None,
                    room__is_open=False
                )

                if not participant_connection.count():
                    room_info = None
                else:
                    room_id = participant_connection[0].room.id
                    room = Room.objects.get(pk=room_id)
                    has_match = True
                    room_info['userType'] = 'participant'
                    room_info['activatedDate'] = room.activated_date
                    room_info['roomId'] = room.id
            else:
                room_id = judge_connection[0].room.id
                room = Room.objects.get(pk=room_id)
                has_match = True
                room_info['userType'] = 'judge'
                room_info['activatedDate'] = room.activated_date
                room_info['roomId'] = room.id


        return Response(
            {
                "roomInfo": room_info,
                "hasActiveMatch": has_match,
                "isQueued":is_queued
            }
        )
