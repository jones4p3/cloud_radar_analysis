import numpy as np
def get_ze_min_max_from_radars(radar_datasets):
    """
    Get the global minimum and maximum reflectivity (Ze) value across multiple radar datasets.

    Parameters:
    radar_datasets (dict): A dictionary where keys are radar names and values are xarray Datasets containing 'ze' variable.

    Returns:
    tuple: A tuple containing the global minimum and maximum Ze values.
    """
    global_ze_min = np.inf
    global_ze_max = -np.inf

    for radar_handle, ds in radar_datasets.items():
        ze = ds["ze"].values
        ze_min = np.nanmin(ze)
        ze_max = np.nanmax(ze)

        if ze_min < global_ze_min:
            global_ze_min = ze_min
            print(f"New global minimum Ze found: {global_ze_min} dBZ from radar {radar_handle}")
        if ze_max > global_ze_max:
            global_ze_max = ze_max
            print(f"New global maximum Ze found: {global_ze_max} dBZ from radar {radar_handle}")

    return global_ze_min, global_ze_max