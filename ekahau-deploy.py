#!/usr/bin/env python3

# This script allows you to generate a CSV report of all surveyed APs in an Ekahau data file. Does not currently report on planned APs.  
# (c) 2022 Ian Beyer - Ekahau table load based on code by Blake Krone - basic stuff, but he wrote it and I didn't, so credit where it's due. 

import argparse
import zipfile
import json
import pathlib
import tempfile
import zlib
import os
import pprint
import csv
import random
import re
import string
import pandas as pd

pp = pprint.PrettyPrinter(indent=3)


def macAnon(sourceMac, laa=False, oui=False, delim=':'):
	anonyMac=[]
	macChunks=sourceMac.split(':')
	for x in range(6):
		a=random.randint(0,255)
		if laa and x == 0:  	# Only first Octet if making LAA compliant
			a |= (1<<1)			# Set second bit to 1
			a &= ~(1<<0)		# Set first bit (LSB) to 0
		hex = '%02x' % a
		anonyMac.append(hex)
	if oui :
		for octet in range(2):
			anonyMac[octet]=macChunks[octet]

	if delim == '.':
		anonymizedMac=anonyMac[0]+anonyMac[1]+'.'+anonyMac[2]+anonyMac[3]+'.'+anonyMac[4]+anonyMac[5] 
	else:
		anonymizedMac=delim.join(anonyMac)
	return anonymizedMac

def serAnon():
	countries=['CN','TH','VN','US','JP','MX','CZ']
	cc=random.choice(countries)
	cc+=''.join(random.choices(string.ascii_uppercase, k=4))
	cc+=random.choice(string.digits)
	cc+=''.join(random.choices(string.ascii_uppercase + string.digits,k=3))
	return cc



def isThisAMac(sourceString):
		isMac=False
		delimiter=""
		if '.' in sourceString:
			macMatch=re.match(r"^([0-9A-Fa-f]{4}[.]){2}([0-9A-Fa-f]{4})$", sourceString)
			if macMatch:
				isMac=True
				delimiter = '.'
		if ':' in sourceString:
			macMatch=re.match(r"^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$", sourceString)
			if macMatch:
				isMac=True
				delimiter = ':'
		if '-' in sourceString:
			macMatch=re.match(r"^([0-9A-Fa-f]{2}[-]){5}([0-9A-Fa-f]{2})$", sourceString)
			if macMatch:
				isMac=True
				delimiter = '-'

		if isMac :
			return True, macMatch.group(), delimiter
		else:
			return False, None, None

def isThisArubaSerial(sourceString):
		isArubaSerial=False

		serMatch=re.match(r"^([A-Z]{2})([A-Z]{4})([0-9A-Z]{4})$", sourceString)
		if serMatch:
			isArubaSerial=True
			return True, serMatch.group()
		else:
			return False, None


def main():

	defaultfile="ekahau_ap_report.csv"

	cli=argparse.ArgumentParser(description='Generate CSV report of all APs in an Ekahau survey file')

	cli.add_argument("-o", "--output", required=False, help='Output File', default=defaultfile)
	cli.add_argument("-i", "--input", required=True, help='Input File')
	cli.add_argument("-a", '--anonymize-macs', required=False, action="store_true", help="anonymize MACs")
	cli.add_argument("-p", '--preserve-oui', required=False, action="store_true", help="preserve OUIs when anonymizing MACs")
	cli.add_argument("-l", '--laa-macs', required=False, action="store_true", help="anonymized MACs are LAA compliant")
	cli.add_argument("-s", '--anonymize-serials', required=False, action="store_true", help="anonymize Aruba serial numbers")


	args = vars(cli.parse_args())
	pp.pprint(args)

	#Load Ekahau Project archive

	orig_archive = zipfile.ZipFile(args['input'],'r')

	ap_data_by_bssid = {}
	ap_data_by_id = {}

	# Define Color Values - each dict entry is a scheme. 

	colors={
		'Ekahau': {
			'Yellow': '#FFE600',
			'Orange': '#FF8500',
			'Red': '#FF0000',
			'Pink': '#FF00FF',
			'Violet': '#C297FF',
			'Blue': '#0068FF',
			'Gray': '#6D6D6D'
		},
		'Aruba':{	
			'Orange': '#FF8300',
			'White': '#FFFFFF',
			'Gray': '#646569',
			'Dark Blue': '#0F3250',
			'Blood Orange': '#FF5F4B',
			'Light Blue': '#ADE1F0'
		},
		'Custom':{}
	}
	
	simData = False
	measData = False
	tagData = False

	print("==========")
	# Load Metadata
	workingFile='project.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+" (Metadata) ...")
		with orig_archive.open(workingFile) as json_file:
			metaJSON = json.load(json_file)
			json_file.close()
	else:
		print(workingFile+" not found in archive. File is probably corrupt. Exiting. ")
		exit()

	print("==========")
	# Load Tag Keys Table
	workingFile='tagKeys.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			tagKeysJSON = json.load(json_file)
			json_file.close()
		tagKeysDF=pd.DataFrame(tagKeysJSON['tagKeys'])		
		tagKeysDF.drop(columns=['status'])
		tagData = True

	else:
		print(workingFile+" not found in archive. Skipping. ")
		tagKeysDF=pd.DataFrame()
		tagData = False


	print("==========")
	# Load Notes
	workingFile='notes.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			notesJSON = json.load(json_file)
			json_file.close()
		notesDF=pd.DataFrame(notesJSON['notes'])
		notesDF.set_index('id')

	else:
		print(workingFile+" not found in archive. Skipping. ")
		notesDF=pd.DataFrame()

	print("==========")
	# Load AP Table (This includes both measured and simulated)
	workingFile='accessPoints.json'
	tagnameList=[]
	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			accessPointsJSON = json.load(json_file)
			json_file.close()
		accessPointsDF=pd.DataFrame(accessPointsJSON['accessPoints'])
		accessPointsDF=accessPointsDF.join(pd.json_normalize(accessPointsDF.location))
		# Extract Tags list by AP ID for further processing
		apTagsRawDF=accessPointsDF[['id','tags']]

		accessPointsDF.drop(columns=['location','tags','status'], inplace=True)
		accessPointsDF.rename(columns={'id':'ap_id','name':'ap_name'}, inplace=True)

		apTagsListDF=pd.DataFrame()
		
		for row in apTagsRawDF.iterrows():
			taglist=row[1][1]
			df_dict={'accessPointId' : row[1][0]}
			for tag in row[1][1]:
				tagrec=tagKeysDF.loc[tagKeysDF["id"]==tag['tagKeyId']]
				tagname='tag_'+tagrec.key.values[0].replace(" ","_")
				if tagname not in tagnameList : tagnameList.append(tagname)
				df_dict[tagname]=tag['value']
			tmp_df = pd.DataFrame(df_dict, index=[0])

			apTagsListDF = apTagsListDF._append(tmp_df) # append the tmp_df to our final df

		apTagsListDF.reset_index(drop=True)  # Reset the final DF index sinze we assign index 0 to each tmp df

	else:
		print(workingFile+" not found in archive. Skipping. ")
		accessPointsDF=pd.DataFrame()

	accessPointsDF.to_csv(path_or_buf='aps.csv')


	print("==========")
	# Load Radios Table
	workingFile='measuredRadios.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			measuredRadiosJSON = json.load(json_file)
			json_file.close()		
		measuredRadiosDF=pd.DataFrame(measuredRadiosJSON['measuredRadios'])
		measuredRadiosDF.set_index('id')
		measData = True
	else:
		print(workingFile+" not found in archive. Skipping. ")
		measuredRadiosDF=pd.DataFrame()
		measData = False


	print("==========")
	# Load Antennas
	workingFile="antennaTypes.json"

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			antennasJSON = json.load(json_file)
			json_file.close()
		antennasDF=pd.DataFrame(antennasJSON['antennaTypes'])
		antennasDF.set_index('id')
	else:
		print(workingFile+" not found in archive. Skipping. ")
		antennasDF=pd.DataFrame()

	print("==========")
	
	if measData ==True:

		# Load Measurements Table
		workingFile='accessPointMeasurements.json'

		if workingFile in orig_archive.namelist():
			print ("Loading "+workingFile+"...")
			with orig_archive.open(workingFile) as json_file:
				accessPointMeasurementsJSON = json.load(json_file)
				json_file.close()		
			apMeasurementsDF=pd.DataFrame(accessPointMeasurementsJSON['accessPointMeasurements'])
			apMeasurementsDF.set_index('id')
		else:
			print(workingFile+" not found in archive. Skipping. ")
			apMeasurementsDF=pd.DataFrame()
	else:
		print("Measured Radios not found, skipping measurements")
	# end conditional

	print("==========")
	# Load Floor Plans Table
	workingFile='floorPlans.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			floorPlansJSON = json.load(json_file)
			json_file.close()
		floorPlansDF=pd.DataFrame(floorPlansJSON['floorPlans'])		
		floorPlansDF.set_index('id')
	else:
		print(workingFile+" not found in archive. Skipping. ")
		floorPlansDF=pd.DataFrame()

	print("==========")
	# Load Buildings Table
	workingFile='buildings.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			buildingsJSON = json.load(json_file)
			json_file.close()
		buildingsDF=pd.DataFrame(buildingsJSON['buildings'])
		buildingsDF.set_index('id')
	else:
		print(workingFile+" not found in archive. Skipping. ")
		buildingsDF=pd.DataFrame()

	print("==========")
	# Load Buildings Table
	workingFile='buildingFloors.json'
	building = False
	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			buildingFloorsJSON = json.load(json_file)
			json_file.close()
		buildingFloorsDF=pd.DataFrame(buildingFloorsJSON['buildingFloors'])
		buildingFloorsDF.set_index('id')
		building = True
	else:
		print(workingFile+" not found in archive. Skipping. ")
		buildingFloorsDF=pd.DataFrame()

	print("==========")
	# Load Simulated APs Table
	workingFile='simulatedRadios.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			simRadiosJSON = json.load(json_file)
			json_file.close()

		simRadiosDF=pd.DataFrame(simRadiosJSON['simulatedRadios'])		
		simRadiosDF.set_index('id')
		#simRadiosDF=simRadiosDF.join(pd.json_normalize(simRadiosDF.defaultAntennas))
		#simRadiosDF.drop(columns='defaultAntennas', inplace=True)
		simData=True
	else:
		print(workingFile+" not found in archive. Skipping. ")
		simRadiosDF=pd.DataFrame()
		simData=False

	print("==========")



	# Close input file, we are done with it and don't need open files aimlessly hanging around. 
	orig_archive.close()

	print("\nNotes:")
	print(notesDF)
	print("\nAccess Points:")
	print(accessPointsDF)
	print("\nMeasured Radios:")
	print(measuredRadiosDF)
	print("\nAntennas:")
	print(antennasDF)
	print("\nAP Measurements:")
	#print(apMeasurementsDF)
	print("\nTag Keys:")
	print(tagKeysDF)
	print("\nFloor Plans:")
	print(floorPlansDF)
	print("\nBuildings:")
	print(buildingsDF)
	print("\nBuilding Floors:")
	print(buildingFloorsDF)
	print("\nSimulated Radios:")
	print(simRadiosDF)

	if tagData == True:
		# Add Tags to AP List
		accessPointsDF=pd.merge(accessPointsDF, apTagsListDF, left_on='ap_id', right_on='accessPointId',how='left')
		accessPointsDF.drop(columns=['accessPointId'], inplace=True)
		accessPointsDF.to_csv(path_or_buf='aps.csv')
	# end tag data conditional block

	# Extrapolate building data
	if building == True:
		accessPointsDF=pd.merge(accessPointsDF, buildingFloorsDF[['floorPlanId','buildingId']], on='floorPlanId')
		accessPointsDF=pd.merge(accessPointsDF, buildingsDF[['name','id']], left_on='buildingId', right_on='id',suffixes=(None,"_bldg"))
	accessPointsDF=pd.merge(accessPointsDF, floorPlansDF[['name','id']], left_on='floorPlanId', right_on='id', suffixes=(None,"_floor"))
	if building== True: 
		accessPointsDF.drop(columns=['floorPlanId','buildingId','id_floor','id'], inplace=True)
		accessPointsDF.rename(columns={'name':'building','name_floor':'floor'}, inplace=True)
	accessPointsDF.to_csv(path_or_buf='aps.csv')

	# Break out the radios

	# First, simulated radios
	if simData == True: 

		simRadiosDF.drop(columns=['defaultAntennas','status'])
		simRadiosDF=pd.merge(simRadiosDF, accessPointsDF[['ap_id','ap_name',]],left_on='accessPointId', right_on='ap_id', how='left')

		simRadioWifi=simRadiosDF.query('radioTechnology == "IEEE802_11"')
		simRadioWifi.to_csv(path_or_buf='simRadiosWiFi.csv')

		simRadioBLE=simRadiosDF.query('radioTechnology == "BLUETOOTH"')
		simRadioBLE.to_csv(path_or_buf='simRadiosBLE.csv')


		# Radio 0
		simRadioWifi0=simRadioWifi.query('accessPointIndex == 0')
		simRadioWifi0=pd.merge(simRadioWifi0, antennasDF[['id','name','maxGain','apCoupling','frequencyBand']],left_on='antennaTypeId', right_on='id', how='left')

		simRadioWifi0.drop(columns=['id_x','id_y','radioTechnology','status','antennaTypeId','accessPointIndex'], inplace=True)
		simRadioWifi0.to_csv(path_or_buf='simRadiosWiFi0.csv')

		simapDF=pd.merge(accessPointsDF, simRadioWifi0, left_on='ap_id', right_on='accessPointId',how='left', suffixes=(None,'_r0'))
		simapDF.drop(columns=['accessPointId','defaultAntennas'], inplace=True)
		simapDF.rename(columns={
				'name':'r0-antenna',
				'transmitPower':'r0-tx_mw',
				'channelByCenterFrequencyDefinedNarrowChannels':'r0-channels',
				'antennaDirection':'r0-azimuth',
				'antennaTilt':'r0-tilt',
				'antennaHeight':'r0-height',
				'antennaMounting':'r0-mounting',
				'technology':'r0-phy',
				'spatialStreamCount':'r0-ss',
				'shortGuardInterval':'r0-sgi',
				'enabled':'r0-enabled',
				'greenfield':'r0-greenfield',
				'maxGain':'r0-gain',
				'apCoupling':'r0-ant-type',
				'frequencyBand':'r0-band'
				}, inplace=True)

		# Radio 1
		simRadioWifi1=simRadioWifi.query('accessPointIndex == 1')
		simRadioWifi1=pd.merge(simRadioWifi1, antennasDF[['id','name','maxGain','apCoupling','frequencyBand']],left_on='antennaTypeId', right_on='id', how='left')
		simRadioWifi1.drop(columns=['id_x','id_y','radioTechnology','status','antennaTypeId','accessPointIndex'], inplace=True)
		simRadioWifi1.to_csv(path_or_buf='simRadiosWiFi1.csv')
		
		simapDF=pd.merge(simapDF, simRadioWifi1, left_on='ap_id', right_on='accessPointId',how='left',suffixes=(None,'_r1'))
		simapDF.drop(columns=['accessPointId','defaultAntennas'], inplace=True)
		simapDF.rename(columns={
				'name':'r1-antenna',
				'transmitPower':'r1-tx_mw',
				'channelByCenterFrequencyDefinedNarrowChannels':'r1-channels',
				'antennaDirection':'r1-azimuth',
				'antennaTilt':'r1-tilt',
				'antennaHeight':'r1-height',
				'antennaMounting':'r1-mounting',
				'technology':'r1-phy',
				'spatialStreamCount':'r1-ss',
				'shortGuardInterval':'r1-sgi',
				'enabled':'r1-enabled',
				'greenfield':'r1-greenfield',
				'maxGain':'r1-gain',
				'apCoupling':'r1-ant-type',
				'frequencyBand':'r1-band'
				}, inplace=True)
		
		# Radio 2
		simRadioWifi2=simRadioWifi.query('accessPointIndex == 2')
		simRadioWifi2=pd.merge(simRadioWifi2, antennasDF[['id','name','maxGain','apCoupling','frequencyBand']],left_on='antennaTypeId', right_on='id', how='left')
		simRadioWifi2.drop(columns=['id_x','id_y','radioTechnology','status','antennaTypeId','accessPointIndex'], inplace=True)
		simRadioWifi2.to_csv(path_or_buf='simRadiosWiFi2.csv')

		simapDF=pd.merge(simapDF, simRadioWifi2, left_on='ap_id', right_on='accessPointId',how='left',suffixes=(None,'_r2'))
		simapDF.drop(columns=['accessPointId','defaultAntennas'], inplace=True)
		simapDF.rename(columns={
				'name':'r2-antenna',
				'transmitPower':'r2-tx_mw',
				'channelByCenterFrequencyDefinedNarrowChannels':'r2-channels',
				'antennaDirection':'r2-azimuth',
				'antennaTilt':'r2-tilt',
				'antennaHeight':'r2-height',
				'antennaMounting':'r2-mounting',
				'technology':'r2-phy',
				'spatialStreamCount':'r2-ss',
				'shortGuardInterval':'r2-sgi',
				'enabled':'r2-enabled',
				'greenfield':'r2-greenfield',
				'maxGain':'r2-gain',
				'apCoupling':'r2-ant-type',
				'frequencyBand':'r2-band'
				}, inplace=True)

		# Bluetooth

		simRadioBLE=pd.merge(simRadioBLE, antennasDF[['id','name','maxGain','apCoupling','frequencyBand']],left_on='antennaTypeId', right_on='id', how='left')
		simRadioBLE.drop(columns=['id_x','id_y','radioTechnology','status','antennaTypeId','accessPointIndex'], inplace=True)
		simRadioBLE.to_csv(path_or_buf='simRadiosBLE.csv')

		simapDF=pd.merge(simapDF, simRadioBLE, left_on='ap_id', right_on='accessPointId',how='left',suffixes=(None,'_bt'))
		#simapDF.drop(columns=['accessPointId','defaultAntennas','greenfield','shortGuardInterval','spatialStreamCount','technology','channel','frequencyBand'], inplace=True)
		simapDF.rename(columns={
				'name':'ble-antenna',
				'transmitPower':'ble-tx_mw',
				'antennaDirection':'ble-azimuth',
				'antennaTilt':'ble-tilt',
				'antennaHeight':'ble-height',
				'antennaMounting':'ble-mounting',
				'enabled':'ble-enabled',
				'maxGain':'ble-gain',
				'apCoupling':'ble-ant-type'
				}, inplace=True)

		
		print("\n\nMerged APs and Simulated Radios:")

		simapDF['ap_serial']=None
		simapDF['ap_hwmac']=None
		simapDF['r0-chanwidth']=None
		simapDF['r1-chanwidth']=None
		simapDF['r2-chanwidth']=None

		fieldlist=[]

		basefields=['ap_id',
					'ap_serial',
					'ap_hwmac',
					'ap_name',
					'vendor',
					'model',
					'coord.x',
					'coord.y',
					'mine',
					'hidden',
					'userDefinedPosition',
					'color'
					]
		radiofields =[	'band',
						'phy',
						'chanwidth',
						'channels',
						'antenna',
						'enabled',
						'gain',
						'tx_mw',
						'ant-type',
						'mounting',
						'azimuth',
						'tilt',
						'height',
						'ss',
						'sgi',
						'greenfield']
		blefields = [	'ble-antenna',
						'ble-enabled',
						'ble-gain',
						'ble-tx_mw',
						'ble-ant-type',
						'ble-mounting',
						'ble-azimuth',
						'ble-tilt',
						'ble-height']
		for f in basefields : fieldlist.append(f)
		for f in tagnameList : fieldlist.append(f)
		for r in range(3):
			for f in radiofields :
				field="r"+str(r)+"-"+f
				fieldlist.append(field)
		for f in blefields : fieldlist.append(f)

		simapDF=simapDF[fieldlist]

		for idx, row in simapDF.iterrows():
			
			for r in range(3):
				radio="r"+str(r)
				ch=radio+"-channels"
				width=radio+"-chanwidth"
				if isinstance(row[ch], list):
					simapDF.at[idx,width]=len(row[ch])*20

		simapDF.to_csv(path_or_buf='deploy.csv')
	# End Simulated AP conditional Block
	
	exit()

if __name__ == "__main__":
	main()
