import pandas as pd
import xarray as xr
import os
from classes import TimeRange, DaysInTimeRange
from dataclasses import asdict


def get_days_in_time_range(time_range: TimeRange):
    start_time, end_time = time_range.start, time_range.end
    days_pd = pd.date_range(start=start_time, end=end_time, freq="D")
    day_strings = days_pd.strftime("%Y/%m/%d").tolist()
    days_in_time_range = DaysInTimeRange(days=days_pd, day_strings=day_strings)
    return days_in_time_range


def create_file_paths_list(radar, data, endswith=".nc"):
    file_paths_in_time_range = []
    data_path = radar.data_path
    print(f"Data path for radar {radar.slug}: {data_path}")
    for single_date in data.days_in_time_range.day_strings:
        directory_path = os.path.join(data_path, single_date)
        if os.path.exists(directory_path):
            for file_name in os.listdir(directory_path):
                if file_name.endswith(endswith):
                    file_paths_in_time_range.append(
                        os.path.join(directory_path, file_name)
                    )
    print(
        f"Found {len(file_paths_in_time_range)} files ending with '{endswith}' for radar {radar.slug} in the specified time range."
    )
    return file_paths_in_time_range


def adding_instrument_height(radar, ds):
    if radar.add_to_range is False:
        print(f"No instrument height addition specified for radar {radar.slug}")
    elif radar.add_to_range is None:
        raise ValueError(
            f"Instrument height addition specified as None for radar {radar.slug}"
        )
    else:
        height_var_name = radar.dimension_names.height
        if not height_var_name or height_var_name not in ds:
            raise ValueError(
                f"Height variable not specified or not found in dataset for radar {radar.slug}"
            )
        instrument_height = ds[radar.add_to_range]
        ds[height_var_name] = ds[height_var_name] + instrument_height
        print(
            f"Added instrument height of {instrument_height.compute().item()} from [{radar.add_to_range}] m to height variables for radar {radar.slug}"
        )
    return ds


def drop_variables(radar, ds):
    vars_to_keep = radar.vars_to_keep
    if not vars_to_keep:
        print(
            f"No variables_to_keep specified for radar {radar.slug}, keeping all variables."
        )
    else:
        print(f"Keeping specified variables for radar {radar.slug}: {vars_to_keep}")
        vars_in_ds = list(ds.data_vars)
        vars_to_drop = [var for var in vars_in_ds if var not in vars_to_keep]
        ds = ds.drop_vars(vars_to_drop)
        print(f"Dropped unnecessary variables for radar {radar.slug}")
    return ds


def check_time_dimension(radar, ds):
    time_dim = radar.dimension_names.time
    if ds[time_dim].dtype != "datetime64[s]":
        ds[time_dim] = ds[time_dim].astype("datetime64[s]")
        print(f"Converted time dimension to datetime64[s] for radar {radar.slug}")
        ds[time_dim].attrs.pop("units", None)  # Remove units attribute if exists

    is_time_index_unique = ds.indexes[time_dim].is_unique
    if not is_time_index_unique:
        ds = ds.sortby(time_dim).drop_duplicates(time_dim)
        print(f"Dropped duplicate time indices for radar {radar.slug}")
    return ds


def convert_linear_to_dBZ(radar, ds):
    convertion_needed = radar.convert_linear_to_dBZ
    if not convertion_needed:
        print(f"No conversion from mm6 to dBZ needed for radar {radar.slug}")
    else:
        ze_var_name = radar.dimension_names.ze
        if not ze_var_name or ze_var_name not in ds:
            raise ValueError(
                f"Variable for reflectivity (ze) not specified or not found in dataset for radar {radar.slug}"
            )
        ds[ze_var_name] = 10 * xr.ufuncs.log10(ds[ze_var_name])
        print(f"Converted {ze_var_name} from mm6 to dBZ for radar {radar.slug}")
    return ds


def rename_to_standard_naming_convention(radar, data, ds):
    radar_dimensions = asdict(radar.dimension_names)
    dataset_dims = asdict(data.standard_dimension_names)

    for radar_dim, standard_name in zip(
        radar_dimensions.values(), dataset_dims.values()
    ):
        if radar_dim == standard_name:
            continue  # No need to rename if already standard
        if radar_dim in ds.dims:
            ds = ds.rename_dims({radar_dim: standard_name})
            print(
                f"Renamed dimension {radar_dim} to {standard_name} for radar {radar.slug}"
            )
        if radar_dim in ds:
            ds = ds.rename_vars({radar_dim: standard_name})
            print(
                f"Renamed variable {radar_dim} to {standard_name} for radar {radar.slug}"
            )
    return ds

def add_attributes(radar, ds):
    radar_attributes = asdict(radar.attributes)
    if radar_attributes:
        for attr_key, attr_value in radar_attributes.items():
            ds.attrs[attr_key] = attr_value
            print(f"Added attribute {attr_key}: {attr_value} to dataset for radar {radar.slug}")
        print(f"Added attributes to dataset for radar {radar.slug}")
    return ds

def sanitize_attributes(radar, ds):
    for attr_key, attr_value in ds.attrs.items():
        is_clean = False
        try:
            attr_value.encode('utf-8')
            is_clean = True
        except UnicodeEncodeError:
            is_clean = False
        if not is_clean:
            attr_value = attr_value.encode('utf-8', 'replace').decode('utf-8')
            ds.attrs[attr_key] = attr_value
            print(f"Sanitized attribute {attr_key} for radar {radar.slug}")
    print(f"Checked sanitization attributes for radar {radar.slug}")
    return ds