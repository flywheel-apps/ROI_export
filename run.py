from pathlib import Path
import pathvalidate as pv
import sys
from datetime import datetime

import flywheel
import flywheel_gear_toolkit as gt

from utils import acquire_ROIs as ar, import_data as id


def main(context):
    
    #fw = flywheel.Client()
    config = context.config
    for inp in context.config_json["inputs"].values():
        if inp["base"] == "api-key" and inp["key"]:
            api_key = inp["key"]

    fw = flywheel.Client(api_key)
    
    # Setup basic logging and log the configuration for this job
    if config["gear_log_level"] == "INFO":
        context.init_logging("info")
    else:
        context.init_logging("debug")
    context.log_config()
    log = context.log
    
    dry_run = config.get('dry-run', False)
    log.debug(f"dry_run is {dry_run}")
    

    ids = config.get("Subject IDs", None)
    if ids:
        log.debug(f"Getting ROI's from subjects {ids}")
        ids = ids.split(',')
    
    
    try:
    
        destination_id = context.destination.get('id')
        dest_container = fw.get(destination_id)
        project = fw.get_project(dest_container.parents.project)

        od = ar.acquire_rois(fw, project)
        
        output_path = Path(context.output_dir)/f"{project.label}_ROIs_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
        report_output = context.output_dir
        id.save_df_to_csv(od, report_output)
    
    except Exception as e:
        log.exception(e)
        return 1
     
    return 0
    


if __name__ == "__main__":
    
    result = main(gt.GearToolkitContext())
    sys.exit(result)

