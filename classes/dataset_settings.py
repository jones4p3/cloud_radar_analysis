from dataclasses import dataclass
from typing import NamedTuple

@dataclass
class TimeRange:
    start_time: str
    end_time: str

@dataclass
class DimensionNames:
    time: str
    height: str
    reflectivity: str

@dataclass
class Dataset:
    """Class to hold dataset information"""
    standard_dimension_names: DimensionNames
    time_range: TimeRange
    figure_folder: str
    files_folder: str
    radar_settings: dict