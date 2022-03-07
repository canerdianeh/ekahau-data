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

def main():
	
	pp = pprint.PrettyPrinter(indent=3)

	defaultfile="ekahau_ap_report.csv"

	cli=argparse.ArgumentParser(description='Generate CSV report of all APs in an Ekahau survey file')

	cli.add_argument("-o", "--output", required=False, help='Output File', default=defaultfile)
	cli.add_argument("-i", "--input", required=True, help='Input File')

	args = vars(cli.parse_args())

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
	
	# Load Notes

	with orig_archive.open('notes.json') as json_file:
		notesJSON = json.load(json_file)
		json_file.close()

	# Load AP Table
	with orig_archive.open('accessPoints.json') as json_file:
		accessPointsJSON = json.load(json_file)
		json_file.close()

	# Load Radios Table
	with orig_archive.open('measuredRadios.json') as json_file:
		measuredRadiosJSON = json.load(json_file)
		json_file.close()		

	# Load Measurements Table
	with orig_archive.open('accessPointMeasurements.json') as json_file:
		accessPointMeasurementsJSON = json.load(json_file)
		json_file.close()		

	# Load Tag Keys Table
	# Need to add error handling here in case tagKeys doesn't exist. 

	with orig_archive.open('tagKeys.json') as json_file:
		tagKeysJSON = json.load(json_file)
		json_file.close()

	# Load Floor Plans Table

	with orig_archive.open('floorPlans.json') as json_file:
		floorPlansJSON = json.load(json_file)
		json_file.close()

	# Load Buildings Table

	with orig_archive.open('buildings.json') as json_file:
		buildingsJSON = json.load(json_file)
		json_file.close()

	with orig_archive.open('buildingFloors.json') as json_file:
		buildingFloorsJSON = json.load(json_file)
		json_file.close()

	# Close input file, we are done with it and don't need open files aimlessly hanging around. 
	orig_archive.close()

	#Build indexes
	#Build index of APs by MeasurementID

	apByMeasurement={}

	for ap in measuredRadiosJSON['measuredRadios']:
		for measID in ap['accessPointMeasurementIds']:
			apByMeasurement[measID]=ap['accessPointId']

	#print("\n\nAPs by measurement ID\n")
	#pp.pprint(apByMeasurement)

	apByID={}

	for ap in accessPointsJSON['accessPoints']:
		apByID[ap['id']]=ap

	#print("\n\nAPs by AP ID\n")
	#p.pprint(apByID)

	#Initialize floor plan dicts
	floorsByName={}
	floorsbyID={}
	bldgsByFloor={}

	#Initialize building dicts
	bldgsByName={}
	bldgsbyID={}

	# Create floor/ID Xref
	for building in buildingsJSON['buildings']:
		bldgsByName[building['name']]=building['id']
		bldgsbyID[building['id']]=building['name']
		
	# Create floor/ID Xref
	for floor in floorPlansJSON['floorPlans']:
		floorsByName[floor['name']]=floor['id']
		floorsbyID[floor['id']]=floor['name']
		for bldgfloor in buildingFloorsJSON['buildingFloors']:
			if floor['id'] == bldgfloor['floorPlanId']:
				bldgsByFloor[floor['id']]=bldgsbyID[bldgfloor['buildingId']]

	#pp.pprint(bldgsByFloor)

	#Initialize tag dicts	
	tagsByName={}
	tagsByID={}

	# Load tag dicts from JSON
	for key in tagKeysJSON['tagKeys']:
		tagsByName[key['key']]=key['id']
		tagsByID[key['id']]=key['key']

	#Initialize output list - this is a list of dict objects.

	outputData=[]

	# What contains what?
	#
	# accessPointsJSON contains:
	#   AP Name
	#	My Status (Boolean)
	#	Vendor
	#	Model
	#	Tags (Dict)
	#	notes (Dict)
	# 	ID (referenced in measuredRadios as accessPointID)
	#	Color
	#	Location (dict containing floorPlanID and dict of x/y coordinates)
	#
	# accessPointMeasurementsJSON contains:
	#	bssid (MAC)
	#	essid
	#	channel (list)
	#	encryption
	#	PHY (list)
	#	Information Elements (encoded string)
	#	ID (referenced in measuredRadios as accessPointMeasurementIDs)
	#
	# measuredRadiosJSON contains:
	#	access point ID
	#	AP Measurement IDs (list)
	#	ID 

	technologies=['A','B','G','N','AC','AX']

	fields=[
		'ap_name',
		'bssid',
		'mine',
		'vendor',
		'model',
		'essid',
		'encryption',
		'band']

	for phy in technologies:
		fields.append("PHY_"+phy)

	for f in [
		'chan_width',
		'pri_channel',
		'sec_channel',
		'channel_3',
		'channel_4',
		'channel_5',
		'channel_6',
		'channel_7',
		'channel_8',
		'building',
		'floor',
		'x-coord',
		'y-coord',
		'color'
		]:
			fields.append(f)

	for tag in tagsByName.keys():
		fields.append(tag)

	#Iterate through each accessPoint element. Good thing computers are fast at repetitive tasks!
	for measuredRadio in accessPointMeasurementsJSON['accessPointMeasurements']:
		ap=apByID[apByMeasurement[measuredRadio['id']]]

		outputRow={}
		for f in fields:
			outputRow[f]=None

		outputRow['bssid']=measuredRadio['mac']

		if 'ssid' in measuredRadio.keys():
			if measuredRadio['ssid'] != "":
				outputRow['essid']=measuredRadio['ssid']
			else:
				outputRow['essid']='[Hidden]'
		
		if 'security' in measuredRadio.keys():
			outputRow['encryption']=measuredRadio['security']
		
		if 'channel' in measuredRadio.keys():
			chans=measuredRadio['channel']
			if chans[0] < 36:
				outputRow['band']="2.4"
			else:
				outputRow['band']="5"

			if len(chans) == 1:
				outputRow['pri_channel']=chans[0]
				outputRow['chan_width']=20
			if len(chans) == 2:
				outputRow['pri_channel']=chans[0]
				outputRow['sec_channel']=chans[1]
				outputRow['chan_width']=40
			if len(chans) == 4:
				outputRow['pri_channel']=chans[0]
				outputRow['sec_channel']=chans[1]
				outputRow['channel_3']=chans[2]
				outputRow['channel_4']=chans[3]
				outputRow['chan_width']=80
			if len(chans) == 8:
				outputRow['pri_channel']=chans[0]
				outputRow['sec_channel']=chans[1]
				outputRow['channel_3']=chans[2]
				outputRow['channel_4']=chans[3]
				outputRow['channel_5']=chans[4]
				outputRow['channel_6']=chans[5]
				outputRow['channel_7']=chans[6]
				outputRow['channel_8']=chans[7]
				outputRow['chan_width']=160

		for phy in technologies:

			header="PHY_"+str(phy)

			outputRow[header]=False
			if phy in measuredRadio['technologies']:
				outputRow[header]=True


		outputRow['ap_name']=ap['name']
		outputRow['mine']=ap['mine']

		if 'location' in ap.keys():
			outputRow['building']=bldgsByFloor[ap['location']['floorPlanId']]
			outputRow['floor']=floorsbyID[ap['location']['floorPlanId']]
			outputRow['x-coord']=ap['location']['coord']['x']
			outputRow['y-coord']=ap['location']['coord']['y']

		for tag in tagsByName.keys():
			outputRow[tag]=""

		for tag in ap['tags']:
			header=tagsByID[tag['tagKeyId']]
			outputRow[header]=tag['value']
		if 'vendor' in ap.keys():
			outputRow['vendor']=ap['vendor']
		if 'model' in ap.keys():
			outputRow['model']=ap['model']
		if 'color' in ap.keys():
			outputRow['color']=ap['color']

		outputData.append(outputRow)

	# Create the CSV

	with open(args['output'], 'w') as csvfile:
		outputFile=csv.writer(csvfile)

		outputFile.writerow(fields)
		for row in outputData:
			datarow=[]
			for f in fields:
				datarow.append(row[f])
			outputFile.writerow(datarow)

	csvfile.close()

if __name__ == "__main__":
	main()
