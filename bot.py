import sqlite3 as sqlite
import telebot
from multiprocessing import Process
from time import sleep
import re
import datetime
from telebot import types
from peewee import *
from playhouse.sqlite_ext import *
from playhouse.shortcuts import model_to_dict, dict_to_model # для сериализации peewee-объектов во время логирования ошибок
import config as cfg 
from config import price
from config import period
from block_io import BlockIo
import strings as s
from models import Btn, Msg, Routing


bot = telebot.TeleBot(cfg.token)
db = SqliteDatabase('db.sqlite3')

sid = lambda m: m.chat.id # лямбды для определения адреса ответа
uid = lambda m: m.from_user.id
cid = lambda c: c.message.chat.id

version = 2
block_io = BlockIo(cfg.key, cfg.pin, version)

msg = Msg() # это для строк. Сообщения и Кнопки.
# r = Routing()
btn = Btn()


class BaseModel(Model):
	class Meta:
		database = db


# class Routing(BaseModel):
# 	state 		= TextField()
# 	decision 	= TextField() # соответствует либо атрибуту data в инлайн кнопках, 
# 							  # либо специальному значению text, которое соответствует любому текстовому сообщению
# 	action		= TextField()

# 	def __init__(self, m):
# 		pass


# 	class Meta:
# 		primary_key = CompositeKey('state', 'decision')		

class User(BaseModel):
	user_id 	 = IntegerField(primary_key = True)
	username 	 = TextField(null = True)
	first_name   = TextField(null = True)
	last_name	 = TextField(null = True)
	state 		 = TextField(default = s.default)
	wallet		 = TextField(null = True)
	balance 	 = DoubleField(default = 0) 
	limit_date	 = DateTimeField(null = True)


	def cog(user_id, username = '', first_name = '', last_name = ''):
		try:
			with db.atomic():
				u = User.create(user_id = user_id, username = username, first_name = first_name, last_name = last_name)
				u.wallet = u.get_wallet()
				u.save()
				return u
		except Exception as e:
			return User.select().where(User.user_id == user_id).get()
				

	def new_wallet(self, user_id):
		return block_io.get_new_address(label = user_id)['data']['address']

	def get_wallet(self):
		if self.wallet is None:
			try:
				self.wallet = self.new_wallet(self.user_id)
			except:
				wallet = block_io.get_address_by_label(label = self.user_id)
				self.wallet = wallet['data']['address']
			self.save()
			return self.wallet
		else:
			return self.wallet

	def get_balance(self):
		return block_io.get_address_balance(label = self.user_id)['data']['available_balance']

	def write_off_money(self, price):
		if self.balance > price:
			self.balance -= price
			self.save()
			return True
		
		return False

	def access_to_chat(self, t):
		self.limit_date += period[t]
		self.save()
		




class Message(BaseModel):
	sender		= IntegerField()
	text 		= TextField()
	msg_type	= TextField()
	timestamp	= DateTimeField(default = datetime.datetime.utcnow)

class Error(BaseModel):
	message 	= TextField()
	state		= TextField()
	exception 	= TextField()
	timestamp	= DateTimeField(default = datetime.datetime.utcnow)

# functions
def get_default_keyboard():
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	three_days_btn = types.KeyboardButton(btn.three_days)
	one_week_btn = types.KeyboardButton(btn.one_week)
	two_weeks_btn = types.KeyboardButton(btn.two_weeks)
	one_month_btn = types.KeyboardButton(btn.one_month)
	my_wallet_btn = types.KeyboardButton(btn.my_wallet)
	my_balance_btn = types.KeyboardButton(btn.my_balance)
	back_btn = types.KeyboardButton(btn.back)
	keyboard.add(three_days_btn, one_week_btn)
	keyboard.add(two_weeks_btn, one_month_btn)
	keyboard.add(my_balance_btn)
	keyboard.add(my_wallet_btn)
	keyboard.add(back_btn)
	return keyboard

def get_access(u, t):
	if u.write_off_money(price[t]):
		u.access_to_chat(t)


# messages

def free_signals(u, m):
	bot.send_message(uid(m), msg.free_signals, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def vip_signals(u, m):
	bot.send_message(uid(m), msg.vip_signals, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def my_balance(u, m):
	bot.send_message(uid(m), msg.my_balance.format(u.get_balance()), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def my_wallet(u, m):
	bot.send_message(uid(m), msg.my_wallet, parse_mode = 'Markdown')
	bot.send_message(uid(m), msg.wallet_address.format(u.get_wallet()), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')

def three_days(u, m):
	bot.send_message(uid(m), msg.repare, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
	get_access(u, '3_days')

def one_week(u, m):
	bot.send_message(uid(m), msg.repare, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
	get_access(u, '1_week')

def two_weeks(u, m):
	get_access(u, '2_weeks')
	bot.send_message(uid(m), msg.repare, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')

def one_month(u, m):
	bot.send_message(uid(m), msg.repare, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
	get_access(u, '1_month')

def access(u, m):
	bot.send_message(uid(m), msg.access_to_chat, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')

def back(u,m):
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	free_signals_btn = types.KeyboardButton(btn.free_signals)
	vip_signals_btn = types.KeyboardButton(btn.vip_signals)
	my_balance_btn = types.KeyboardButton(btn.my_balance)
	my_wallet_btn = types.KeyboardButton(btn.my_wallet)
	keyboard.add(my_balance_btn)
	keyboard.add(my_wallet_btn)
	keyboard.add(free_signals_btn, vip_signals_btn)
	bot.send_message(uid(m), msg.select_action, reply_markup = keyboard, parse_mode = 'Markdown')	



# handlers

@bot.message_handler(commands = ['ping'])
def ping(m):
	bot.send_message(uid(m), "I'm alive")


@bot.message_handler(commands = ['init'])
def init(m):
	Routing.create_table(fail_silently = True)
	User.create_table(fail_silently = True)
	Message.create_table(fail_silently = True)
	Error.create_table(fail_silently = True)



@bot.message_handler(commands = ['start'])
def start(m):
	u = User.cog(uid(m), username = m.from_user.username, first_name = m.from_user.first_name, last_name = m.from_user.last_name)

	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	free_signals_btn = types.KeyboardButton(btn.free_signals)
	vip_signals_btn = types.KeyboardButton(btn.vip_signals)
	my_balance_btn = types.KeyboardButton(btn.my_balance)
	my_wallet_btn = types.KeyboardButton(btn.my_wallet)
	keyboard.add(my_balance_btn)
	keyboard.add(my_wallet_btn)
	keyboard.add(free_signals_btn, vip_signals_btn)
	bot.send_message(uid(m), msg.start, reply_markup = keyboard, parse_mode = "Markdown")
	



@bot.message_handler(content_types = ['text'])
def action(m):
	u = User.cog(uid(m), username = m.from_user.username, first_name = m.from_user.first_name, last_name = m.from_user.last_name)
	try:
		r = Routing.select(Routing.btn, Routing.action).where(Routing.btn == m.text).get()
		eval(r.action)(u, m)
	except Exception as e:
		print(e)
	# u = User.cog(user_id = uid(m))
	# bot.send_message(uid(m), msg.start, reply_markup = get_default_keyboard(), parse_mode = "Markdown")
	
	# Message.create(sender = uid(m), text = m.text, msg_type = "text")
	# try:
	# 	r = Routing.get(state = u.state, decision = 'text')
	# 	try: # на случай если action не определён в таблице роутинга
	# 		eval(r.action)(u = u, m = m)
	# 	except Exception as e:
	# 		Error.create(message = m.text, state = u.state, exception = e)
	# 		print(e)
	# 		print(m)
	# except Exception as e:
	# 	Error.create(message = m.text, state = u.state, exception = e)
	# 	print(e)


@bot.callback_query_handler(func=lambda call: True)
def clbck(c):
	print(c)
	return
	u = User.cog(user_id = cid(c))
	Message.create(sender = cid(c), text = c.data, msg_type = "clbck")
	try:
		r = Routing.get(state = u.state, decision = c.data)
		keyboard = types.ReplyKeyboardMarkup()
		bot.edit_message_reply_markup(chat_id = cid(c), message_id = c.message.message_id, reply_markup = keyboard)
		bot.answer_callback_query(callback_query_id = c.id, show_alert = True)

		try: # на случай если action не определён в таблице роутинга
			# print(u.state)
			# print(c.data)
			# print(r.action)
			eval(r.action)(u = u, c = c)
		except Exception as e:
			Error.create(message = c.data, state = u.state, exception = e)
			print(e)
			print(s.action_not_defined)
	except Exception as e:
		Error.create(message = c.data, state = u.state, exception = e)
		print(e)	



if __name__ == '__main__':
	bot.polling(none_stop=True)