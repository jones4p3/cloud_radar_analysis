from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class CloudStatisticsSettings:
    time_range: Optional[Tuple[str, str]] = None  # e.g., ("2025-02-01", "2025-02-28")
    radars_to_test: Optional[str] = None  # e.g., "grawac167"
    show_plots: bool = True
    output_folder: str = "cloud_statistics"
    debug: bool = False

@dataclass
class PlotSettings:
    figsize: Tuple[int, int] = (12, 6)
    output_folder: str = "cloud_statistics_plots"
    height_bin_size: Optional[int] = None # in meters
    title: Optional[str] = "Set title for the plot"
    xlabel: Optional[str] = None 
    ylabel: Optional[str] = None
    legend: bool = True