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

    curator = ROICurator(fw)
    project_walker = MyWalker(project, depth_first=curator.depth_first)

    output_dict = {}

    for container in project_walker.walk():
        container_dict = curator.curate_container(container)

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
    df = pd.DataFrame.from_dict(output_dict)
    df.to_csv(path)