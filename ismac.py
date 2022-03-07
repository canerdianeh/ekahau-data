#!/usr/bin/python3

import re

for sourceString in ['aa:bb:cc:dd:ee:ff', "AA-BB-CC-DD-EE-FF", "aaaa.bbbb.cccc", "This. is-not a : hex string"]:
	print("\n\nSource String: "+sourceString)
	isMac=False 
	delimiter=""
	# Let's Check to see if this is at least vaguely hexadecimal
	if '.' in sourceString:
		macMatch=re.match(r"^([0-9A-Fa-f]{4}[.]){2}([0-9A-Fa-f]{4})$", sourceString)
		if macMatch:
			isMac=True
			delimiter = '.'
			print(macMatch.group())
	if ':' in sourceString:
		macMatch=re.match(r"^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$", sourceString)
		if macMatch:
			isMac=True
			delimiter = ':'
			print(macMatch.group())
	if '-' in sourceString:
		macMatch=re.match(r"^([0-9A-Fa-f]{2}[-]){5}([0-9A-Fa-f]{2})$", sourceString)
		if macMatch:
			isMac=True
			delimiter = '-'
			print(macMatch.group())


	print (isMac)
	print("Delimiter: " + delimiter)

