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
class Parameters:
    """Class to hold parameters for the analysis"""
    sensitivity: SensitivityParameters
    occurrence: OccurrenceParameters
    uptime_alignment: UptimeAlignmentParameters