import xarray as xr
from .utils import *


def load_and_preprocess_datasets(data):
    # Initialize an empty dictionary to store the processed datasets for each radar
    radar_datasets = {}

    # Add days in time range for folder navigation and file loading
    data.days_in_time_range = get_days_in_time_range(data.time_range)

    # Loading dataset files within specified time range and pre-processing them
    for _, radar in data.radar_settings.items():
        # Initialize key for this radar's datasets
        radar_datasets[radar.slug] = {}
        print(
            f"💻 Preparing to process radar: {radar.attributes.name} - {radar.attributes.band}"
        )

        # Grab all file paths
        file_paths = create_file_paths_list(radar, data, endswith=".nc")

        # Load the dataset with xarray based on file paths
        print(f"⏱️ Loading dataset for radar {radar.slug} with xarray...")
        ds = xr.open_mfdataset(
            file_paths,
            preprocess=lambda ds: ds.sortby(radar.dimension_names.time),
            data_vars=None,
            chunks={
                radar.dimension_names.time: "auto",
                radar.dimension_names.ze: "auto",
            },
            engine="h5netcdf",
        )
        print(f"⏱️ ✅ Loaded dataset for radar {radar.slug}")

        # Adding the instrument height to range gates if specified
        ds = adding_instrument_height(radar, ds)

        # Drop unnecessary variables
        ds = drop_variables(radar, ds)

        # Convert time dimension to datetime64[s] if not already in that format and ensure it is unique
        ds = check_time_dimension(radar, ds)

        # Conversion from mm6 to dBZ if needed
        ds = convert_linear_to_dBZ(radar, ds)

        # Renaming dimensions and variables to a standard naming convention
        ds = rename_to_standard_naming_convention(radar, data, ds)

        # Adding attributes to the dataset
        ds = add_attributes(radar, ds)

        # Sanatizing the attributes
        ds = sanitize_attributes(radar, ds)

        # Store the processed dataset in the radar_datasets dictionary
        radar_datasets[radar.slug] = ds
        print(f"✅ Finished processing dataset for radar {radar.slug}\n")
    
    data.radar_datasets = radar_datasets
    return data