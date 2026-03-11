from dataclasses import dataclass

@dataclass
class SensitivityParameters:
    """Class to hold parameters for sensitivity calculation"""
    threshold: float
    min_samples_per_height: float

@dataclass
class OccurrenceParameters:
    """Class to hold parameters for occurrence calculation"""
    bin_size: float

@dataclass
class UptimeAlignmentParameters:
    """Class to hold parameters for uptime alignment"""
    sampling_interval_in_minutes: int
    max_sampling_time_in_seconds: int
    threshold_for_uptime: float

@dataclass
class CloudDetectionParameters:
    """Class to hold parameters for cloud detection algorithm"""
    use_fixed_threshold: bool
    fixed_threshold_in_dBZ: float
    sensitivity_add_in_dBZ: float
    min_cloud_thickness_in_m: list[int]
    min_layer_spacing_in_m: list[int]

@dataclass
class Parameters:
    """Class to hold parameters for the analysis"""
    sensitivity: SensitivityParameters
    occurrence: OccurrenceParameters
    uptime_alignment: UptimeAlignmentParameters
    cloud_detection: CloudDetectionParameters
    debug: bool