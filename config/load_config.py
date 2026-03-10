
import os
import xarray as xr
import pandas as pd
from typing import List, Tuple, Dict

# Paths
processing_config_path = "./config/processing_config.json"
dataset_config_path = "./config/dataset_config.json"

def get_days_in_time_range(start_time: pd.Timestamp, end_time: pd.Timestamp) -> Tuple[List[pd.Timestamp], List[str]]:
    """Generates a list of days and their string representations within a given time range.

    Args:
        start_time (pd.Timestamp): The start time of the range.
        end_time (pd.Timestamp): The end time of the range.

    Returns:
        Tuple[List[pd.Timestamp], List[str]]: A tuple containing a list of pd.Timestamp objects for each day and their corresponding string representations in 'YYYYMMDD' format.
    """
    days = pd.date_range(start=start_time, end=end_time, freq='D')
    day_strings = days.strftime('%Y/%m/%d').tolist()
    return days, day_strings

def load_datasets_from_dict(dataset_dict: Dict, stage: str) -> Dict[str,xr.Dataset]:
    """Loads dataset names from a dataset dictionary.

    Args:
        dataset_dict (dict): A dictionary containing dataset information. Keys are radar slugs, and values are dictionaries with dataset details. Especially, each value dictionary should contain an 'output_path_pp' key indicating where the pre-processed data is stored.
        stage (str): The processing stage, e.g., 'pp' for pre-processed data.
    Returns:
        Dict[str, xr.Dataset]: A dictionary of loaded xarray Datasets for each radar.
        """
    if stage == "pre_processed":
        stage_key = "output_path_pp"
    elif stage == "time_matched":
        stage_key = "output_path_tm"
    elif stage == "cloud_detection":
        stage_key = "output_path_cd"
    elif stage == "finished":
        stage_key = "output_path_finished"
    else:
        raise ValueError(f"Unsupported stage: {stage}")
    radars_ds = {}
    for radar_slug, radar_info in dataset_dict.items():
        data_path = radar_info.get(stage_key, None)
        if data_path is None:
            raise ValueError(f"Output path for {stage} data not specified for radar {radar_slug}")
        try:
            file_path = os.path.join(data_path, radar_slug + f'_{stage}.nc')
            ds = xr.open_dataset(file_path, chunks={'time': 'auto', "height": "auto"})
            radars_ds[radar_slug] = ds
            print(f"Loaded dataset for radar {radar_slug} from {file_path}")
        except Exception as e:
            print(f"Error loading dataset for radar {radar_slug} from {file_path}: {e}")
    return radars_ds