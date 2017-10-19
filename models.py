from config import price
from peewee import *

db = SqliteDatabase('db.sqlite3')

class BaseModel(Model):
	class Meta:
		database = db

class Routing(BaseModel):
	btn 	 	= TextField(unique = True) 
	action		= TextField(null = True)

	@staticmethod
	def clear_table():
		Routing.create_table(fail_silently = True)
		q = Routing.delete()
		q.execute()


class Btn():
	def __init__(self):
		self.free_signals 	= "Сигналы FREE"
		self.vip_signals	= "Сигналы VIP"
		self.my_wallet		= "Мой кошелёк"
		self.my_balance		= "Мой баланс"
		self.three_days 	= "3 дня за {} Btc".format(price['3_days'])
		self.one_week 		= "1 неделя за {} Btc".format(price['1_week'])
		self.two_weeks 		= "2 недели за {} Btc".format(price['2_weeks'])
		self.one_month 		= "1 месяц за {} Btc".format(price['1_month'])
		self.back 			= "Назад"

		self.set_routing()

	def set_routing(self):
		btns = self.__dict__
		Routing.clear_table()
		for b in btns:
			r = Routing.create(btn = btns[b], action = b)



#	BUTTONS



# CALLBACKS
# free_signals_clbck 	= "free_signals"
# vip_signals_clbck	= "vip_signals"
# my_balance_clbck	= "my_balance"
# my_wallet_clbck		= "my_wallet"
# one_day_clbck		= "one_day"
# three_days_clbck	= "three_days"	
# one_week_clbck		= "one_week"
# one_month_clbck		= "one_month"


class Msg():
	def __init__(self):
		self.start = '''
		Добро пожаловать!
		Вы переходите на VIP канал сигналов c криптовалютной биржи Bittrex. Канал ведут биржевые аналитики, анализируя массу информации от источников со всего мира,  дают рекомендации на какие валюты стоит обратить внимание, дают информацию о возможных пампах.. помогают начать зарабатывать и  наращивать количество Биткойна в вашем портфеле! По возникшим вопросам вы всегда можете обратится к администраторам канала. Мы работаем для вас 24 часа - 7 дней в неделю. Выберите дальнейшее действия:
		'''

		self.my_balance = '''
		Ваш баланс составляет {} BTC.
		Выберите нужный период. Для пополнения баланса выберите **Мой кошелёк**. 
		'''

		self.my_wallet = '''
		Адрес вашего кошелька ниже.
		Переведите необходимую сумму btc на этот кошелек. 
		ВНИМАНИЕ! Средства зачисляются спустя 3 подтверждения сети. 
		После получения подтверждений на вашем балансе отобразятся перечисленные средства. 
		Вам остается лишь выбрать необходимый период доступа к сервису! Ссылка придет автоматически!
		'''

		self.wallet_address = '```{}```'	

		self.free_signals = '''
		Добро пожаловать!
		Ознакомьтесь с результатами игры по сигналам группы за прошлый месяц:

		NXC 80%; BRK 107%; SNRG 70%; HKG 70%; GLD 70%; NEO168%; DAR 91%; QWARK 176%; XCP 85%; GCR 60%; THC 53%; XRP 62%; FLDC 77%; LSK 157%; QTUM 67%; MCO 102%; XVG 78%; KORE 330%; OMG 102%; PTOY 76%; NEO 73%; IOP 54%; ZEC 101%; ADX 117%; XLM 83%
		Присоединяйтесь к группе Профессионалов и наращивайте количество Биткойна на своем счету. 
		Ссылка: https://t.me/joinchat/Fxl6JkOKhf6kwLxnzCyJkg 
		'''

		self.vip_signals = '''
		Сервис по оплате доступа работает в ТЕСТовом режиме
		Пользуйтесь моментом, тестируйте VIP сигналы БЕСПЛАТНО!!!
		Ссылка: https://t.me/joinchat/Fxl6JkOKhf6kwLxnzCyJkg 
		'''

		self.access_to_chat = '''
		Пополните свой баланс на необходимое количество BTC и Вы получите доступ в чат
		'''

		self.repare = 'Оплата пока на ремонте. Скоро всё будет'

		self.select_action = 'Выберите действие:'

