#!/usr/bin/env python3

from optparse import OptionParser
import zipfile
import json
from shutil import copyfile
from optparse import OptionParser
import pathlib
import tempfile
import zlib
import os
from pprint import pprint
import csv

def main():
	#This script allows you to update the AP Name attribute of an AP object in Ekahau by using a CSV file containing bss,ess,ap_name,group,model,serial,wired-mac,color
	#Any additional columns used for tags should be defined in tagsXref{} below. 

	# (c) 2021 Ian Beyer
	# based on code by Blake Krone from WiFiAcademy's Advanced Ekahau Design & Survey Fundamentals lab course (https://wifiacademy.net/courses/aeds)


	usage = "usage: %prog [options] csv_file project_file\n CSV file should be formatted as bss,ess,ap_name,group,model,serial,wired-mac,color"
	parser = OptionParser(usage)
	(options, args) = parser.parse_args()

	#Load Ekahau Project archive
	current_filename = pathlib.PurePath(args[1]).stem

	orig_archive = zipfile.ZipFile(args[1],'r')

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

	# Tag Key/Value pairs, with the Tag Name as key, CSV heading as value. 
	# You can add any number of these as tags, just make sure the tag has been created in ekahau first. 
	tagXref={'AP Group':'group',
			 'AP Serial':'serial',
			 'Wired MAC':'wired-mac'}


	#Load CSV file provided from CLI
	with open(args[0], 'r') as csvfile:
		reader = csv.DictReader(csvfile, dialect=csv.excel)
		for row in reader:
			values = {
			'bssid':row['bss'], 
			'ap_name':row['ap_name'], 
			'ssid':row['ess'],
			'model':row['model']
			}

			values['color']= row['color']
	
			for tag in tagXref:
				values[tagXref[tag]]=row[tagXref[tag]]

			ap_data_by_bssid[row['bss']] = values
			
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

	#Initialize tag dicts	
	tagsByName={}
	tagsByID={}

	# Load tag dicts from JSON
	for key in tagKeysJSON['tagKeys']:
		tagsByName[key['key']]=key['id']
		tagsByID[key['id']]=key['key']

	# Check to see if tags exist

	for tag in tagXref.keys():
		# remove any tags from the xref that are not in the Ekahau tagKeys JSON
		if tag not in tagsByName:
			del tagXref[tag]


	#Iterate through each accessPoint element. Good thing computers are fast at repetitive tasks!
	for ap in accessPointsJSON['accessPoints']:
		# Iterate through each measuredRadios with accessPointId = current ap
		for measuredRadio in measuredRadiosJSON['measuredRadios']:
			# If we find a match:
			if measuredRadio['accessPointId'] == ap['id']:
				# Iterate through the measurements list to find the measurement IDs
				for accessPointMeasurementId in measuredRadio['accessPointMeasurementIds']:
					# Iterate through the measurements to find the actual measurement
					for accessPointMeasurement in accessPointMeasurementsJSON['accessPointMeasurements']:
						# If it's a match, then we've found our bssid. 
						if accessPointMeasurement['id'] == accessPointMeasurementId:
							bssid = accessPointMeasurement['mac']
							# If the BSSID is in our list, do the stuff we want to do. 
							if bssid in ap_data_by_bssid:
								print("Matched bssid {0}".format(bssid))

								# This AP is in the controller BSS list, and is therefore "mine", and we need to set the mine flag to true. 
								ap['mine']=True

								# Update the ESSID Name
								accessPointMeasurement['ssid'] = ap_data_by_bssid[bssid]['ssid']
								print("\tUpdated ESSID to {0}".format(ap_data_by_bssid[bssid]['ssid']))

								# Update the AP Name
								ap['name'] = ap_data_by_bssid[bssid]['ap_name']
								print("\tUpdated AP Name to {0}".format(ap['name']))

								# Update the AP model
								ap['model'] = ap_data_by_bssid[bssid]['model']
								print("\tUpdated AP Model to {0}".format(ap['model']))

								# Update the AP color
								# Is the scheme/color in our list?
								print("Color:"+ap_data_by_bssid[bssid]['color'])
								if '/' in ap_data_by_bssid[bssid]['color']: 
									scheme, color=ap_data_by_bssid[bssid]['color'].split('/')
									if scheme in colors:
										if color in colors[scheme]:
											# Update the color. 						
											ap['color']=colors[scheme][color]
											print("\tUpdated color to "+scheme+"/"+color+" ("+colors[scheme][color]+")")
									else:
										# Remove this entire else block if you just want to leave whatever value, if any, alone. 
										# Check to see if an existing color tag exists
										if 'color' in ap.keys():
											# delete it
											del ap['color']

								# Update the tags - start by creating an empty array
								taglist=[]

								# Iterate through the tag keys list for the stuff we're interested in. 
								for tag in tagXref.keys():
									# If it exists in the list, we have a tag key ID for it. 
									if tag in tagsByName.keys():
										# Append the tags list with the new tags
										taglist.append({"tagKeyId" : tagsByName[tag],"value" : ap_data_by_bssid[bssid][tagXref[tag]]})
										print("\tAdded tag "+tag+" : "+tagXref[tag]+" ("+tagsByName[tag]+")")

								# Update the tags object in the ap dict with the list object we just made		
								ap['tags']=taglist
							else:
								#This AP is unknown to the controller, and thus not mine, and we need to set the mine flag to false. 
								ap['mine']=False

	# Building the new file and Writing the updated data back out to it
	with tempfile.TemporaryDirectory() as tmpdirname:
		# Get all the other stuff from the input ESX
		orig_archive.extractall(tmpdirname)

		# Write out the AP data
		with open(os.path.join(tmpdirname, 'accessPoints.json'), 'w') as outfile:
			json.dump(accessPointsJSON, outfile)

		# Write out the Measurements data
		with open(os.path.join(tmpdirname, 'accessPointMeasurements.json'), 'w') as outfile:
			json.dump(accessPointMeasurementsJSON, outfile)
		
		# Create new ESX file
		new_archive = zipfile.ZipFile(current_filename + "_modified.esx",'w',zipfile.ZIP_DEFLATED)
		for dirname, subdirs, files in os.walk(tmpdirname):
			for filename in files:
				new_archive.write(os.path.join(tmpdirname, filename), filename)

	# Close the files
	orig_archive.close()
	new_archive.close()

if __name__ == "__main__":
	main()
