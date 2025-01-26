**bpo2g** - Parse blood pressure reports exported from Omron as .csv files then import them into Garmin Connect

This is a simple python program that loads files that have been exported from OMRON containing blood pressure history data.

**WARNING!!** It does not check for existing data in Garmin Connect, so if you run it twice, it will create duplicate data.

First, you need to use the Omron app to request a historical report of BP readings.

In the Omron Connect app, go to History > Blood Pressure and tap the Share button in the upper right corner.

Select only Blood Pressure and the period you want, then choose the CSV format and request Omron to email you the report.

Once you receive the emailed .csv report, download the CSV report attachment into a local directory.  The bpo2g tool will work with multiple CSV reports.  

**WARNING!!** Make sure they have non-overlapping date ranges so you don't end up with duplicate data in Garmin Connect.

The Omron BP reports are named like this (in English):
```
Your Requested OMRON Report from Jan 01 2025 to Jan 22 2025.csv
```

And the format should be this: 
```
Date,Time,Systolic (mmHg),Diastolic (mmHg),Pulse (bpm),Symptoms,Consumed,TruRead,Notes
Jan 12 2025,08:12,114,74,47,-,-,-,-
Jan 10 2025,07:49,114,71,47,-,-,-,-
Jan 6 2025,08:46,117,76,50,-,-,-,-
```

Once you have all the reports you want to migrate downloaded, you can proceed to setup the requirements to run the script.

Python Setup: 
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
or you can run the included script: `python_setup.sh`

Running the bpo2g script:
```
python3 src/bpo2g.py -c <csv_directory> -u <garmin_connect_email_username>

The script will securely prompt for the garmin_connect_password
```

The program loads each .csv file in the CSV directory and uploads it to Garmin Connect using the garminconnect python libary from here: [https://pypi.org/project/garminconnect/](https://pypi.org/project/garminconnect/)

You will need to supply a valid username and password for Garmin Connect to the script.




