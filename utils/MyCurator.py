import copy
import logging
from pathlib import Path
from pprint import pprint
import json

import pydicom
from pydicom.filebase import DicomBytesIO

import flywheel

from flywheel_gear_toolkit.utils import curator
from flywheel_gear_toolkit.utils.datatypes import Container

POSSIBLE_KEYS = ["ohifViewer", "roi"]
OHIF_KEY = "ohifViewer"
SUPPORTED_ROIS = ["RectangleRoi", "EllipticalRoi"]
EXPORT_VALUES = [""]
KNOWN_EXTENSIONS = {
    ".dcm": "DICOM",
    ".dicom": "DICOM",
    ".nii.gz": "NIFTI",
    ".nii": "NIFTI",
}

OUTPUT_TEMPLATE = {
    "Group": [],
    "Project": [],
    "Subject": [],
    "Session": [],
    "Acquisition": [],
    "File": [],
    "Dicom Member": [],
    "File Type": [],
    "location": [],
    "description": [],
    "X min": [],
    "X max": [],
    "Y min": [],
    "Y max": [],
    "User Origin": [],
    "ROI type": [],
    "area": [],
    "count": [],
    "max": [],
    "mean": [],
    "min": [],
    "stdDev": [],
    "variance": []
}


log = logging.getLogger("export-ROI")


class ROICurator(curator.HierarchyCurator):
    def __init__(self, fw):
        super().__init__()
        self.fw = fw

    def curate_container(self, container: Container):
        """Curates a generic container and returns a python dictionary
        
        The returned python dictionary contains any OhifViewer ROI metadata objects.
        The returned dictionary is organized as follows:
        
        output_dict = {"ROI TYPE": [<list of ROIs of that type>]}

        Args:
            container (Container): A Flywheel container.
            
        Returns:
            output_dict (dict):  A dictionary of ROI types found on the container
        """
        
        if hasattr(container, "container_type"):
            container_type = container.container_type
            if container_type == "project":
                if self.validate_project(container):
                    output_dict = self.curate_project(container)
            elif container_type == "subject":
                if self.validate_subject(container):
                    output_dict = self.curate_subject(container)
            elif container_type == "session":
                if self.validate_session(container):
                    output_dict = self.curate_session(container)
            elif container_type == "acquisition":
                if self.validate_acquisition(container):
                    output_dict = self.curate_acquisition(container)
            elif container_type == "file":
                if self.validate_file(container):
                    output_dict = self.curate_file(container)
            else:
                if self.validate_analysis(container):
                    output_dict = self.curate_analysis(container)
        else:
            # element is a file and has no children
            if self.validate_file(container):
                output_dict = self.curate_file(container)

        return output_dict


    def get_file_hierarchy(self, file):
        """ Returns the hierarchy path for a given file on flywheel
        
        This is used to provide a human-readable path to the file that an ROI is found
        on.  These values are later saved in an output.csv file.
        
        Args:
            container (flywheel.models.FileReference): The flywheel container that 
            is the direct parent of the file

        Returns:
            group_label (str): the label of the file's parent group
            project_label (str): the label of the file's parent project
            subject_label (str): the label of the file's parent subject
            session_label (str): the label of the file's parent session
            acquisition_label (str): the label of the file's parent acquisition

        """
        
        # The highest level a file can be on is a project,  so it will ALWAYS have a 
        # parent group and project:
        group_label = file.parent.parents.group
        project_id = file.parent.parents.project
        if project_id:
            project_label = self.fw.get_project(project_id).label
        else:
            if file.parent.container_type == "project":
                project_label = file.parent.label
            else:
                project_label = None
        
        
        # Check if the file has a parent subject and extract label if so
        subject_id = file.parent.parents.subject
        if subject_id:
            subject_label = self.fw.get_subject(subject_id).label
        else:
            if file.parent.container_type == "subject":
                subject_label = file.parent.label
            else:
                subject_label = None
        
        # Check if file has a parent session and extract label of so
        session_id = file.parent.parents.session
        if session_id:
            session_label = self.fw.get_session(session_id).label
        else:
            if file.parent.container_type == "session":
                session_label = file.parent.label
            else:
                session_label = None
        
        # Check if the file has a parent acquisition and extract label
        acquisition_id = file.parent.parents.acquisition
        if acquisition_id:
            acquisition_label = self.fw.get_acquisition(acquisition_id).label
        else:
            if file.parent.container_type == "acquisition":
                acquisition_label = file.parent.label
            else:
                acquisition_label = None

        return (
            group_label,
            project_label,
            subject_label,
            session_label,
            acquisition_label,
        )


    def get_roi_hierarchy(self, session, roi):
        """ Returns the hierarchy paths for each file that has an ROI within a given
        session on flywheel

        This is used to provide a human-readable path to the session that an ROI is found
        on.  These values are later saved in an output.csv file.

        Args:
            session (flywheel.Session): The flywheel session that has ROI metadata.
            roi (dict): the specific ROI that we are generating a hierarchy for

        Returns:
            group_label (str): the label of the file's parent group
            project_label (str): the label of the file's parent project
            subject_label (str): the label of the file's parent subject
            session_label (str): the label of the file's parent session
            acquisition_label (str): the label of the file's parent acquisition
            file_name (str): The name of the file that the 
            file_type,

        """
        
        # If this ROI doesn't have this key, we have no way of linking it to a file
        # when operating at the session level.
        file_id = roi.get("seriesInstanceUid")
        if file_id is None:
            log.error("No seriesInstanceUid for ROI")
            return [None]*7
        
        # Get all the files contained in all the acquisitions in this session
        acquisitions = session.acquisitions()
        files = []
        for a in acquisitions:
            files.extend(a.reload().files)
        
        # Get dicoms only
        files = [f for f in files if f.type == "dicom"]
        
        # If they have metadata (THEY MUST), match the series instance uid to find the 
        # fild that this ROI is reffereing to.
        my_file = [f for f in files if f.info.get("SeriesInstanceUID", "").replace('_', '.') == file_id]

        if len(my_file) == 0:
            log.warning("No files match series instance UID")
            return [None]*7

        elif len(my_file) > 1:
            log.warning(f"Multiple matches for series uid {file_id} ")

        my_file = my_file[0]

        file_name = Path(my_file.name)
        suffix = "".join(file_name.suffixes[-2:])
        file_type = KNOWN_EXTENSIONS.get(suffix, suffix[1:])
        
        # Now actually work backwards from this file to build the full hierarchy
        (
            group_label,
            project_label,
            subject_label,
            session_label,
            acquisition_label,
        ) = self.get_file_hierarchy(my_file)

        return (
            group_label,
            project_label,
            subject_label,
            session_label,
            acquisition_label,
            file_name,
            file_type,
        )


    def process_namespace_roi(
        self,
        roi_namespace,
        file
    ):
        """
        Processes the OHIF viewer ROI's when they're saved under the namespace "roi"
        
        I'm not sure if this is an older version of the ROI's or something but 
        sometimes i see them in this location so I made this to cover that case.
        
        Args:
            roi_namespace (dict): the metadata object within the "roi" namespace
            file (flywheel.FileEntry): the file that the metadata is attached to

        Returns:
            output_dict (dict): an output dictionary with the desired ROI info.

        """

        # Create a copy of the output template.  This will be populated here.
        output_dict = copy.deepcopy(OUTPUT_TEMPLATE)
        
        for roi in roi_namespace:
            roi_type = roi.get("toolType")
            # Tool types aren't even formated the same as `SUPPORTED_ROIS` keys...
            # I could add these to the list but again, idk.
            if roi_type == "rectangleRoi" or roi_type == "ellipticalRoi":
                
                study_uid = roi.get("studyInstanceUid")
                series_uid = roi.get("seriesInstanceUid")
                sop_uid = roi.get("sopInstanceUid")
                
               
                dicom_member = self.get_roi_dicom_file(file, study_uid, series_uid,
                                                       sop_uid)
                
                (
                    group_label,
                    project_label,
                    subject_label,
                    session_label,
                    acquisition_label,
                ) = self.get_file_hierarchy(file)

                file_name = Path(file.name)

                suffix = "".join(file_name.suffixes[-2:])
                file_type = KNOWN_EXTENSIONS.get(suffix, suffix[1:])
                
                
                (
                    description,
                    label,
                    timestamp,
                    x_start,
                    y_start,
                    x_end,
                    y_end,
                    user_origin,
                    cached_stats
                ) = self.process_generic_roi(roi)

                output_dict["Group"].append(group_label)
                output_dict["Project"].append(project_label)
                output_dict["Subject"].append(subject_label)
                output_dict["Session"].append(session_label)
                output_dict["Acquisition"].append(acquisition_label)

                output_dict["File"].append(file_name)
                output_dict["Dicom Member"].append(dicom_member)
                output_dict["File Type"].append(file_type)

                output_dict["location"].append(label)
                output_dict["description"].append(description)

                output_dict["X min"].append(x_start)
                output_dict["X max"].append(x_end)
                output_dict["Y min"].append(y_start)
                output_dict["Y max"].append(y_end)

                output_dict["area"].append(cached_stats.get('area', 0))
                output_dict["count"].append(cached_stats.get('count', 0))
                output_dict["max"].append(cached_stats.get('max', 0))
                output_dict["mean"].append(cached_stats.get('mean', 0))
                output_dict["min"].append(cached_stats.get('min', 0))
                output_dict["stdDev"].append(cached_stats.get('stdDev', 0))
                output_dict["variance"].append(cached_stats.get('variance', 0))

                output_dict["User Origin"].append(user_origin)

                output_dict["ROI type"].append(roi_type)

        return output_dict


    def process_namespace_ohifViewer(
        self,
        session,
        roi_namespace
    ):
        
        """
        Process the metadata structure "ohifViewer" to extract ROI's from a session.
        
        The session is passed in for hierarchy information.  The roi_namespace is
        metadata extracted from session.info. It's passed in as its own object... for
        reasons?  It made sense to have the logic of finding that namespace and
        extracting it in a different function in case the structure ever changes.
        
        Args:
            session (flywheel.Session): The session that has the metadata ROI
            roi_namespace (dict): The actual metadata ROI from the session pre-extracted

        Returns:

        """
        
        # Create a copy of the output template.  This will be populated here.
        output_dict = copy.deepcopy(OUTPUT_TEMPLATE)
        
        # Loop through the different ROI types in the namespace
        for roi_type in roi_namespace.keys():
    
            # If it's a supported ROI type, we will process
            if roi_type in SUPPORTED_ROIS:
                
                # This structure is a list of all ROI's of that type.
                roi_type_namespace = roi_namespace.get(roi_type, {})
                
                # Loop through that list and process each one.
                for roi in roi_type_namespace:
                    
                    # These three pieces link the ROI to the file/slice (vital)
                    study_uid = roi.get("studyInstanceUid", roi.get("StudyInstanceUID"))
                    series_uid = roi.get("seriesInstanceUid", roi.get("SeriesInstanceUID"))
                    sop_uid = roi.get("sopInstanceUid", roi.get("SOPInstanceUID"))
                    
                    # With these three, we will locate the exact dicom file that the 
                    # session level ROI is referring to
                    dicom_member = self.get_roi_dicom_file(session, study_uid, series_uid, sop_uid)
                    
                    # This rebuilds the flywheel path (hierarchy) in human readable
                    # labels for this particular ROI
                    
                    (
                        group_label,
                        project_label,
                        subject_label,
                        session_label,
                        acquisition_label,
                        file_name,
                        file_type,
                    ) = self.get_roi_hierarchy(session, roi)
                    
                    # Now extract all the information we need from this ROI.
                    (
                        description,
                        label,
                        timestamp,
                        x_start,
                        y_start,
                        x_end,
                        y_end,
                        user_origin,
                        cached_stats
                    ) = self.process_generic_roi(roi)

                    # If we don't have a group label, we didn't find a matching file.
                    # We must skip.
                    if group_label is None:
                        log.info('Unable to find matching file for ROI')
                        continue
                    
                    # populate the output_dictionary
                    output_dict["Group"].append(group_label)
                    output_dict["Project"].append(project_label)
                    output_dict["Subject"].append(subject_label)
                    output_dict["Session"].append(session_label)
                    output_dict["Acquisition"].append(acquisition_label)
                    
                    output_dict["File"].append(file_name)
                    output_dict["Dicom Member"].append(dicom_member)
                    output_dict["File Type"].append(file_type)
                    
                    output_dict["location"].append(label)
                    output_dict["description"].append(description)
                    
                    output_dict["X min"].append(x_start)
                    output_dict["X max"].append(x_end)
                    output_dict["Y min"].append(y_start)
                    output_dict["Y max"].append(y_end)
                    
                    output_dict["area"].append(cached_stats.get('area', 0))
                    output_dict["count"].append(cached_stats.get('count', 0))
                    output_dict["max"].append(cached_stats.get('max', 0))
                    output_dict["mean"].append(cached_stats.get('mean', 0))
                    output_dict["min"].append(cached_stats.get('min', 0))
                    output_dict["stdDev"].append(cached_stats.get('stdDev', 0))
                    output_dict["variance"].append(cached_stats.get('variance', 0))

                    output_dict["User Origin"].append(user_origin)

                    output_dict["ROI type"].append(roi_type)

        return output_dict


    def process_generic_roi(self, roi):
        """
        Processes the generic structure of an OHIF viewer ROI, regardless of ROI type
        
        
        Args:
            roi (dict): an OHIF viewer ROI metadata object

        Returns:
            description (str): the description of the ROI
            label (str): the Label of the ROI
            timestamp (str): the timestamp that the ROI was created
            x_start (float): the smallest x coordinate of the ROI
            y_start (float): the smallest y coordinate of the ROI
            x_end (float): the largest x coordinate of the ROI
            y_end (float): the largest y coordinate of the ROI
            user_origin (str): the flywheel ID of the user who created the ROI
            cached_stats (dict): a dictionary of cached stats about the ROI

        """
        
        # Simply exctract the values we need
        description = roi.get("description")
        label = roi.get("location")
        timestamp = roi.get("updatedAt")
        
        # Label can be two different things...It's weird, ok?
        if label is None:
            label = roi.get("label")
        
        # these are dictionaries that have information we need
        handles = roi.get("handles", {})
        start = handles.get("start", {})
        end = handles.get("end", {})
        
        # Not sure why I don't just take the start and end...
        exs = (start.get("x"), end.get("x"))
        whys = (start.get("y"), end.get("y"))
        x_start = min(exs)
        y_start = min(whys)

        x_end = max(exs)
        y_end = max(whys)
        
        # Get the user
        user_origin = roi.get("updatedById")
        if user_origin is None:
            user_origin = roi.get("flywheelOrigin", {}).get("id")
        
        # Retrieve the cahed stats (things like voxel value mean, min, max, std, etc)    
        cached_stats = roi.get('cachedStats', {})
        log.debug(f"Cached stats:{cached_stats}")
        
        return (
            description,
            label,
            timestamp,
            x_start,
            y_start,
            x_end,
            y_end,
            user_origin,
            cached_stats
        )


    def curate_session(self, session: flywheel.Session):
        """
        Curates a flywheel session container object to extract ROI's.
        
        Args:
            session (flywheel.Session): The flywheel Session to curate.

        Returns:
            output_dict (dict)
        """

        log.info(f"curating session {session.label}")
        
        # Copy the output dict template.  Could alternatively be done with dict
        # comprehension.  Each item in output_dict is a list.  Each list will have
        # one entry for every ROI
        session = session.reload()
        session_info = session.info
        
        # I've seen two keys used for this, "roi" and "ohifViewer".  'roi' was probably
        # Just for testing since I rarely see it, but here we are.
        output_dict = {}
        for OHIF_KEY in session_info:
            log.debug(f"checking {OHIF_KEY} in {session_info.keys()}")
            # We're looking for the 'measurements' key.
            measurements = session_info.get(OHIF_KEY, {}).get("measurements", {})
            
            # Process this metadata structure
            output_dict = self.process_namespace_ohifViewer(session, measurements)
            
        return output_dict


    def curate_file(self, file: flywheel.FileEntry):
        """
        Curates a flywheel session container object to extract ROI's.
        
        Args:
            file (flywheel.FileEntry): the file to curate

        Returns:

        """
        
        log.info(f"curating file {file.name}")

        output_dict = copy.deepcopy(OUTPUT_TEMPLATE)

        # Files can have either rois or ohifViewers... I think files are being phased
        # out in general for having this ROI metadata in favor of always storing it at
        # the session level but idk.
        for pk in POSSIBLE_KEYS:
            log.debug(f"checking {pk} in {file.info.keys()}")
            if pk in file.info:

                log.debug("FOUND")
                # If the namespace is "roi", the structure is slightly different
                if pk == "roi":
                    namespace = file.info.get(pk, {})
                    output_dict = self.process_namespace_roi(
                        namespace,
                        file
                    )

                    # for d in temp_dict:
                    #     if d in output_dict:
                    #         output_dict[d].extend(temp_dict[d])
                    #     else:
                    #         output_dict[d] = temp_dict[d]

                elif pk == "ohifViewer":
                    namespace = file.info.get(pk, {}).get("measurements", {})
                    parent_ses = file.parent.parents.session
                    if parent_ses is None:
                        log.debug('file is not at acquisition level, skipping')
                        continue
                    session = self.fw.get_session(parent_ses)
                    output_dict = self.process_namespace_ohifViewer(session, namespace)

                    # for d in temp_dict:
                    #     if d in output_dict:
                    #         output_dict[d].extend(temp_dict[d])
                    #     else:
                    #         output_dict[d] = temp_dict[d]

        return output_dict


    def get_roi_dicom_file(self, fw_object, study_uid, series_uid, sop_uid):
        """ locates the specific dicom file associated with a given ROI.
        
        Given an ROI's study UID, series UID, and SOP uid, locate the exact dicom file
        that the roi corresponds to.  
        
        Args:
            fw_object (flywheel object): flywheel file or a parent container of a file
            study_uid (str): the study UID on the ROI
            series_uid (str): the series UID on the ROI
            sop_uid (str):  the SOP uid on the ROI

        Returns:
            dicom_file (str) the name of the dicom file that the ROI is on. 

        """
        
        container_type = fw_object.container_type
        if container_type == "file":
            log.debug('working on file')
            acq = fw_object.parent
            files = [fw_object]
            object_name = fw_object.name
            
        elif container_type == "acquisition":
            log.debug('working on acquisition')
            files = fw_object.reload().files
            object_name = fw_object.label
    
        elif container_type == "session":
            # first extract all files from the session.
            log.debug('working on session')
            files = []
            for acq in fw_object.acquisitions():
                acq = acq.reload()
                files.extend(acq.files)
            object_name = fw_object.label
        
        # Filter by file type, study UID and series UID:
        files = [f for f in files if f.type == "dicom" and f.info.get("StudyInstanceUID") == study_uid and f.info.get("SeriesInstanceUID") == series_uid]
        if len(files) == 0:
            log.warning(f"No dicom files found in session {object_name} with matching study/series UID "
                        f" Dicom Classifier must be run before ROI export.")
            return "NO MATCHES FOUND"
        
        # If we found more than one dicom matching study/series, something is probably wrong...duplicate upload?
        if len(files) > 1:
            log.warning(f"more than 1 file found mathing:\nStudyUID: {study_uid}\nSeriesUID: {series_uid}")
        
        file = files[0]
        acq = file.parent

        # This reads the raw dicom data stream into a pydicom object
        #     (https://github.com/pydicom/pydicom/issues/653#issuecomment-449648844)
        zip_info = acq.get_file_zip_info(file['name'])
        
        # First pass - we will look for a simple string match in the zipped dicom:
        match = [p['path'] for p in zip_info['members'] if sop_uid in p['path']]
        
        if match:
            dicom_file = match[0]
            return dicom_file
        
        # otherwise we have to pull each dicom, read the header, and compare SOP id's.  
        # Do this one zip member by one in the chance that you will find the correct
        # file early on and you don't have to download everything:
        for zip_member in zip_info["members"]:
            raw_dcm = DicomBytesIO(
            acq.read_file_zip_member(file['name'], zip_member.path))
            dcm = pydicom.dcmread(raw_dcm)
            
            if dcm.SOPInstanceUID == sop_uid:
                match = zip_member.path
                return match
        
        log.warning(f"found matching Study and Series UID but no matching SOP uid:\nSTUDY:{study_uid}\tSERIES:{series_uid}\nSOP:{sop_uid}")
        
        return "NO SOP MATCH"
