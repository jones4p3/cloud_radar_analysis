from dataclasses import dataclass

@dataclass
class RadarSettings:
    """Class to hold radar settings information"""
    slug: str
    data_path: str
    attributes: dict
    convert_linear_to_dBZ: bool
    add_to_range: bool
    vars_to_keep: list
    dimension_names: dict