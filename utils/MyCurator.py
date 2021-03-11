import copy
import logging
from pathlib import Path
from pprint import pprint
import json

import flywheel

from flywheel_gear_toolkit.utils import curator
from flywheel_gear_toolkit.utils.datatypes import Container

POSSIBLE_KEYS = ["ohifViewer", "roi"]
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
    "File Name": [],
    "File Type": [],
    "Label": [],
    "Description": [],
    "Xmin": [],
    "Xmax": [],
    "Ymin": [],
    "Ymax": [],
    "User": [],
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
        """Curates a generic container.

        Args:
            container (Container): A Flywheel container.
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

    def get_file_hierarchy(self, container):

        group_label = container.parent.parents.group

        project_id = container.parent.parents.project
        project_label = self.fw.get_project(project_id).label

        subject_id = container.parent.parents.subject
        if subject_id:
            subject_label = self.fw.get_subject(subject_id).label
        else:
            subject_label = None

        session_id = container.parent.parents.session
        if session_id:
            session_label = self.fw.get_session(session_id).label
        else:
            session_label = None

        acquisition_id = container.parent.parents.acquisition
        if acquisition_id:
            acquisition_label = self.fw.get_acquisition(acquisition_id).label
        else:
            if container.parent.container_type == "acquisition":
                acquisition_label = container.parent.label
            else:
                acquisition_label = None

        return (
            group_label,
            project_label,
            subject_label,
            session_label,
            acquisition_label,
        )

    def get_session_hierarchy(self, session, namespace):

        file_id = namespace.get("seriesInstanceUid")
        if file_id is None:
            log.error("No seriesInstanceUid for ROI")
            return [None]*7

        acquisitions = session.acquisitions()
        files = []
        for a in acquisitions:
            files.extend(a.reload().files)

        my_file = [f for f in files if f.info.get("SeriesInstanceUID","").replace('_','.') == file_id]

        if len(my_file) == 0:
            log.warning("No files match series instance UID")
            return [None]*7

        elif len(my_file) > 1:
            log.warning("Multiple matches for series uid")

        my_file = my_file[0]

        file_name = Path(my_file.name)
        suffix = "".join(file_name.suffixes[-2:])
        file_type = KNOWN_EXTENSIONS.get(suffix, suffix[1:])

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

    def update_output_dict(self, output_dict, **kwargs):
        pass

    def process_namespace_roi(
        self,
        roi_namespace,
        output_dict,
        file
    ):

        for roi in roi_namespace:
            print(roi)
            roi_type = roi.get("toolType")
            if roi_type == "rectangleRoi" or roi_type == "ellipticalRoi":
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
                output_dict["File Name"].append(file_name)
                output_dict["File Type"].append(file_type)
                
                output_dict["Label"].append(label)
                output_dict["Description"].append(description)
                
                output_dict["Xmin"].append(x_start)
                output_dict["Xmax"].append(x_end)
                output_dict["Ymin"].append(y_start)
                output_dict["Ymax"].append(y_end)

                output_dict["area"].append(cached_stats.get('area', 0))
                output_dict["count"].append(cached_stats.get('count', 0))
                output_dict["max"].append(cached_stats.get('max', 0))
                output_dict["mean"].append(cached_stats.get('mean', 0))
                output_dict["min"].append(cached_stats.get('min', 0))
                output_dict["stdDev"].append(cached_stats.get('stdDev', 0))
                output_dict["variance"].append(cached_stats.get('variance', 0))
                
                output_dict["User"].append(user_origin)
                output_dict["ROI type"].append(roi_type)

        return output_dict

    def process_namespace_ohifViewer(
        self,
        session,
        roi_namespace,
        output_dict,

    ):

        for roi_type in roi_namespace.keys():

            if roi_type in SUPPORTED_ROIS:
                roi_type_namespace = roi_namespace.get(roi_type, {})

                for roi in roi_type_namespace:
                    (
                        group_label,
                        project_label,
                        subject_label,
                        session_label,
                        acquisition_label,
                        file_name,
                        file_type,
                    ) = self.get_session_hierarchy(session, roi)
                    
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

                    if group_label is None:
                        log.info('Unable to find matching file for ROI')
                        continue

                    output_dict["Group"].append(group_label)
                    output_dict["Project"].append(project_label)
                    output_dict["Subject"].append(subject_label)
                    output_dict["Session"].append(session_label)
                    output_dict["Acquisition"].append(acquisition_label)
                    
                    output_dict["File Name"].append(file_name)
                    output_dict["File Type"].append(file_type)
                    
                    output_dict["Label"].append(label)
                    output_dict["Description"].append(description)
                    
                    output_dict["Xmin"].append(x_start)
                    output_dict["Xmax"].append(x_end)
                    output_dict["Ymin"].append(y_start)
                    output_dict["Ymax"].append(y_end)
                    
                    output_dict["area"].append(cached_stats.get('area', 0))
                    output_dict["count"].append(cached_stats.get('count', 0))
                    output_dict["max"].append(cached_stats.get('max', 0))
                    output_dict["mean"].append(cached_stats.get('mean', 0))
                    output_dict["min"].append(cached_stats.get('min', 0))
                    output_dict["stdDev"].append(cached_stats.get('stdDev', 0))
                    output_dict["variance"].append(cached_stats.get('variance', 0))
                    
                    output_dict["User"].append(user_origin)
                    
                    output_dict["ROI type"].append(roi_type)

        return output_dict

    def process_generic_roi(self, roi):
        description = roi.get("description")
        label = roi.get("location")
        timestamp = roi.get("updatedAt")

        if label is None:
            label = roi.get("label")

        handles = roi.get("handles", {})
        start = handles.get("start", {})
        end = handles.get("end", {})

        exs = (start.get("x"), end.get("x"))
        whys = (start.get("y"), end.get("y"))
        x_start = min(exs)
        y_start = min(whys)

        x_end = max(exs)
        y_end = max(whys)

        user_origin = roi.get("updatedById")
        if user_origin is None:
            user_origin = roi.get("flywheelOrigin", {}).get("id")
            
        cached_stats = roi.get('cachedStats', {})
        log.debug(pprint(cached_stats, indent=2))

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

        log.info(f"curating session {session.label}")

        output_dict = copy.deepcopy(OUTPUT_TEMPLATE)
        session = session.reload()
        session_info = session.info

        for pk in POSSIBLE_KEYS:
            log.info(f"checking {pk} in {session_info.keys()}")
            if pk in session_info:
                log.info("Found")
                if pk == "ohifViewer":
                    log.info('OHIFVIWER')
                    namespace = session_info.get(pk, {}).get("measurements", {})

                    output_dict = self.process_namespace_ohifViewer(session, namespace, output_dict)
   
                    
                              
                            
        return output_dict

    def curate_file(self, file: flywheel.FileEntry):
        log.info(f"curating file {file.name}")

        output_dict = copy.deepcopy(OUTPUT_TEMPLATE)

        for pk in POSSIBLE_KEYS:
            log.debug(f"checking {pk} in {file.info.keys()}")
            if pk in file.info:

                log.info("FOUND")


                if pk == "roi":
                    namespace = file.info.get(pk, {})
                    output_dict = self.process_namespace_roi(
                        namespace,
                        output_dict,
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
                        log.info('file is not at acquisition level, skipping')
                        continue
                    session = fw.get_session(parent_ses)
                    output_dict = self.process_namespace_ohifViewer(session, namespace, output_dict)

                    # for d in temp_dict:
                    #     if d in output_dict:
                    #         output_dict[d].extend(temp_dict[d])
                    #     else:
                    #         output_dict[d] = temp_dict[d]

        return output_dict



