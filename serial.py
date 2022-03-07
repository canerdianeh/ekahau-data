#!/usr/bin/python3 
import string
import random

countries=['CN','TH','VN','US','JP','MX','CZ']
cc=random.choice(countries)
cc+=''.join(random.choices(string.ascii_uppercase, k=4))
cc+=random.choice(string.digits)
cc+=''.join(random.choices(string.ascii_uppercase + string.digits,k=3))
print(cc)

