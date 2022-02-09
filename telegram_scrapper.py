
####################################################################################################
#        #####     ####    ##    #   ##    #   #   #
#        #    #   #    #   # #   #   # #   #    # #
#        #    #   ######   #  #  #   #  #  #     #
#        #    #   #    #   #   # #   #   # #     #
#        ####     #    #   #    ##   #    ##     #
####################################################################################################

import itertools
from getpass import getpass
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon import TelegramClient, sync
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from os import path, makedirs
import json


# Chat to inspect
CHAT_LINK = "https://t.me/chat_chop_chop"


# Connect and Log-in/Sign-in to telegram API
def tlg_connect():
	# Connect and Log-in/Sign-in to Telegram API
	# Request Sign-in code for first execution
	with open("tokens.json", "r") as rf:
		tokens = json.load(rf)
	all_clients = set()
	print('Trying to connect to Telegram...')
	for i, token in enumerate(tokens):
		client = TelegramClient(f"Session{i}", token.get("api_id"), token.get("api_hash"))
		if not client.start():
			print('Could not connect to Telegram servers.')
			return None
		else:
			if not client.is_user_authorized():
				print('Session file not found. This is the first run, sending code request...')
				client.sign_in(token.get("phone"))
				self_user = None
				while self_user is None:
					code = input('Enter the code you just received: ')
					try:
						self_user = client.sign_in(code=code)
					except SessionPasswordNeededError:
						pw = getpass('Two step verification is enabled. Please enter your password: ')
						self_user = client.sign_in(password=pw)
						if self_user is None:
							return None
		print('Sign in success.')
		all_clients.add(client)
	print()
	return itertools.cycle(all_clients)


# Get basic info from a chat
def tlg_get_basic_info(client, chat):
	chat_entity = client.get_entity(chat)
	num_members_offset = client(GetParticipantsRequest(channel=chat_entity,
													   filter=ChannelParticipantsSearch(''),
													   offset=0, limit=0, hash=0)).count
	num_members = client(GetParticipantsRequest(channel=chat_entity,
											    filter=ChannelParticipantsSearch(''),
											    offset=num_members_offset, limit=0, hash=0)).count
	msgs = client.get_messages(chat_entity, limit=1)
	basic_info = {
		"id": msgs[0].chat_id,
		"title": msgs[0].chat.title,
		"username": msgs[0].chat.username,
		"num_members": num_members,
		"num_messages": msgs.total,
		"supergroup": msgs[0].chat.megagroup
	}
	return basic_info


# Get all members data from a chat
def tlg_get_all_members(client, chat, external=False):
	chat_entity = client.get_entity(chat)
	i = 0
	members = []
	users = []
	num_members = client(GetParticipantsRequest(channel=chat_entity,
												filter=ChannelParticipantsSearch(''),
												offset=0, limit=0, hash=0)).count
	while True:
		participants_i = client(GetParticipantsRequest(channel=chat_entity,
													   filter=ChannelParticipantsSearch(''),
													   offset=i, limit=num_members, hash=0))
		if not participants_i.users:
			break
		users.extend(participants_i.users)
		i = i + len(participants_i.users)
	for i, usr in enumerate(users):
		if hasattr(usr.status, "was_online"):
			usr_last_connection = "{}/{}/{} - {}:{}:{}".format(usr.status.was_online.day,
				usr.status.was_online.month, usr.status.was_online.year,
				usr.status.was_online.hour, usr.status.was_online.minute,
				usr.status.was_online.second)
		else:
			usr_last_connection = "The user does not share this information"
		if external:
			phone = None
			about = None
			if usr.username:
				full_data = client(GetFullUserRequest("@" + usr.username))
				phone = full_data.user.phone
				about = full_data.about
			usr_data = {
				"id": usr.id,
				"username": usr.username,
				"first_name": usr.first_name,
				"last_name": usr.last_name,
				"phone": phone,
				"about": about,
				"last_connection": usr_last_connection
			}
			members.append(usr_data)
		else:
			usr_data = {
				"id": usr.id,
				"username": usr.username,
				"first_name": usr.first_name,
				"last_name": usr.last_name,
				"last_connection": usr_last_connection
			}
			members.append(usr_data)
	return members


# Get messages data from a chat
# num_msg = 0 => get all messages
def tlg_get_messages(client_generator, chat, num_msg=0):
	offset_id = 0
	limit = 100
	all_messages = []
	total_messages = 0
	total_count_limit = num_msg

	while True:
		print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
		history = next(client_generator)(GetHistoryRequest(
			peer=chat,
			offset_id=offset_id,
			offset_date=None,
			add_offset=0,
			limit=limit,
			max_id=0,
			min_id=0,
			hash=0
		))
		if not history.messages:
			break
		messages = history.messages
		for msg in messages:
			if msg.from_id.__class__.__name__ == 'PeerUser':
				msg_sender_id = msg.from_id.user_id
			else:
				msg_sender_id = msg.from_id.channel_id
			msg_sent_date = "{}/{}/{}".format(msg.date.day, msg.date.month, msg.date.year)
			msg_sent_time = "{}:{}:{}".format(msg.date.hour, msg.date.minute, msg.date.second)
			msg_data = {
				"id": msg.id,
				"text": msg.message,
				"sent_time": msg_sent_time,
				"sent_date": msg_sent_date,
				"sender_user_id": msg_sender_id,
				"reply_to": msg.reply_to.reply_to_msg_id if msg.reply_to else None
			}
			all_messages.append(msg_data)
		offset_id = messages[-1].id
		total_messages = len(all_messages)
		if total_count_limit != 0 and total_messages >= total_count_limit:
			break
	return all_messages[::-1]


# Json files handle functions
def json_write(file, data):
	directory = path.dirname(file)
	if not path.exists(directory):
		makedirs(directory)
	try:
		with open(file, 'w', encoding='utf-8') as outfile:
			json.dump(data, outfile, indent=4)
	except IOError as e:
		print("I/O error({0}): {1}".format(e.errno, e.strerror))
	except ValueError:
		print("Error: Can't convert data value to write in the file")
	except MemoryError:
		print("Error: You are trying to write too much data")

####################################################################################################


def main():
	print()
	client_generator = tlg_connect()
	if client_generator is not None:
		print('Getting chat basic info...')
		chat_info = tlg_get_basic_info(next(client_generator), CHAT_LINK)
		print('Done')

		if chat_info["username"]:
			files_name = chat_info["username"]
		else:
			files_name = chat_info["id"]
		fjson_chat = f"./output/{files_name}/chat.json"
		fjson_users = f"./output/{files_name}/users.json"
		fjson_messages = f"./output/{files_name}/messages.json"

		json_write(fjson_chat, chat_info)

		print('Getting chat members (users) info...')
		members = tlg_get_all_members(next(client_generator), CHAT_LINK)
		print('Done')
		json_write(fjson_users, members)

		print('Getting chat messages info...')
		messages = tlg_get_messages(client_generator, CHAT_LINK, 1000)
		print('Done')
		json_write(fjson_messages, messages)

		print('Proccess completed')
		print()

####################################################################################################


if __name__ == "__main__":
	main()
