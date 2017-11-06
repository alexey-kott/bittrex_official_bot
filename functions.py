import re

def is_invitation(m):
	return re.findall(r'(?<=\s)rl\w+(?=\s?)', m.text)

def calc_discount_by_invited(n):
	"""величина скидки в зависимости от кол-ва приглашённых
	"""
	if n >= 15:
		return 30
	elif n >= 10:
		return 20
	elif n >= 5:
		return 10
	elif n >= 2:
		return 5
	elif n >= 1:
		return 3
	else: 
		return 0
