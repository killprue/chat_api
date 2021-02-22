from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from .models import ParticipantMessage, Room, ParticipantConnection, Question, JudgeConnection, WaitingJudge, JudgeMessage
from django.db import models
import celery
import random
import time
import datetime
import threading
import json

class ParticipantChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        current_user = await self.scope['user']
        self.current_user = current_user
        if not self.current_user.id:
            return
        else:
            try:
                self.room_name = self.scope['url_route']['kwargs']['room_name']
                self.participant_room_group_name = 'participant_chat_%s' % self.room_name
                self.judge_room_group_name = 'judge_chat_%s' % self.room_name
                await self.channel_layer.group_add(
                    self.participant_room_group_name,
                    self.channel_name
                )

                await self.accept()
            except Exception as e:
                raise e

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.participant_room_group_name,
            self.channel_name
        )

        await self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.commands[data['command']](self, data)

    async def format_messages(self, messages):
        jsonified_messages = await database_sync_to_async(self.populate_messages)(messages)
        return jsonified_messages

    def populate_messages(self, messages):
        result = []
        if messages.count() == 0:
            return
        elif messages.count() == 1:
            result = [self.message_to_json(messages[0])]
        else:
            for message in messages.order_by('create_date'):
                json_message = self.message_to_json(message)
                result.append(json_message)
        return result

    def message_to_json(self, message):
        return {
            'username': message.participant_connection.user.username,
            'content': message.body,
            'timestamp': str(message.create_date),
            'userid': message.participant_connection.user.id
        }

    async def fetch_messages(self, data):
        messages = await database_sync_to_async(ParticipantMessage.objects.filter)(participant_connection__room=data['room'])
        formated_messages = await self.format_messages(messages)
        content = {'contentType': 'fetched_messages', 'participantMessages': formated_messages}
        await self.send_fetched_message(content)

    async def new_messages(self, data):
        p_connection = await database_sync_to_async(ParticipantConnection.objects.get)(user=self.current_user, room=data['room'])
        message = ParticipantMessage(participant_connection=p_connection, body=data['messages'])
        await database_sync_to_async(message.save)()
        messages = await database_sync_to_async(ParticipantMessage.objects.filter)(participant_connection__room=data['room'])
        formated_messages = await self.format_messages(messages)
        await self.send_chat_message(formated_messages, self.participant_room_group_name)
        await self.send_chat_message(formated_messages, self.judge_room_group_name)

    async def terminate_match(self, data):
        room = await database_sync_to_async(Room.objects.get)(pk=data['room'])
        await database_sync_to_async(room.close_room)()
        await self.send_terminate_to_group(self.participant_room_group_name)
        await self.send_terminate_to_group(self.judge_room_group_name)

    async def send_chat_message(self, message, room_group_name):
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'chat_message',
                'data': {
                    'contentType': 'new_message',
                    'participantMessages': message
                }
            }
        )

    async def send_terminate_to_group(self, room_group_name):
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'terminate_notification',
                'data': {
                    'contentType': 'termination_notification',
                    'participantMessages': [
                        { 
                            'username': self.current_user.username,
                            'content': self.current_user.id,
                            'timestamp': str(datetime.datetime.now(datetime.timezone.utc)),
                            'userid': self.current_user.id
                        }
                    ] 
                }
            }
        )

    async def send_fetched_message(self, message):
        await self.send(text_data=json.dumps(message))

    async def chat_message(self, event):
        message = event['data']
        await self.send(text_data=json.dumps(message))

    async def terminate_notification(self, event):
        message = event['data']
        await self.send(text_data=json.dumps(message))

    commands = {
        'fetch_messages': fetch_messages,
        'new_messages': new_messages,
        'terminate_match': terminate_match
    }

class ParticipantMatchingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        current_user = await self.scope['user']
        self.current_user = current_user
        if not self.current_user.id:
            return
        else:
            self.current_user = current_user
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = 'participant_searching_%s' % self.room_name
            self.match_found = False
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        clean_up_room = False
        if not self.match_found:
            initial_room_connection = await database_sync_to_async(Room.objects.filter)(initial_connection_id=self.room_name)
            initial_connection_exists = await database_sync_to_async(initial_room_connection.exists)()
            if initial_connection_exists:
                room = await database_sync_to_async(initial_room_connection[:1].get)()
                if not room.activated_date:
                    clean_up_room = True
                
            if not initial_connection_exists:
                clean_up_room = True

            if clean_up_room:
                disconnected_room = await database_sync_to_async(Room.objects.get)(initial_connection_id=self.room_name)
                await database_sync_to_async(disconnected_room.remove_room)()

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.close()

    async def find_match(self, data):
        room_queryset = await database_sync_to_async(Room.objects.filter)(is_open=True)
        room_count = await database_sync_to_async(room_queryset.count)()
        if room_count == 0:
            first_user = self.current_user
            randomized_questions = await database_sync_to_async(Question.objects.order_by)("?")
            question = await database_sync_to_async(randomized_questions.first)()
            new_room = Room(initial_connection_id=self.room_name,question=question)
            await database_sync_to_async(new_room.save)()
            first_user_connection = ParticipantConnection(user=first_user, room=new_room, is_current_speaker=True)
            await database_sync_to_async(first_user_connection.save)()
        else:
            room = await database_sync_to_async(room_queryset.first)()
            match_made = await self.make_match(data, room)
            if match_made and room.is_open:
                await database_sync_to_async(room.set_room_match)()
                self.match_found = True
                await database_sync_to_async(celery.current_app.send_task)('daseiner.tasks.change_turns', (room.id,))
                await self.send_room_id(str(room.id), self.room_group_name)
                await self.send_room_id(str(room.id), f"participant_searching_{room.initial_connection_id}")
                await database_sync_to_async(self.add_judges_to_room)(room)
                
    def add_judges_to_room(self, room):
        queued_judges = WaitingJudge.objects.all()
        queued_judges_count = queued_judges.count()
        if queued_judges_count > 0:
            ordered_judges = queued_judges.order_by("create_date")
            for queued_judge in ordered_judges:
                new_connection = JudgeConnection(room=room, user=queued_judge.user).save()
                if new_connection:
                    queued_judge.send_room_id(str(room.id))
                    queued_judge.delete()


    async def make_match(self, data, open_room):
        second_user = self.current_user
        rooms_to_match = await database_sync_to_async(Room.objects.filter)(participantconnection__user=second_user, id=open_room.id)
        room_count = await database_sync_to_async(rooms_to_match.count)()
        if room_count != 0:
            return None
        else:
            second_user_connection = ParticipantConnection(user=second_user, room=open_room)
            await database_sync_to_async(second_user_connection.save)()
            return second_user_connection
            
    commands = {
        'find_match': find_match
    }
    
    async def room_id_to_json(self, message):
        return {
            'room_id':str(message)
        }

    async def send_room_id(self, room_id, group_name):
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'room_id',
                'room_id': str(room_id)
            }
        )

    async def room_id(self, event):
        await self.send(text_data=json.dumps(event['room_id']))

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.commands[data['command']](self, data)

class JudgeChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            current_user = await self.scope['user']
            self.current_user = current_user
            if not self.current_user.id:
                return
            else:
                self.room_name = self.scope['url_route']['kwargs']['room_name']
                self.judge_room_group_name = 'judge_chat_%s' % self.room_name

                await self.channel_layer.group_add(
                    self.judge_room_group_name,
                    self.channel_name
                )

                await self.accept()
        except Exception as e:
            raise e

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.judge_room_group_name,
            self.channel_name
        )
        await self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.commands[data['command']](self, data)

    def messages_to_json(self, messages, is_participant_message):
        result = []
        for message in messages:
            result.append(self.message_to_json(message, is_participant_message))
        return result

    def message_to_json(self, message, is_participant_message):
        username = ''
        userid = None
        if is_participant_message:
            username = message.participant_connection.user.username
            userid = message.participant_connection.user.id
        else :
            username = message.judge_connection.user.username
            userid = message.judge_connection.user.id

        return {
            'username':username,
            'content': message.body,
            'timestamp': str(message.create_date),
            'userid': userid
        }

    async def fetch_messages(self, data):
        judge_messages = await database_sync_to_async(self.get_judge_messages)(data)
        participant_messages = await database_sync_to_async(self.get_participant_messages)(data)
        await self.send_fetched_message(
            {
                'contentType': 'fetched_messages', 
                'judgeMessages': judge_messages,
                'participantMessages': participant_messages
            }
        )

    def get_participant_messages(self, data):
        participant_messages = ParticipantMessage.objects.filter(
            participant_connection__room=data['room']).order_by('create_date')

        if participant_messages.count() == 0:
            participant_messages = []
        elif participant_messages.count() == 1:
            participant_messages = [self.message_to_json(participant_messages[:1].get(), True)]
        else:
            participant_messages = self.messages_to_json(participant_messages, True)
        return participant_messages

    def get_judge_messages(self, data):
        judge_messages = JudgeMessage.objects.filter(
            judge_connection__room=data['room']).order_by('create_date')

        if judge_messages.count() == 0:
            judge_messages = []
        elif judge_messages.count() == 1:
            judge_messages = [self.message_to_json(judge_messages[:1].get(), False)]
        else:
            judge_messages = self.messages_to_json(judge_messages, False)
        return judge_messages


    async def new_messages(self, data):
        j_connection = await database_sync_to_async(JudgeConnection.objects.get)(user=self.current_user, room=data['room'])
        message = JudgeMessage(judge_connection=j_connection, body=data['messages'])
        await database_sync_to_async(message.save)()
        judge_messages = await database_sync_to_async(JudgeMessage.objects.filter)(judge_connection__room=data['room'])
        ordered_messages = await database_sync_to_async(judge_messages.order_by)('create_date')
        jsonified_messages = await database_sync_to_async(self.messages_to_json)(ordered_messages, False)
        await self.send_chat_message(jsonified_messages)

    async def send_chat_message(self, message):
        await self.channel_layer.group_send(
            self.judge_room_group_name,
            {
                'type': 'chat_message',
                'data': {
                    'contentType': 'new_message',
                    'judgeMessages': message
                }
            }
        )

    async def send_fetched_message(self, message):
        await self.send(text_data=json.dumps(message))

    async def chat_message(self, event):
        message = event['data']
        await self.send(text_data=json.dumps(message))

    async def terminate_notification(self, event):
        message = event['data']
        await self.send(text_data=json.dumps(message))

    commands = {
        'fetch_messages': fetch_messages,
        'new_messages': new_messages,
    }

class JudgeMatchingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_found = False
        current_user = await self.scope['user']
        self.current_user = current_user
        if not self.current_user.id:
            return
        else:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = 'judging_%s' % self.room_name
            self.waiting_judge_user = None
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.waiting_judge_user and not self.match_found:
            judge_waiting = await database_sync_to_async(WaitingJudge.objects.filter)(user=self.waiting_judge_user)
            judge_waiting_count = await database_sync_to_async(judge_waiting.count)()
            if judge_waiting_count != 0:
                await database_sync_to_async(judge_waiting.delete)()
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        await self.close()

    async def find_match(self, data):
        matchable_rooms = await database_sync_to_async(Room.objects.filter)(is_open=False, termination_date=None)
        matchable_rooms_count = await database_sync_to_async(matchable_rooms.count)()
        waiting_judge_queue = await database_sync_to_async(WaitingJudge.objects.filter)(user=self.current_user)
        waiting_judge_queue_count = await database_sync_to_async(waiting_judge_queue.count)() 
        not_queued = waiting_judge_queue_count == 0
        if not_queued:
            if matchable_rooms_count == 0:
                await database_sync_to_async(self.que_judge)()
            else:
                room  = await database_sync_to_async(self.find_room_for_judge)(matchable_rooms)
                if self.match_found:
                    await database_sync_to_async(room.save)()
                    await self.send_room_id(room.id, self.room_group_name)
                else:
                    await database_sync_to_async(self.que_judge)()

    def que_judge(self):
        waiting_judge = WaitingJudge(user=self.current_user, group_name=self.room_group_name)
        self.waiting_judge_user = self.current_user
        waiting_judge.save()
    
    def find_room_for_judge(self, matchable_rooms):
        room = None
        for room in matchable_rooms:
            duplicate_connection = JudgeConnection.objects.filter(room=room,user=self.current_user).count() != 0
            connected_as_participant = ParticipantConnection.objects.filter(room=room,user=self.current_user).count() != 0
            if not duplicate_connection and not connected_as_participant:
                new_judge_connection = JudgeConnection(room=room,user=self.current_user).save()
                if new_judge_connection:
                    self.match_found = True
                    room = Room.objects.get(pk=str(room.id))
                    break
        return room

    async def send_room_id(self, room_id, group_name):
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'room_id',
                'room_id': str(room_id)
            }
        )
    
    async def room_id(self, event):
        await self.send(text_data=json.dumps(event['room_id']))
    

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.commands[data['command']](self, data)

    commands = {
        'find_match': find_match
    }
