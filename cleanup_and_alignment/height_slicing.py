import numpy as np

def slice_height_range(data, params):
    debug = params.debug
    highest_minimum_height = {"radar": "", "height": -np.inf}
    lowest_maximum_height = {"radar": "", "height": np.inf}
    for radar, ds in data.radar_datasets.items():
        print(f"  ---------------- Processing radar: {radar} ----------------")
        height = ds["height"].values
        min_height = height.min()
        max_height = height.max()
        print(f"    Min height: {min_height} m")
        print(f"    Max height: {max_height} m")
        if min_height > highest_minimum_height["height"]:
            highest_minimum_height["radar"] = radar
            highest_minimum_height["height"] = min_height
        if max_height < lowest_maximum_height["height"]:
            lowest_maximum_height["radar"] = radar
            lowest_maximum_height["height"] = max_height
    if debug:
        print(
            f"Radar with lowest min height: {highest_minimum_height['radar']} at {highest_minimum_height['height']} m"
        )
        print(
            f"Radar with highest max height: {lowest_maximum_height['radar']} at {lowest_maximum_height['height']} m"
        )

    # Slcing the dataset to common height range
    common_min_height = highest_minimum_height["height"]
    common_max_height = lowest_maximum_height["height"]
    print(
        f"Common height range for all radars: {common_min_height} m to {common_max_height} m"
    )

    for radar, ds in data.radar_datasets.items():
        if debug:
            print(f"  ---------------- Slicing radar: {radar} ----------------")
        height_size = ds["height"].size
        height_1d = np.asarray(ds["height"].values).squeeze()
        idx = np.where(
            (height_1d >= common_min_height) & (height_1d <= common_max_height)
        )[0]
        i0, i1 = idx[0], idx[-1] + 1  # +1 to include the last index

        # Mask the heights within the common range
        ds_sliced = ds.isel(height=slice(i0, i1))
        new_min_height = ds_sliced["height"].min().values
        new_max_height = ds_sliced["height"].max().values
        if debug:
            print(f"Original height size: {height_size} gates")
            print(f"Sliced height size: {ds_sliced['height'].size} gates")
            print(f"    New min height: {new_min_height} m")
            print(f"    New max height: {new_max_height} m")
        data.radar_datasets[radar] = ds_sliced
        
    return data, highest_minimum_height, lowest_maximum_height