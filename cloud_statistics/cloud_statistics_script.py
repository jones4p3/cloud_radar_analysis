import os

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

def calculate_cloud_statistics(data):
    for radar_slug, ds in data.radar_datasets.items():
        print(f"Radar: {radar_slug}")
        n_layers = ds["n_layers"]
        # Define resampling interval
        interval_step = "1D"

        # Calculate clear sky, cloudiness, and multilayer fractions
        clear_sky_interval_count = (n_layers == 0).resample(time=interval_step).sum(dim="time") # n_layers == 0 indicates clear sky
        cloudiness_interval_count = (n_layers > 0).resample(time=interval_step).sum(dim="time") # n_layers > 0 indicates at least 1 cloud layer is present
        multilayer_interval_count = (n_layers > 1).resample(time=interval_step).sum(dim="time") # n_layers > 1 indicates multilayer clouds more or equal 2 layers

        # Calculate precipitation fractions relative to cloudiness
        # Asssuming precipitation is given, when cloud_base (time, layer) is at gate 0, assuming precipitation reaching the ground
        precipitation_gate = 0
        precipitation_event = ((ds["cloud_base_gate"] == precipitation_gate).any(dim="layer")) & (n_layers > 0) # Count precipitation event if any layer has cloud_base_gate == 0
        precipitation_interval_count = precipitation_event.resample(time=interval_step).sum(dim="time")
    

        # Calculate total samples in each interval
        total_interval_samples = n_layers.resample(time=interval_step).count(dim="time") # Only counting time samples in the interval, done once as they are the same for all conditions
        total_interval_samples = total_interval_samples.where(total_interval_samples > 0, other=1) # Avoid division by zero

        # Calculate fractions
        clear_sky_fraction = clear_sky_interval_count / total_interval_samples
        cloudiness_fraction = cloudiness_interval_count / total_interval_samples
        precipitation_fraction = precipitation_interval_count / cloudiness_interval_count.where(cloudiness_interval_count > 0, other=1) # relative to cloudiness
        multilayer_fraction = multilayer_interval_count / total_interval_samples

        # Adding to the dataset for potential further analysis
        # Renaming time dimension to avoid conflicts
        clear_sky_fraction = clear_sky_fraction.rename({"time": "time_interval"})
        cloudiness_fraction = cloudiness_fraction.rename({"time": "time_interval"})
        precipitation_fraction = precipitation_fraction.rename({"time": "time_interval"})
        multilayer_fraction = multilayer_fraction.rename({"time": "time_interval"})

        # Assign new coordinate for time intervals
        ds = ds.assign_coords(time_interval=clear_sky_fraction["time_interval"])
        ds["time_interval"].attrs.update({"description": f"Time intervals of {interval_step} for fraction calculations"})

        # Adding fractions to dataset
        ds[f"clear_sky_fraction"] = clear_sky_fraction
        ds[f"cloudiness_fraction"] = cloudiness_fraction
        ds[f"precipitation_fraction"] = precipitation_fraction
        ds[f"multilayer_fraction"] = multilayer_fraction

        # Adding counts to dataset
        clear_sky_interval_count = clear_sky_interval_count.rename({"time": "time_interval"})
        cloudiness_interval_count = cloudiness_interval_count.rename({"time": "time_interval"})
        precipitation_interval_count = precipitation_interval_count.rename({"time": "time_interval"})
        multilayer_interval_count = multilayer_interval_count.rename({"time": "time_interval"})
        total_interval_samples = total_interval_samples.rename({"time": "time_interval"})
        ds[f"clear_sky_interval_count"] = clear_sky_interval_count
        ds[f"cloudiness_interval_count"] = cloudiness_interval_count
        ds[f"precipitation_interval_count"] = precipitation_interval_count
        ds[f"multilayer_interval_count"] = multilayer_interval_count

        # ---------------------------------
        # CLOUD FRACTION
        # ---------------------------------
        print(f"Processing cloud fraction per height for radar: {radar_slug}")
        cloud_base = ds["cloud_base_gate"]
        cloud_top = ds["cloud_top_gate"]
        # range_gate_sizes = ds["range_gate_size_in_m"]  # Size of each height gate in meters

        # Create a mask for cloud presence
        cloud_presence = cloud_base.notnull() & cloud_top.notnull()


        # Create a height grid
        n_gates = ds.sizes["height"]
        height_gates = xr.DataArray(np.arange(n_gates), dims=["height"], coords={"height": ds["height"]})

        # Filter height grid to only include heights within cloud layers
        clouds_in_height = cloud_presence & (cloud_base <= height_gates) & (cloud_top >= height_gates) # (cloud yes, no) & (above base) & (below top)

        # Collapse layers from (time, layer, height) to (time, height). Any layer with cloud presence counts as cloud presence at that height, multiple layers possible and counted once
        cloud_in_gate = clouds_in_height.any(dim="layer")
    
        # Cloud fraction per height gate in interval
        cloud_fraction_per_interval = cloud_in_gate.resample(time=interval_step).mean(dim="time")
        # # Cloud fraction over campaign
        cloud_fraction_campaign = cloud_in_gate.mean(dim="time")

        # Add it to the dataset
        ds["cloud_in_gate"] = cloud_in_gate
        ds["cloud_in_gate"].attrs.update({
            "description": "Boolean mask indicating cloud presence in each height gate",
            "units": "1 (cloud present), 0 (no cloud)"
        })

        data.radar_datasets[radar_slug] = ds

    print("--- Finished cloud statistics calculation for all radars ---")


    # ---------------------------------
    # BINNING
    # ---------------------------------

    vars_to_bin = ["cloud_base_in_m", "cloud_top_in_m", "cloud_thickness_in_m"]

    # Binning the cloud thickness
    bin_size = 100  # Bin size in meters
    max_thickness = -np.inf
    max_height = -np.inf
    for radar_slug, ds in data.radar_datasets.items():
        max_ds  = ds["cloud_thickness_in_m"].max()
        max_height_ds = ds["cloud_top_in_m"].max()
        if max_height_ds > max_height:
            max_height = max_height_ds
            print(f"{radar_slug}: New max height found: {max_height.values} m")
        if max_ds > max_thickness:
            max_thickness = max_ds
            print(f"{radar_slug}: New max thickness found: {max_thickness.values} m")

    # Binning edges and centers
    thickness_bin_edges = np.arange(0, max_thickness + bin_size, bin_size)
    thickness_bin_centers = (thickness_bin_edges[:-1] + thickness_bin_edges[1:]) / 2

    height_bin_edges = np.arange(0, max_height + bin_size, bin_size)
    height_bin_centers = (height_bin_edges[:-1] + height_bin_edges[1:]) / 2

    for (radar_slug, ds) in data.radar_datasets.items():
        for var in vars_to_bin:
            print(f"Calculating binned {var} for radar: {radar_slug}")
            # Extract cloud values as a 1D array
            cloud_propertie = ds[var].values.ravel()
            valid_mask = np.isfinite(cloud_propertie) & (cloud_propertie > 0)
            valid_propertie = cloud_propertie[valid_mask]

            # Bin the cloud thickness values
            if var == "cloud_thickness_in_m":
                bin_edges = thickness_bin_edges
                dim_name = "thickness_bin"
                coords = thickness_bin_centers
            else:
                bin_edges = height_bin_edges
                dim_name = "height_bin"
                coords = height_bin_centers

        
            binned_counts, _ = np.histogram(valid_propertie, bins=bin_edges)

            # Normalize to get fraction
            cloud_propertie_fraction = binned_counts / binned_counts.sum()
            print(f"Fraction check sum for {var}: {cloud_propertie_fraction.sum()} for radar: {radar_slug}")
            # Create xarray DataArray for binned cloud thickness fraction
            cloud_propertie_da = xr.DataArray(
                cloud_propertie_fraction,
                dims=[dim_name],
                coords={dim_name: coords},
                name=f"{var}_fraction_binned",
                attrs={
                    "description": f"{var.replace('_', ' ').capitalize()} fraction binned in {bin_size} m bins",
                    "units": "fraction (0-1)"
                }
            )

            ds[f"{var}_fraction_binned"] = cloud_propertie_da
            data.radar_datasets[radar_slug] = ds

    # ---------------------------------
    # BINNING PER LAYER
    # ---------------------------------

    # layers_to_process = [1, 2, 3, 4]
    layers_to_process = [1,2,3,4]
    var_to_plot = ["cloud_base_in_m", "cloud_top_in_m", "cloud_thickness_in_m"]

    # Itterating thorugh each layer
    for layer in layers_to_process:
        print(f"Processing layer: {layer}")
        max_height = -np.inf
        max_thickness = -np.inf


        # Grabbing max height and thickness for the specific layer
        for radar_slug, ds in data.radar_datasets.items():
            # n_layers = n_layers_dict[radar_slug] # Holds the information of number of layers per time step (e.g a scenario where 2 layer where detected at time t, n_layers[t] == 2) 
            # layer_mask = (n_layers >= layer) # Grabs time steps where equal or more 'layer' layers are present

            # # Select data for the specific layer
            # layer_ds = ds.isel(time=np.where(layer_mask)[0]).sel(layer=layer)

            max_height_ds = ds["cloud_top_in_m"].sel(layer=layer).max(skipna=True) 
            max_thickness_ds = ds["cloud_thickness_in_m"].sel(layer=layer).max(skipna=True)
            if max_height_ds > max_height:
                max_height = max_height_ds
                print(f"{radar_slug} Layer {layer}: New max height found: {max_height.values} m")
            if max_thickness_ds > max_thickness:
                max_thickness = max_thickness_ds
                print(f"{radar_slug} Layer {layer}: New max thickness found: {max_thickness.values} m")
        print(f"Final max height for layer {layer}: {max_height.values} m")
        print(f"Final max thickness for layer {layer}: {max_thickness.values} m")

        # Iterate over variables to plot
        for var in var_to_plot:
            # Get the binning for each layer and variable
            # Binning edges and centers
            thickness_bin_edges = np.arange(0, max_thickness + bin_size, bin_size)
            thickness_bin_centers = (thickness_bin_edges[:-1] + thickness_bin_edges[1:]) / 2
            height_bin_edges = np.arange(0, max_height + bin_size, bin_size)
            height_bin_centers = (height_bin_edges[:-1] + height_bin_edges[1:]) / 2

            # Binning the cloud properties for each radar
            for (radar_slug, ds) in data.radar_datasets.items():
                print(f"Calculating binned {var} for radar: {radar_slug}, layer: {layer}")
                # n_layers = n_layers_dict[radar_slug]
                # layer_mask = (n_layers >= layer) # Select time steps where at least 'layer' layers are present
                # layer_ds = ds.isel(time=np.where(layer_mask)[0]).sel(layer=layer)
                # Extract cloud property values as a 1D array
                cloud_propertie = ds[var].sel(layer=layer).values.ravel() # Selects the cloud property for the specific layer and flattens it to 1D
                valid_mask = np.isfinite(cloud_propertie) & (cloud_propertie > 0)
                valid_propertie = cloud_propertie[valid_mask]

                # Bin the cloud property values
                if var == "cloud_thickness_in_m":
                    bin_edges = thickness_bin_edges
                    dim_name = "thickness_bin"
                    coords = thickness_bin_centers
                else:
                    bin_edges = height_bin_edges
                    dim_name = "height_bin"
                    coords = height_bin_centers
                binned_counts, _ = np.histogram(valid_propertie, bins=bin_edges)

                # Normalize to get fraction relative to all valid signals in all layers
                # total_var = ds[f"{var}_fraction_binned"].sum().values # Total valid signals for the variable across all layers, used for normalization
                cloud_propertie_fraction = binned_counts / binned_counts.sum() # Normalize to get fraction relative to valid signals in the specific layer, so we can compare the distribution between layers without the influence of different number of valid signals in each layer

                print(f"Fraction check sum: {cloud_propertie_fraction.sum()} for radar: {radar_slug}, layer: {layer}, variable: {var}")

                # Create xarray DataArray for binned cloud property fraction
                cloud_propertie_da = xr.DataArray(
                    cloud_propertie_fraction,
                    dims=[dim_name],
                    coords={dim_name: coords},
                    name=f"{var}_fraction_binned_layer_{layer}",
                    attrs={
                        "description": f"{var.replace('_', ' ').capitalize()} fraction for layer {layer} binned in {bin_size} m bins",
                        "units": "fraction (0-1)"
                    }
                )
                title = var.split("_in_")[0]
                ds[f"{title}_fraction_binned_layer_{layer}"] = cloud_propertie_da

                data.radar_datasets[radar_slug] = ds

    # ---------------------------------
    # SAVING FILE TEST
    # ---------------------------------
    for radar_slug, ds in data.radar_datasets.items():
        save_path = os.path.join(data.files_folder, f"{radar_slug}_with_statistics.nc")
        print(f"Saving dataset with statistics for radar: {radar_slug} to {save_path}")
        ds.to_netcdf(save_path, engine="h5netcdf")
        print(f"✅ Dataset with statistics saved for radar: {radar_slug}")

    # ---------------------------------
    # CLOUD LAYER DISTRIBUTION
    # ---------------------------------
    grouped_bar_plot_data = {}
    layer_counts_per_radar = {}

    for (radar_slug, ds) in data.radar_datasets.items():
        print(f"Preparing grouped bar plot data for radar: {radar_slug}")
        band = ds.attrs.get("band", "Unknown Band")
        # Extract number of layers
        n_layers = ds["n_layers"]
        max_layers = int(n_layers.max().values)
        print(f"Max number of layers in dataset: {max_layers}")
    
        # Calculate counts and fractions
        layer_counts = []
        total_counts = len(n_layers)

        for layer_num in range(0, max_layers + 1):
            count = (n_layers == layer_num).sum().values
            layer_counts.append(count)

        layer_fractions = [count / total_counts for count in layer_counts]  # Convert to percentage
        # print(f"Layer fractions for {band}: {layer_fractions}")
        grouped_bar_plot_data[band] = layer_fractions
        layer_counts_per_radar[band] = layer_counts

    for layer_idx, layer in enumerate(layer_fractions):
        print(f"Layer {layer_idx}: ")
        for band, fractions in grouped_bar_plot_data.items():
            print(f"{band}: {(fractions[layer_idx]*100):.6f}%")

    for band, counts in layer_counts_per_radar.items():
        print(f"Layer counts for {band}: {counts}")

    x_labels = ["Clear-sky", "1 Layer", "2 Layers", "3 Layers", "4 Layers", "5 Layers", "6 Layers", "7 Layers", "8 Layers"]
    plot_colors = plt.get_cmap("tab10").colors

    # Filter out layers, remove 5 upwards
    up_to_layer = 5
    filtered_data = grouped_bar_plot_data.copy()
    for band in grouped_bar_plot_data.keys():
        filtered_data[band] = grouped_bar_plot_data[band][:up_to_layer]  # Keep only up to 4 layers
    x_location = np.arange(len(x_labels[:up_to_layer]))
    bar_width = 0.2
    multiplier = 0

    fig, ax = plt.subplots(figsize=(8, 4.5))

    for band, fractions in filtered_data.items():
        offset = bar_width * multiplier
        fractions = np.array(fractions) * 100  # Convert to percentage
        rects = ax.bar(x_location + offset, fractions, bar_width, label=band, color=plot_colors[multiplier])
        ax.bar_label(rects, padding=3, fmt="%.2f", fontsize=6)
        multiplier += 1

    ax.set_xticks(x_location + bar_width * (multiplier - 1) / 2)
    ax.set_xticklabels(x_labels[:up_to_layer])
    ax.legend()
    ax.grid(True)
    ax.set_ylabel(r"Occurrence (\%)")
    # ax.set_title("Cloud Layer Distribution by Radar Band")
    plt.savefig(os.path.join(data.figure_folder, "cloud_layer_distribution.png"), dpi=300, bbox_inches="tight")

    return data

