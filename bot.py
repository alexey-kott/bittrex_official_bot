import locale
from time import sleep
import datetime
import re
from multiprocessing import Process

import sqlite3 as sqlite
import telebot
from telebot import types
from peewee import *
from playhouse.sqlite_ext import *
from playhouse.shortcuts import model_to_dict, dict_to_model # для сериализации peewee-объектов во время логирования ошибок
from block_io import BlockIo
from models import Btn, Msg, Routing, Message, Error # Msg -- тексты сообщений бота, Message -- для логирования всех сообщений, но это пока не работает
import pymorphy2
from hashlib import sha1

from functions import *
import strings as s
import config as cfg 
from config import price, period, admins, private_chat_id, private_chat_link


locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

bot = telebot.TeleBot(cfg.token)
db = SqliteDatabase('db.sqlite3')

morph = pymorphy2.MorphAnalyzer() # объект для морфологического преобразования слов

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



class User(BaseModel):
	user_id 	 = IntegerField(primary_key = True)
	username 	 = TextField(null = True)
	first_name   = TextField(null = True)
	last_name	 = TextField(null = True)
	state 		 = TextField(default = 'default')
	wallet		 = TextField(null = True)
	balance 	 = DoubleField(default = 0) 
	limit_date	 = DateTimeField(null = True)
	referal_link = TextField(null = True)
	refer_users  = IntegerField(default = 0)
	invited_user = IntegerField(default = 0)
	discount 	 = IntegerField(default = 0)


	def cog(m):
		username = m.from_user.username
		first_name = m.from_user.first_name
		last_name = m.from_user.last_name
		try:
			with db.atomic():
				u = User.create(user_id = uid(m), 
								username = username, 
								first_name = first_name, 
								last_name = last_name
								)
				u.wallet = u.get_wallet()
				u.referal_link = u.gen_referal()
				u.save()
				return u
		except Exception as e:
			return User.select().where(User.user_id == uid(m)).get()
			
				

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
		balance = block_io.get_address_balance(label = self.user_id)['data']['available_balance']
		self.balance = balance 
		self.save()
		return float(balance)

	def write_off_money(self, price):
		self.get_balance()
		discount = calc_discount_by_invited(self.refer_users)
		total = (100 - discount) * price / 100
		if float(self.balance) > float(price): 
			self.balance = self.get_balance()
			self.refer_users = 0
			r = block_io.withdraw_from_labels(amounts = total, from_labels = self.user_id, to_labels = 'default')
			print(r)
			self.save()
			return True
		
		return False

	def get_access(self, t):
		if self.write_off_money(price[t]):
			if self.limit_date == None:
				now = datetime.datetime.now()
				now = now.replace(microsecond = 0)
				self.limit_date = now
			self.limit_date += period[t]
			self.save()
			return True
		return False

	def kick_chat(self):
		self.limit_date = None
		self.save()
		bot.kick_chat_member(private_chat_id, self.user_id)

	def has_access(self):
		now = datetime.datetime.now()
		if self.limit_date == None:
			return False 
		elif now > self.limit_date:
			return False
		return True

	def gen_referal(self):
		user_id = str(self.user_id)
		user_id = user_id.encode('utf-8')
		user_id_hash = sha1(user_id).hexdigest()
		return "rl_{}".format(user_id_hash)

	@staticmethod
	def invite_from(m):
		rl_tokens = re.findall(r'(?<=\s)rl\w+(?=\s?)', m.text)
		if not rl_tokens:
			return 0
		rl_token = rl_tokens[0]
		invited_user = User.select().where(User.referal_link == rl_token).get()
		return invited_user.user_id

	def set_invited_user(self, user_id):
		if not self.invited_user:
			self.invited_user = user_id
			self.save()
			invited_user = User.get(User.user_id == user_id)
			# invited_user.refer_users = User.select(fn.Count(User.user_id)).where(User.invited_user == user_id).scalar()
			invited_user.refer_users += 1
			invited_user.discount = calc_discount_by_invited(invited_user.refer_users)
			invited_user.save()
			return True
		return False







# functions
def get_default_keyboard():
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	three_days_btn = types.KeyboardButton(btn.three_days)
	one_week_btn = types.KeyboardButton(btn.one_week)
	two_weeks_btn = types.KeyboardButton(btn.two_weeks)
	one_month_btn = types.KeyboardButton(btn.one_month)
	my_wallet_btn = types.KeyboardButton(btn.my_wallet)
	my_balance_btn = types.KeyboardButton(btn.my_balance)
	referal_btn = types.KeyboardButton(btn.referal)
	back_btn = types.KeyboardButton(btn.back)
	keyboard.add(three_days_btn, one_week_btn)
	keyboard.add(two_weeks_btn, one_month_btn)
	keyboard.add(my_balance_btn)
	keyboard.add(my_wallet_btn)
	keyboard.add(referal_btn)
	keyboard.add(back_btn)
	return keyboard




# messages

def free_signals(u, m):
	bot.send_message(uid(m), msg.free_signals, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def vip_signals(u, m):
	bot.send_message(uid(m), msg.vip_signals, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def my_balance(u, m):
	bot.send_message(uid(m), msg.my_balance.format(u.get_balance(), u.discount), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def my_wallet(u, m):
	bot.send_message(uid(m), msg.my_wallet, parse_mode = 'Markdown')
	bot.send_message(uid(m), msg.wallet_address.format(u.get_wallet()), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')




def three_days(u, m):
	if u.get_access('3_days'):
		block_datetime = u.limit_date
		d = block_datetime.strftime("%-d")
		m = morph.parse(block_datetime.strftime("%B"))[0].inflect({'gent'}).word
		t = block_datetime.strftime("%H:%m")
		bot.send_message(u.user_id, msg.access_granted.format(d, m, t), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
		bot.unban_chat_member(private_chat_id, u.user_id)
		bot.restrict_chat_member(private_chat_id, u.user_id, can_send_messages = False, can_send_media_messages=False, can_send_other_messages=False)
	else:
		bot.send_message(u.user_id, msg.not_enough_money, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def one_week(u, m):
	if u.get_access('1_week'):
		block_datetime = u.limit_date
		d = block_datetime.strftime("%-d")
		m = morph.parse(block_datetime.strftime("%B"))[0].inflect({'gent'}).word
		t = block_datetime.strftime("%H:%m")
		bot.send_message(u.user_id, msg.access_granted.format(d, m, t), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
		bot.unban_chat_member(private_chat_id, u.user_id)
		bot.restrict_chat_member(private_chat_id, u.user_id, can_send_messages = False, can_send_media_messages=False, can_send_other_messages=False)
	else:
		bot.send_message(u.user_id, msg.not_enough_money, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def two_weeks(u, m):
	if u.get_access('2_weeks'):
		block_datetime = u.limit_date
		d = block_datetime.strftime("%-d")
		m = morph.parse(block_datetime.strftime("%B"))[0].inflect({'gent'}).word
		t = block_datetime.strftime("%H:%m")
		bot.send_message(u.user_id, msg.access_granted.format(d, m, t), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
		bot.unban_chat_member(private_chat_id, u.user_id)
		bot.restrict_chat_member(private_chat_id, u.user_id, can_send_messages = False, can_send_media_messages=False, can_send_other_messages=False)
	else:
		bot.send_message(u.user_id, msg.not_enough_money, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def one_month(u, m):
	if u.get_access('1_month'):
		block_datetime = u.limit_date
		d = block_datetime.strftime("%-d")
		m = morph.parse(block_datetime.strftime("%B"))[0].inflect({'gent'}).word
		t = block_datetime.strftime("%H:%m")
		bot.send_message(u.user_id, msg.access_granted.format(d, m, t), reply_markup = get_default_keyboard(), parse_mode = 'Markdown')
		bot.unban_chat_member(private_chat_id, u.user_id)
		bot.restrict_chat_member(private_chat_id, u.user_id, can_send_messages = False, can_send_media_messages=False, can_send_other_messages=False)
	else:
		bot.send_message(u.user_id, msg.not_enough_money, reply_markup = get_default_keyboard(), parse_mode = 'Markdown')


def referal(u, m):
	bot.send_message(uid(m), msg.referal_manual, parse_mode = "Markdown")
	bot.send_message(uid(m), msg.referal_message.format(u.referal_link))




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
	u = User.cog(m)

	keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
	free_signals_btn = types.KeyboardButton(btn.free_signals)
	vip_signals_btn = types.KeyboardButton(btn.vip_signals)
	my_balance_btn = types.KeyboardButton(btn.my_balance)
	my_wallet_btn = types.KeyboardButton(btn.my_wallet)
	referal_btn = types.KeyboardButton(btn.referal)
	keyboard.add(my_balance_btn)
	keyboard.add(my_wallet_btn)
	keyboard.add(referal_btn)
	keyboard.add(free_signals_btn, vip_signals_btn)
	bot.send_message(uid(m), msg.start, reply_markup = keyboard, parse_mode = "Markdown")
	

@bot.message_handler(content_types = ['new_chat_members'])
def new_member(m):
	user_id = m.new_chat_member.id
	if user_id in admins:
		return True
	try:
		u = User.select().where(User.user_id == user_id).get()
		if not u.has_access():
			raise
	except:
		bot.kick_chat_member(private_chat_id, user_id)




@bot.message_handler(content_types = ['text'])
def action(m):
	# print(m.from_user.username)
	# print(m.text, end="\n\n")
	u = User.cog(m)
	if is_invitation(m):
		invited_user = User.get(User.user_id == User.invite_from(m))
		if u.set_invited_user(invited_user.user_id):
			bot.send_message(uid(m), msg.your_invited_user.format(invited_user.username), parse_mode = 'Markdown')
		else:
			bot.send_message(uid(m), msg.already_invited.format(invited_user.username), parse_mode = 'Markdown')
	try:
		r = Routing.select(Routing.btn, Routing.action).where(Routing.btn == m.text).get()
		eval(r.action)(u, m)
	except Exception as e:
		# print(e)
		pass
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

class Watcher:
	def __call__(self):
		while True:
			now = datetime.datetime.now()
			now = now.replace(microsecond = 0)
			try:
				for user in User.select():
					if user.limit_date == now:
						try:
							user.kick_chat()
							bot.send_message(user.user_id, msg.subscription_ended)
						except Exception as e:
							print(e)
			except:
				pass
			sleep(1)


if __name__ == '__main__':
	watcher = Watcher()
	w = Process(target = watcher)
	w.start()
	bot.polling(none_stop=True)
	# while True:
	# 	try:
	# 		bot.polling(none_stop=True)
	# 	except Exception as e:
	# 		print(e)
	# 		sleep(3.5)