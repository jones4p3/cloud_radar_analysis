from dataclasses import dataclass, field


@dataclass
class TimeRange:
    start: str
    end: str


@dataclass
class DimensionNames:
    time: str
    height: str
    reflectivity: str


@dataclass
class DaysInTimeRange:
    days: list
    day_strings: list


@dataclass
class Dataset:
    """Class to hold dataset information"""

    standard_dimension_names: DimensionNames
    time_range: TimeRange
    figure_folder: str
    files_folder: str
    radar_settings: dict
    radar_datasets: dict = field(init=False)
    days_in_time_range: DaysInTimeRange = field(init=False)
