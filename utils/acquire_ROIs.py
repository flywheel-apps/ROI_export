import logging
from pathlib import Path
import json
import pandas as pd


import flywheel

from utils.MyCurator import ROICurator
from utils.MyWalker import MyWalker
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



def acquire_rois(fw, project):
    """
    Acquire the ROI metadata from all the sessions in 'project'
    
    Using a walker and modified curator class, this function walks through a project,
    looking for ohif viewer metadata containing ROI's.  These ROI's are packaged into
    a python dictionary object and returned.
    
    The returned output_dict is subdivided by ROI type.  The supported types are listed
    above as the constant `SUPPORTED_ROIS`.  Each ROI object in the output_roi dict is
    a list of all ROI's on that container of that type.
    
    Args:
        fw (flywheel.Client): the flywheel client
        project (flywheel.Project): the flywheel project

    Returns:
        output_dict (dict): a dictionary of ROI objects

    """

    curator = ROICurator(fw)
    project_walker = MyWalker(project, depth_first=curator.depth_first)

    output_dict = {}

    for container in project_walker.walk():
        container_dict = curator.curate_container(container)
        
        # Every container from this curator will return a dict, but if the keys are
        # empty, that means it didn't find any metadata matching OhifViewer Roi's on
        # that container.  so if it exists and it's not None and it's not empty, it's
        # a real ROI and we should process it.
        if (container_dict and
            container_dict.get("Group") is not None and
            container_dict.get("Group") != []):
            
            for d in container_dict:
                if d in output_dict:
                    output_dict[d].extend(container_dict[d])
                else:
                    output_dict[d] = container_dict[d]

    return output_dict


def save_csv(output_dict, path):
    """
    Saves the list of roi dictionaries into a .csv file
    Args:
        output_dict (list): a list of ROI dictionaries
        path (PathLike): the location to save the .csv file to

    """
    
    # Save without index since that clutters the csv and the ROI's will be unique
    df = pd.DataFrame.from_dict(output_dict)
    df.to_csv(path, index=False)