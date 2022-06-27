#!/usr/bin/env python3

# This script allows you to add new tag keys to an Ekahau data file. 

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
import uuid
import pandas as pd

pp = pprint.PrettyPrinter(indent=3)

def main():

	defaultfile="output.csv"

	cli=argparse.ArgumentParser(description='Add new tag keys to an Ekahau survey file')

	cli.add_argument("-i", "--input", required=True, help='Input File')
	cli.add_argument("-t", '--tag-name', required=True, nargs='+', help="New Tag name - one or more. Enclose each in quotes or escape non-alphas")
	

	args = vars(cli.parse_args())

	newTags=args['tag_name']
	
	#Load Ekahau Project archive
	current_filename = pathlib.PurePath(args['input']).stem

	orig_archive = zipfile.ZipFile(args['input'],'r')


	print("==========")
	# Load Tag Keys Table
	workingFile='tagKeys.json'

	if workingFile in orig_archive.namelist():
		print ("Loading "+workingFile+"...")
		with orig_archive.open(workingFile) as json_file:
			tagKeysJSON = json.load(json_file)
			json_file.close()
	#	tagKeysDF=pd.DataFrame(tagKeysJSON['tagKeys'])		
	#	tagKeysDF.drop(columns=['status'])
		tagData = True

	else:
		print(workingFile+" not found in archive. Creating Blank Tag List. ")
		tagKeysJSON={'tagKeys':[]}
		#tagKeysDF=pd.DataFrame()
		tagData = False

	# create UUID
	for tag in newTags:

		tagKeyId = str(uuid.uuid4())
		print(tag+" : Generated UUID "+tagKeyId)
		tagKeyName = tag
		newTag={'key':tagKeyName, 'id':tagKeyId, 'status':'CREATED'}
		print("Added to list")
		tagKeysJSON['tagKeys'].append(newTag)

	if len(tagKeysJSON['tagKeys']) > 0:

		with tempfile.TemporaryDirectory() as tmpdirname:
		# Get all the other stuff from the input ESX
			orig_archive.extractall(tmpdirname)

		# Write out the tag data
			with open(os.path.join(tmpdirname, 'tagKeys.json'), 'w') as outfile:
				outfile.write(json.dumps(tagKeysJSON, indent=2))
		
		# Create new ESX file
			new_archive = zipfile.ZipFile(current_filename + "_modified.esx",'w',zipfile.ZIP_DEFLATED)
			for dirname, subdirs, files in os.walk(tmpdirname):
				for filename in files:
					new_archive.write(os.path.join(tmpdirname, filename), filename)

		# Close the files
		orig_archive.close()
		new_archive.close()


	# End of conditional loop
	
	exit()

if __name__ == "__main__":
	main()
