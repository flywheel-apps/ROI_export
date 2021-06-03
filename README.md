# ROI export

## Description

This gear exports OHIF viewer ROI's from flywheel to a csv.

This csv is compatible with the "ROI import" gear.

### Instructions:

Files must be in DICOM format.  The flywheel DICOM classifier MUST be run before hand
so that the DICOM headers are copied to the file's flywheel metadata.  

Run this gear on a session or project, and the gear will automatically export ALL roi's
on every session in the entire parent project.

Output Columns:

The output columns contain info on the location of the ROI inf flywheel, as well as
information about the ROI itself:

#### Flywheel location columns:

- **group** : The group label that the ROI is in
- **project** : The project label that the ROI is in
- **subject** : The subject label that the ROI is in
- **session** : The session label that the ROI is in
- **acquisition** : The acquisition label that the ROI is in
- **file** : The file name that the ROI is located on
- **dicom member** : The location of the file within the dicom zip archive that the ROI
is on
- **file type** : The type of file that the ROI is on 

#### ROI Information Columns:
- **location** : The "location" given to the ROI (usually a body part/region)
- **description** : A description given to the ROI
- **x min** : The minimum x coordinate of the ROI
- **x max** : The maximum x coordinate of the ROI
- **y min** : The minimum y coordinate of the ROI
- **y max** : The maximum y coordinate of the ROI
- **user origin** : The flywheel user who created the ROI
- **roi type** : The ROI type
- **area** : The area contained in the ROI (mm or vox squared)
- **count** : The number of voxels in the ROI
- **max** : The max voxel value in the ROI
- **mean** : The mean voxel value in the ROI
- **min** : The min voxel value in the ROI
- **stdDev** : The standard deviation of voxel values in the ROI
- **variance** : The Variance of voxel values in the ROI


## Output

The gear generates an output CSV file called:

**<project_label>\_ROI-Export\_\<timestamp>.csv**

where `project_label` is the label of the parent project that this gear was run in, and
`timestamp` is of the format `MM-DD-YYYY_Hour-min-second`



