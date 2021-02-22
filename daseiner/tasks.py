import celery
from celery import task
from daseiner_proj.celery import app
from celery.utils.log import get_task_logger
from daseiner.models import Room, ParticipantConnection
from django.db import close_old_connections
import time

logger = get_task_logger(__name__)

@app.task
def change_turns(room_id):
    close_old_connections()
    participant_connections = ParticipantConnection.objects.filter(room=room_id)
    participant_one = participant_connections[0]
    participant_two = participant_connections[1]
    room = Room.objects.get(pk=room_id)
    counter = 0
    while(counter <= 6 and not room.termination_date):
        close_old_connections()
        time.sleep(120)
        close_old_connections()
        participant_one.is_current_speaker = True if not participant_one.is_current_speaker else False
        participant_two.is_current_speaker = True if not participant_two.is_current_speaker else False
        participant_one.save()
        participant_two.save()
        counter += 1
