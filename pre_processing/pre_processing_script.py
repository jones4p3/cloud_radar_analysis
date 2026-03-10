import xarray as xr
import os

def load_and_preprocess_datasets(radars_to_process, days_in_time_range, dataset_dims):
    radar_datasets = {}  # Initialize an empty dictionary to store the processed datasets for each radar

    # Loading datasets files within specified time range and pre-processing them according to the processing configuration
    for radar_slug, radar_info in radars_to_process.items():
        radar_datasets[radar_slug] = {}  # Initialize a dictionary for this radar's datasets
        print(f"Preparing to process radar: {radar_info['attributes']['radar_name']} ({radar_info['attributes']['frequency']})")
        # Validate data path
        data_path = radar_info.get("data_path", None)
        if not data_path:
            raise ValueError(f"No data_path specified for radar {radar_slug}")
        print(f"Data path for radar {radar_slug}: {data_path}")

        # Grab all file paths
        file_paths_in_time_range = []
        for single_date in days_in_time_range:
            directory_path = os.path.join(data_path, single_date)
            if os.path.exists(directory_path):
                for file_name in os.listdir(directory_path):
                    if file_name.endswith(".nc"):
                        file_paths_in_time_range.append(os.path.join(directory_path, file_name))
        print(f"Found {len(file_paths_in_time_range)} files for radar {radar_slug} in the specified time range.")

        # Load the dataset with xarray based on file paths
        print(f"Loading dataset for radar {radar_slug} with xarray...")
        radar_dims = radar_info.get("dimensions", False)
        if not radar_dims["time"]:
            raise ValueError(f"No time dimension specified for radar {radar_slug}")
        ds = xr.open_mfdataset(file_paths_in_time_range, preprocess= lambda ds: ds.sortby(radar_dims["time"]), data_vars=None, chunks={radar_dims["time"]: "auto", radar_dims["ze"]: "auto"}, engine="h5netcdf")
        print(f"Loaded dataset for radar {radar_slug}")

        # Adding the instrument height to range gates if specified
        add_to_range = radar_info.get("add_to_range", None)
        if add_to_range is False:
            print(f"No instrument height addition specified for radar {radar_slug}")
        elif add_to_range is None:
            raise ValueError(f"Instrument height addition specified as None for radar {radar_slug}")
        else:
            height_var_name = radar_dims.get("height", None)
            if not height_var_name or height_var_name not in ds:
                raise ValueError(f"Height variable not specified or not found in dataset for radar {radar_slug}")
            instrument_height = ds[add_to_range]
            ds[height_var_name] = ds[height_var_name] + instrument_height
            print(f"Added instrument height of {instrument_height.compute().item()} from [{add_to_range}] m to height variable for radar {radar_slug}")

        # Drop unnecessary variables
        vars_to_keep = radar_info.get("vars_to_keep", False)
        if not vars_to_keep:
            print(f"No variables_to_keep specified for radar {radar_slug}, keeping all variables.")
        else:
            print(f"Keeping specified variables for radar {radar_slug}: {vars_to_keep}")
            vars_in_ds = list(ds.data_vars)
            vars_to_drop = [var for var in vars_in_ds if var not in vars_to_keep]
            ds = ds.drop_vars(vars_to_drop)
            print(f"Dropped unnecessary variables for radar {radar_slug}")
    
        # Check for a proper domain in time dimension and indexing
        if ds[radar_dims["time"]].dtype != 'datetime64[s]':
            ds[radar_dims["time"]] = ds[radar_dims["time"]].astype('datetime64[s]')
            print(f"Converted time dimension to datetime64[s] for radar {radar_slug}")
            ds[radar_dims["time"]].attrs.pop("units", None)  # Remove units attribute if exists
    
        is_time_index_unique = ds.indexes[radar_dims["time"]].is_unique
        if not is_time_index_unique:
            ds = ds.sortby(radar_dims["time"]).drop_duplicates(radar_dims["time"])
            print(f"Dropped duplicate time indices for radar {radar_slug}")
    
        # Conversion from mm6 to dBZ if needed
        convertion_needed = radar_info.get("convert_mm6_to_dBZ", False)
        if not convertion_needed:
            print(f"No conversion from mm6 to dBZ needed for radar {radar_slug}")
        else:
            ze_var_name = radar_dims["ze"]
            if not ze_var_name or ze_var_name not in ds:
                raise ValueError(f"Variable for reflectivity (ze) not specified or not found in dataset for radar {radar_slug}")
            ds[ze_var_name] = 10 * xr.ufuncs.log10(ds[ze_var_name])
            print(f"Converted {ze_var_name} from mm6 to dBZ for radar {radar_slug}")
    
        # Renaming dimensions and variables to a standard naming convention
        radar_dimensions = radar_info.get("dimensions", False)
        if not radar_dimensions:
            raise ValueError(f"No dimensions specified for radar {radar_slug}")
    
        for dim, standard_name in zip(radar_dimensions.values(), dataset_dims.values()):
            if dim == standard_name:
                continue  # No need to rename if already standard
            if dim in ds.dims:
                ds = ds.rename_dims({dim: standard_name})
                print(f"Renamed dimension {dim} to {standard_name} for radar {radar_slug}")
            if dim in ds:
                ds = ds.rename_vars({dim: standard_name})
                print(f"Renamed variable {dim} to {standard_name} for radar {radar_slug}")
    
        # Adding attributes to the dataset
        radar_attributes = radar_info.get("attributes", False)
        if radar_attributes:
            for attr_key, attr_value in radar_attributes.items():
                ds.attrs[attr_key] = attr_value
                print(f"Added attribute {attr_key}: {attr_value} to dataset for radar {radar_slug}")
            print(f"Added attributes to dataset for radar {radar_slug}")
    
        # Sanatizing the attributes
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
                print(f"Sanitized attribute {attr_key} for radar {radar_slug}")
        print(f"Checked sanitization attributes for radar {radar_slug}")

        print("-------- TIME RANGE OF THE DATASET --------")
        print(f"Start time: {ds[dataset_dims['time']].min().values}")
        print(f"End time: {ds[dataset_dims['time']].max().values}")
        print("-------------------------------------------")


        # Store the processed dataset in the radar_datasets dictionary
        radar_datasets[radar_slug] = ds
        print(f"Stored processed dataset for radar {radar_slug} in radar_datasets dictionary")
    return radar_datasets