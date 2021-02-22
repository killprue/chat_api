from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(default=timezone.now,editable=False)
    title = models.CharField(max_length=500,default="")

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'question'

class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_open = models.BooleanField(default=True)
    create_date = models.DateTimeField(default=timezone.now, editable=False)
    activated_date = models.DateTimeField(default=None, blank=True, null=True)
    initial_connection_id = models.UUIDField(editable=False)
    termination_date = models.DateTimeField(default=None, blank=True, null=True)
    question = models.ForeignKey(Question, default=None,on_delete=models.CASCADE)

    def __str__(self):
        return f"Open: {self.is_open}"

    def set_room_match(self):
        self.is_open = False
        self.activated_date = timezone.now()
        self.save()

    def close_room(self):
        if not self.termination_date:
            self.termination_date = timezone.now()
            self.save()

    def remove_room(self):
        self.delete()

    class Meta:
        db_table = 'room'

class ParticipantConnection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    create_date = models.DateTimeField(default=timezone.now, editable=False)
    is_current_speaker = models.BooleanField(default=False)

    def __str__(self):
        return f"Room:{self.room.id} | User: {self.user.username}"
    
    def save(self, *args, **kwargs):
        participant_set_count = self.room.participantconnection_set.all().count()
        participant_connection_limit_met = True if participant_set_count == 2 else False

        existing_save = self.room.participantconnection_set.filter(room=self.room, user=self.user)
        is_exisisting_save = True if existing_save.count() == 1 else False

        if is_exisisting_save or not participant_connection_limit_met:
            super(ParticipantConnection, self).save(*args, **kwargs)
        else:
            return None
    
    class Meta:
        db_table = 'participant_connection'

class JudgeConnection(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args,**kwargs):
        judge_connection_limit_met = True if self.room.judgeconnection_set.all().count() == 5 else False
        existing_save = self.room.judgeconnection_set.filter(room=self.room, user=self.user)
        is_exisisting_save = True if existing_save.count() == 1 else False

        if is_exisisting_save or not judge_connection_limit_met:
            super(JudgeConnection, self).save(*args, **kwargs)
            return True
        else:
            return False

    def __str__(self):
        return f"Room:{self.room.id} | User: {self.user.username}"

    class Meta:
        db_table = 'judge_connection'

class ParticipantMessage(models.Model):
    participant_connection = models.ForeignKey(ParticipantConnection, on_delete=models.CASCADE)
    body = models.CharField(default='', max_length=2500)
    create_date = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.body

    class Meta:
        db_table = 'participant_message'

class JudgeMessage(models.Model):
    judge_connection = models.ForeignKey(JudgeConnection, on_delete=models.CASCADE)
    body = models.CharField(default='', max_length=1000)
    create_date = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.body

    class Meta:
        db_table = 'judge_message'

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic_url = models.CharField(max_length=1000, null=True, blank=True)
    bio = models.CharField(max_length=3000, null=True, blank=True)
    upvote_score = models.IntegerField(default=0)
    email_is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"User: {self.user.username} | Score: {self.upvote_score}"

    def verify_email(self):
        self.email_is_verified = True
        self.save()

    class Meta:
        db_table = 'profile'

class WaitingJudge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    group_name = models.CharField(max_length=500)
    create_date = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return str(self.create_date)

    def send_room_id(self, message):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
        self.group_name,
        {'type': 'room_id', 'room_id': str(message)}
    )

    class Meta:
        db_table = 'waiting_judge'
