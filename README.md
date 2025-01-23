OmronBP2GarminBP - Take blood pressure export .csv files from Omron and import them into Garmin Connect

Usage: 

```
omronbp2garminbp <csv_directory> <username> <password>
```

This is a simple python program that loads files which have been exported from OMRON which contain blood pressure history data, like this:

```
Your Requested OMRON Report from Jan 01 2025 to Jan 22 2025.csv
```

The OMRON format of these files is a simple CSV that looks like this:

```
Date,Time,Systolic (mmHg),Diastolic (mmHg),Pulse (bpm),Symptoms,Consumed,TruRead,Notes
Jan 12 2025,08:12,114,74,47,-,-,-,-
Jan 10 2025,07:49,114,71,47,-,-,-,-
Jan 6 2025,08:46,117,76,50,-,-,-,-
```

The program loads each .csv file in a directory and uploads it to Garmin Connect using the garminconnect libary from here: [https://pypi.org/project/garminconnect/](https://pypi.org/project/garminconnect/)

It requires a valid username and password for Garmin Connect.


