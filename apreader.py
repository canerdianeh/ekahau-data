#!/usr/bin/python3

import requests
import argparse
import json
import csv
import sys
import warnings
import sys
import xmltodict
import datetime
import yaml
import zipfile
import pprint
from yaml.loader import FullLoader
from pathlib import Path

pp = pprint.PrettyPrinter(indent=2)
print("==================================================================")
with zipfile.ZipFile('test.esx', 'r') as ekahau:
	with ekahau.open('accessPointMeasurements.json', 'r') as apmjson :
		apmstring=apmjson.read()
		apmdict=json.loads(apmstring)
		#print(apmdict)
	with ekahau.open('accessPoints.json', 'r') as apjson :
		apstring=apjson.read()
		apdict=json.loads(apstring)
	with ekahau.open('measuredRadios.json', 'r') as radiojson :
		radiostring=radiojson.read()
		radiodict=json.loads(radiostring)

masterlist={}
for ap in apdict['accessPoints']:
	apid=ap['id']
	del ap['id']
	masterlist[apid]=ap

for radio in radiodict['measuredRadios']:
	radioid=radio['id']
	apid=radio['accessPointId']
	#del radio['accessPointId']
	radiobss={}
	#print(radio['accessPointMeasurementIds'])
	for bss in radio['accessPointMeasurementIds']:
		for measurement in apmdict['accessPointMeasurements']:
			#pp.pprint(measurement)
			if measurement['id'] == bss:
				radiomac=measurement['mac']
				del measurement['mac']
				radiobss.update({radiomac:measurement})
#pp.pprint(radiobss)
masterlist[apid]['radios']=radiobss

pp.pprint(masterlist)


for ap in masterlist.keys():
	rec=masterlist[ap]
	#pp.pprint(rec)
	mine="     "
	vendor=" (Unknown)"
	if 'vendor' in rec.keys():
		vendor=" ("+rec['vendor']+")"

	if rec['mine']: mine="(My) "
	print(mine+rec['name']+vendor)
#	for radio in rec['radios'].keys():
#	pp.pprint(rec)
#			if 'ssid' in radio:
#				ssid="  "+radio['ssid']+" "+radio['security']
#				phys='/'.join(radio['technologies'])
#				channels = '/'.join(radio['channel'])
#				tech="    "+rad['mac']+" - "+phys+" Ch. "+channels
#				print(ssid)
#				print(tech)



#print(type(apmdict))
#print(type(apdict))
#print(idlist.keys())

#for ap in apmdict['accessPointMeasurements']:

#	apid = ap['id']
#	if apid in idlist.keys():
#		print("found "+apid+" and assigned MAC address "+ap['mac'])
#	else:
#		print(apid+" not found in Measurements")
#
#	if ap['id'] == "750a00b0-5070-4219-bcca-8505b720913c":
#		print("match!")
#		print(idlist.get(apid))
	#apmac = idlist[apid]
	#print("AP "+name+" found with ID "+apid+" ("+apmac+")")
	#pp.pprint(idlist[apid])
#print(idlist["750a00b0-5070-4219-bcca-8505b720913c"])