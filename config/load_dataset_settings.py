import json
import sys
from classes import Dataset, TimeRange, DimensionNames

def load_dataset_settings(dataset_settings_path: str, radar_settings_dict: dict) -> Dataset:
    try:
        with open(dataset_settings_path, 'r') as file:
            dataset_settings = json.load(file)
        

        # Create a Dataset object with the loaded settings
        dataset = Dataset(
            standard_dimension_names=DimensionNames(**dataset_settings["standard_dimension_names"]),
            time_range=TimeRange(**dataset_settings["time_range"]),
            figure_folder=dataset_settings["figure_folder"],
            files_folder=dataset_settings["files_folder"],
            radar_settings=radar_settings_dict
        )
        return dataset
    except Exception as e:
        print(f"❌ Error loading dataset settings: {e}")
        sys.exit(1)