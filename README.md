# ekahau-data
Ekahau Data Manipulation Code

Here you'll find scripts for fiddling with Ekahau data files to do things that are either impossible within the Ekahau application, or are a tedious manual process. 

## Update_APs.py
based on a lab file from WiFiAcademy, this takes a list of BSSIDs from a CSV and updates AP names, models, ESSIDs, as well as adding key/value tags for AP groups, AP serial numbers, AP Wired MAC addresses, and anything else you want. Can be used in conjunction with my Aruba API scripts for pulling BSS table and AP Database. 

## AP_Report.py
This script will go through all the surveyed radios in an ekahau file and generate a CSV file with the following fields (input to CSV is string unless otherwise indicated - CSV output is always strings):

  * AP Name
  * BSSID
  * My (boolean)
  * Vendor
  * Model
  * ESSID
  * Encryption
  * Band
  * A/B/G/N/AC/AX PHYs (boolean for each)
  * Channel Width (int)
  * Primary Channel Number (int)
  * Secondary Channel Number (int)
  * Channels 3-8 (int)
  * Building
  * Floor
  * X/Y Coordinates (float)
  * Color
  * Tags (one per column, header is tag name, all defined tags in the ESX data file will have a column)
  
Note that because the primary key here is the BSSID, there will be multiple entries per AP. It's also possible to have multiple surveyed channels for an AP if it's under RRM. These will show up as multiple rows with the same BSSID. 
