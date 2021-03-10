# metadata import

## Description

This gear imports metadata from a csv into flywheel.

The CSV columns specify a flywheel object identifier, and metadata information to import.
Column headers specify the name of the metadata info, while all following rows specify 
the values to upload for a given object.  By default, the gear assumes that the first 
column has the flywheel object identifier.  This is a file name or object label.  If the
gear can locate the specified file/container, the metadata specified in the rest of the 
table is uploaded.  By default, the gear uploads all metadata under an object with the
same name as the CSV file.  

For example, uploading a csv file called "Initial_Exam_Results.csv" with the following
info:

| SubID       | Mood        | Percent Correct | Duration of stay (min) |
| ----------- | ----------- | --------------- | ---------------------- |
| sub01  | happy | 89 | 23 |
| sub02  | sad | 75 | 34 |


After the proper configuration options are set, the gear would look for subjects with 
the labels "sub01" and "sub02", and would populate:

    Mood: "happy"
    Percent Correct: 89
    Duration of stay (min): 23
   
to `sub01.info.Initial_Exam_Results`



## Inputs & Settings

### Inputs:

 - **csv_file**: The input CSV file to be ingested for metadata upload
  

  
### Config Settings:

#### CSV file properties:

 - **mapping_column**: The name of the column (column header) that contains the flywheel
 object names.  By default, flywheel assumes this is the first column.

 - **object_type**: This specifies what type of object is being specified in the 
 mapping column (If mapping to files, select the level of container that the files are
 stored on).  By default, this assumes that the ID's are for subjects
 
 - **attached_files**: If the objects specified in the mapping column are files, check 
 this box, and for "object_type", specify the container level that these files are
 attached to.
  
 - **metadata_destination**: The location of the metadata fields to be uploaded to under
  'info'.  Default is the csv file's name.  Sub-categories are specified with a period,
   e.x. 'Health.InitialAssessment' would upload the metadata to 
   `<object>.info.Health.InitialAssessment`

 - **first_row**: The first row that contains data.  By default, the gear assumes row 1.
  The first fow of data MUST be column headers.  Row 1 is always the absolute first row 
  of the file.
 
 - **delimiter**: Flywheel can support tab, space, and comma separated files.  Default 
 is comma.

#### Gear Execution Properties:

 - **gear_log_level**: The level at which the gear will log.  "Info" for normal amounts
 of information, and "Debug" for more detailed logs.

 - **dry_run**: Only log what changes would be made, do not update anything.
 
 - **overwrite**: If checked, the gear will overwrite existing metadata with what's in 
 the CSV.
 
 
## Logging

This gear will log information the help you follow the progress of the metadata ingest.

The log is roughly broken into 3 parts:  First, the configuration settings are logged:

```
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.logging] Log level is INFO
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Destination is analysis=6037e06f8afc643bad6e8ace
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Input file "csv_file" is Data_Entry_2017_test.csv from project=6037d56c6e67757f166e8aa6
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "attached_files=True"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "delimiter=,"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "dry_run=False"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "first_row=1"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "gear_log_level=INFO"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "mapping_column="
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "object_type=acquisition"
[ 20210225 17:41:21     INFO flywheel_gear_toolkit.context.context] Config "overwrite=True"
[ 20210225 17:41:21     INFO utils.load_data] No object column specified, assuming column 1
[ 20210225 17:41:21     INFO utils.load_data] Using column Image Index
[ 20210225 17:41:22     INFO __main__] Starting Mapping
```


Following this, each row will generate a report.  For example, given the row:

| Image Index | Finding Labels | Follow-up # | Patient ID | Patient Age | Patient Gender | View Position | "OriginalImage[Width,Height]" | "OriginalImagePixelSpacing[x,y]" |
| ----------- | -------------- | ----------- | ---------- | ----------- | -------------- | ------------- | ----------------------------- | -------------------------------- |
| 00000340_239.png | No Finding | 3 | 340 | 33 | F | AF | "3532,3451" | "0.033,0.643" |


The output may look like this:

```[ 20210225 17:41:22     INFO __main__] 
==================================================
Setting Metadata For 00000500_009.png
--------------------------------------------------
[ 20210225 17:41:22     INFO __main__] Image Index                       00000340_239.png
Finding Labels                          No Finding
Follow-up #                                      3
Patient ID                                     340
Patient Age                                     33
Patient Gender                                   F
View Position                                   AF
OriginalImage[Width,Height]              3532,3451
OriginalImagePixelSpacing[x,y]         0.033,0.643

Name: 0, dtype: object
[ 20210225 17:41:22     INFO __main__] updating {'Data_Entry_2017_test': {'csv': {'Finding Labels': 'No Finding', 'Follow-up #': 3, 'Patient ID': 340, 'Patient Age': 33, 'Patient Gender': 'F', 'View Position': 'AF', 'OriginalImage[Width,Height]': '3532,3451', 'OriginalImagePixelSpacing[x,y]': '0.033,0.643'}}
[ 20210225 17:41:22     INFO __main__] 
--------------------------------------------------
STATUS: Success
==================================================
```

Finally, at the end, a summary will be given on the whole process:
```
===============================================================================
Final Report: 10/11 objects updated successfully
90.9090909090909%
See output report file for more details
===============================================================================
```

## Output

The gear generates an output CSV file called "Data_Import_Status_report.csv".

This file is a copy of the original CSV, with two additional columns:

- 'Gear_Status': The status of the upload for the specified row.  "Success" or "Fail"
- 'Gear_FW_Location': The full fw path to the object modified, specified as: 

`<group>/<project>/<subject>/<session>/<acquisition>/<file>`




