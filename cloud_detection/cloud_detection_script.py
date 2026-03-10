import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from .get_min_max import get_reflectivity_min_max, get_height_min_max_with_valid_ze
from .single_time_functions import get_single_time_from_input, get_single_time_reflectivity_min_max, plot_single_time_stamp
from .edge_detection import find_cloud_edges, check_cloud_boundaries
from .layer_detection import analyze_possible_cloud_layers, get_max_layers_in_time_range


def run_cloud_detection_algorithm(radar_datasets):
    # General Setting
    use_threshold = False # If threshold is False, the sensitivity of the radar is used instead
    sensitivity_add_in_dbz = 3  # Only used if use_threshold is False (Cloud detection sensitivity = sensitivity + sensitivity_add_in_dbz)
    show_plots = False
    test_single_radar = False
    example_radar = ["grawac167", "grawac174"]
    single_time_input = "2025-02-25T20:13:13" #"2025-02-27T10:51:20" #"2025-02-26T02:09:10.000000000" # (bool or datetime64) If bool, random time is selected
    create_new_ds = False
    debug = False
    detailed_debug = False
    use_test_time_range = False
    test_time_range = ("2025-02-25T00:00:00", "2025-02-28T00:00:00") # Only used if use_test_time_range is True, else the whole time range of the dataset is used


    # Set cloud properties
    ze_threshold_in_dbz = -30
    min_cloud_thickness_in_m = [31, 35, 70, 130] # 2,2,3,4 range gate sizes of lowest resolution
    min_cloud_spacing_in_m = [64, 71, 117, 195] # 4,4,5,6 range gate sizes of lowest resolution
    max_cloud_layer = 20
    force_height_settings = ((False, 0), (True, 8000)) # (True, Int/Float) / (True, Int/Float) for bottom / top height forcing

    # Plotting
    plot_ze = True # Plotting reflectivity over time
    plot_single_time = True # Plotting single time reflectivity profile
    plot_sensitivity = True # Plotting sensitivity profile in single time plot
    show_all_ze_values = True # If True, all ze values are shown in single time plot, else only those above threshold
    show_possible_cloud_layers = False # Show possible cloud layers as horizontal lines
    mark_one_range_gate_clouds = True
    show_distinct_ze_value_points = True # 
    show_cloud_edges = True # Show detected cloud edges in plots
    marker_size = 1.5
    single_time_line_width = 1.5
    big_figure_for_multiple_radars = not test_single_radar

    # Setting the radar data to analyze based on single or multiple radar test
    if test_single_radar:
        cloud_radars = {}
        for radar in example_radar:
            cloud_radars[radar] = radar_datasets[radar]
    else:
        cloud_radars = radar_datasets
        print("Using the whole set of cloud radars for analysis.")
        radars_to_analyze = [radar_added for radar_added in cloud_radars.keys() if radar_added != "_meta"]
        print(f"Radars to analyze: {radars_to_analyze}\n")

    # Pack settings together
    general_settings = {
        "data": cloud_radars,
        "debug": debug,
        "use_threshold": use_threshold,
        "sensitivity_add_in_dbz": sensitivity_add_in_dbz,
        "use_test_time_range": use_test_time_range,
        "test_single_radar": test_single_radar,
        "example_radar": example_radar,
    }

    time_settings = {
        "test_time_range": test_time_range,
        "single_time_input": single_time_input
    }

    plot_settings = {
        "show_plots": show_plots,
        "show_possible_cloud_layers": show_possible_cloud_layers,
        "mark_one_range_gate_clouds": mark_one_range_gate_clouds,
        "show_distinct_ze_value_points": show_distinct_ze_value_points,
        "show_cloud_edges": show_cloud_edges,
        "show_all_ze_values": show_all_ze_values,
        "plot_ze": plot_ze,
        "plot_single_time": plot_single_time,
        "plot_sensitivity": plot_sensitivity,
        "big_figure_for_multiple_radars": big_figure_for_multiple_radars,
        "marker_size": marker_size,
        "height_min": None,
        "height_max": None
    }

    cloud_detection_settings = {
        "ze_threshold_in_dbz": ze_threshold_in_dbz,
        "sensitivity_add_in_dbz": sensitivity_add_in_dbz,
        "min_cloud_thickness_in_m": min_cloud_thickness_in_m,
        "min_cloud_spacing_in_m": min_cloud_spacing_in_m,
        "max_cloud_layer": max_cloud_layer
    }

    # Setting up figure based on plotting settings
    n_rows = len(cloud_radars)
    n_cols = int(plot_ze) + int(plot_single_time)
    if show_plots and big_figure_for_multiple_radars:
        if n_cols > 1:
            big_fig, big_fig_rows = plt.subplots(n_rows, n_cols, figsize=(10,4*n_rows), constrained_layout=True, gridspec_kw={"width_ratios": [1.3,1]}, sharey=True)
        else:
            big_fig, big_fig_rows = plt.subplots(n_rows, n_cols, figsize=(5,5*n_rows), constrained_layout=True, sharey=True)
        # big_fig.suptitle(f"Cloud Layer Detection for Different Radars")
    elif show_plots:
        if n_cols > 1:
            big_fig, big_fig_rows = plt.subplots(n_rows, n_cols, figsize=(14,6), constrained_layout=True, sharey=True, gridspec_kw={"width_ratios": [1.5,1]})
        else:
            big_fig, big_fig_rows = plt.subplots(n_rows, n_cols, figsize=(6,6), constrained_layout=True, sharey=True)

    # Reflectivity min and max for scaling in plots. Searched across all radars
    if show_plots:
        ze_min, ze_max = get_reflectivity_min_max(general_settings, time_settings, cloud_detection_settings, debug)
        height_min, height_max = get_height_min_max_with_valid_ze(general_settings, time_settings, debug)
        height_min -= 50  # Adding some space at bottom for better visualization
        height_max += 50  # Adding some space on top for better visualization

        # Applying forced height if set
        is_force_min_set, force_min = force_height_settings[0][0], force_height_settings[0][1]
        is_force_max_set, force_max = force_height_settings[1][0], force_height_settings[1][1]
        if is_force_min_set and is_force_max_set:
            height_min, height_max = force_min, force_max
            if debug: print(f"Forced height min to: {height_min} m")
            if debug: print(f"Forced height max to: {height_max} m")
        elif not is_force_min_set and is_force_max_set:
            height_max = force_max
            if debug: print(f"Forced height max to: {height_max} m")
        elif is_force_min_set and not is_force_max_set:
            height_min = force_min
            if debug: print(f"Forced height min to: {height_min} m")
        if debug and (is_force_min_set or is_force_max_set): 
            print(f"Height min for plotting: {height_min} m")
            print(f"Height max for plotting: {height_max} m\n")
        plot_settings["height_min"] = height_min
        plot_settings["height_max"] = height_max

    # ---------------------------------
    # CLOUD LAYER DETECTION
    # ---------------------------------
    single_times_for_radars = []
    single_time = None
    print("--- Starting Cloud Layer Detection ---")
    for fig_idx, (radar_slug, ds) in enumerate(cloud_radars.items()):
        radar_band = ds.attrs["band"]
        print(f"💻 Starting cloud layer detection for: {radar_band}")
        # Unpacking settings
        debug = general_settings["debug"]
        use_threshold = general_settings["use_threshold"]
        show_plots = plot_settings["show_plots"]
        show_cloud_edges = plot_settings["show_cloud_edges"]
        use_big_figure_for_multiple_radars = plot_settings["big_figure_for_multiple_radars"]
        use_plot_ze = plot_settings["plot_ze"]
        plot_single_time = plot_settings["plot_single_time"]
        single_time_input = time_settings["single_time_input"]

        # Selecting dataset based on time range settings
        if general_settings["use_test_time_range"]:
            test_time_range = time_settings["test_time_range"]
            ds = ds.sel(time=slice(*test_time_range))
            print(f"- Selected dataset test time range: {test_time_range}\n")
        else:
            print(f"- Using full dataset time range for radar: {radar_band}")
            print(f"Time range: {ds['time'].values[0]} to {ds['time'].values[-1]}\n")

        # Getting single time for plotting later if needed
        if show_plots and plot_single_time:
            if len(single_times_for_radars) == 0:
                single_time = get_single_time_from_input(single_time_input, ds, debug)
                print(f"-------------------------------- Selected single time for plotting: {single_time}\n")
                single_times_for_radars.append(single_time)
            else:
                single_time_input = single_times_for_radars[-1]
                single_time = get_single_time_from_input(single_time_input, ds, debug)
                print(f"-------------------------------- Selected single time for plotting: {single_time}\n")
                single_times_for_radars.append(single_time)

        # Applying the threshold if needed and selecting variables from dataset
        if use_threshold:
            threshold_mask = ds["ze"] >= ze_threshold_in_dbz
            ze = ds["ze"].where(threshold_mask) # Shape (time, height)
            print(f"- Applying fixed threshold of {ze_threshold_in_dbz} dBZ for radar: {radar_band}\n")
        else:
            print(f"- Applying sensitivity-based threshold for radar: {radar_band} at sensitivity + {sensitivity_add_in_dbz} dBZ")
            sensitivity_mask = (ds["sensitivity"] + sensitivity_add_in_dbz)
            if debug: 
                # print(f"  Sensitivity mask stats - min: {sensitivity_mask.min():.2f} dBZ, max: {sensitivity_mask.max():.2f} dBZ")
                print(f"  Head: {sensitivity_mask.values.flatten()[:5]}")
                print(f"  Tail: {sensitivity_mask.values.flatten()[-5:]}\n")
            threshold_mask = ds["ze"] >= (sensitivity_mask)
            ze = ds["ze"].where(threshold_mask) # Shape (time, height)
        ze_np = ze.values  # Numpy array of ze for faster processing
        height = ds["height"].values    # Shape (height,)
        ds_time_range = ds["time"].values       # Shape (time,)
        range_gate_sizes = ds["range_gate_sizes"].values  # Shape (height,)
        unique_range_gate_sizes = np.unique(ds["rounded_range_gate_sizes"].values)

        # Setting up plotting variables based on plot settings
        if show_plots:
            # General settings for plotting
            current_row = big_fig_rows[fig_idx] if n_rows > 1 else big_fig_rows
            single_ze_min, single_ze_max = get_single_time_reflectivity_min_max(general_settings, single_time, cloud_detection_settings, debug)
            single_ze_min -= 2  # Adding some space on left for better visualization
            single_ze_max += 2  # Adding some space on right for better visualization
            time_str = np.datetime_as_string(single_time, unit='s').split("T")[1]

            # Settings for both plots
            if plot_ze and plot_single_time:
                # Reflectivity
                ze_ax = current_row[0]

                # Single time
                time_ax = current_row[1]
                single_ze = ze.sel(time=single_time, method="nearest")
                if np.all(np.isnan(single_ze.values)):
                    print(f"❌ Warning: No valid Ze values found at single time {single_time} for radar {radar_band}. Skipping single time plot.")
            elif plot_ze:
                ze_ax = current_row
                ze_ax.grid(which='major')
            elif plot_single_time:
                time_ax = current_row
                time_ax.grid(which='both')
                single_ze = ze.sel(time=single_time, method="nearest")
                if np.all(np.isnan(single_ze.values)):
                    print(f"❌ Warning: No valid Ze values found at single time {single_time} for radar {radar_band}. Skipping single time plot.")
                single_ze_min = single_ze.min()
                single_ze_max = single_ze.max()
                print(f"-------------------- Single time Ze min: {single_ze_min}, max: {single_ze_max}")
    
        # Setting up the all_layer_per_time_range
        all_detected_cloud_layer_per_radar = [] # Shape [(time_step, [cloud_layers_in_time_step]), ...]

        # Iterating over all time steps in the given time_range
        for i, time_step in enumerate(ds_time_range):
            # Analyze ze profile for the current time step
            if debug and detailed_debug: print(f"🔬 Analyzing time step: {time_step} - {single_time if single_time is not None else 'None'}")
            ze_profile = ze_np[i, :]  # Selecting ze_profile for the given time_step
            # ze_profile = ze.sel(time=time_step) # Selecting ze_profile for the given time_step
            if debug and detailed_debug: print(f"   Selected ze profile for time step")


            # Get back the indices where a cloud start and ends
            cloud_base_idx, cloud_top_idx = find_cloud_edges(ze_profile, detailed_debug)
            check_cloud_boundaries(cloud_base_idx, cloud_top_idx, time_step)
            possible_cloud_layers = np.array(list(zip(cloud_base_idx, cloud_top_idx)))
        
            cloud_layers_in_time_step, number_of_cloud_layers = analyze_possible_cloud_layers(
                height, range_gate_sizes, unique_range_gate_sizes,
                possible_cloud_layers, 
                cloud_detection_settings,
                detailed_debug
            )
            if debug: print(f"   --- RESULT: Detected {number_of_cloud_layers} cloud layers.\n")

            # Marking clouds in plots
            if show_plots:

                # Mark possible cloud layers as horizontal lines
                if (time_step == single_time) and plot_single_time:
                    if show_possible_cloud_layers or mark_one_range_gate_clouds:
                        for cloud in possible_cloud_layers:
                            cloud_base_gate, cloud_top_gate = cloud[0], cloud[1]
                            cloud_base_in_m = height[cloud_base_gate].item()
                            cloud_top_in_m = height[cloud_top_gate].item()
                            cloud_thickness_in_gates = cloud_top_gate - cloud_base_gate
                            # Single time marking
                            if cloud_thickness_in_gates == 0:
                                marker_ze = single_ze[cloud_base_gate].values
                                time_ax.plot(marker_ze, cloud_base_in_m, marker="X", color="green", markersize=marker_size*2)
                            elif show_possible_cloud_layers:
                                time_ax.axhline(cloud_base_in_m, xmin=0, xmax=1, color="purple", linestyle="-.")
                                time_ax.axhline(cloud_top_in_m, xmin=0, xmax=1, color="purple", linestyle="--")

                if show_cloud_edges:
                    for cloud_data in cloud_layers_in_time_step:
                        data_in_gates = cloud_data[0]
                        data_in_height = cloud_data[1]
                        cloud_base_gate, cloud_top_gate = data_in_gates[0], data_in_gates[1]
                        cloud_base_in_m, cloud_top_in_m = data_in_height[0], data_in_height[1]

                    
                        # Ze marking
                        if plot_ze:
                            # Calculate time edges for proper marking of cloud layer in ze plot
                            t = ds_time_range.astype("datetime64[ns]")  # (N,)
                            dt = np.diff(t)

                            # Build time edges (N+1)
                            t_edges = np.empty(t.size + 1, dtype="datetime64[ns]")
                            t_edges[1:-1] = t[:-1] + dt // 2
                            t_edges[0]    = t[0]  - dt[0] // 2
                            t_edges[-1]   = t[-1] + dt[-1] // 2
                            xmin = t_edges[i]
                            xmax = t_edges[i+1]
                            # ze_ax.hlines(y=cloud_base_in_m, xmin=xmin, xmax=xmax, colors="magenta", linestyles="dashed")
                            # ze_ax.hlines( y=cloud_top_in_m, xmin=xmin, xmax=xmax, colors="magenta", linestyles="dashed")
                            ze_ax.plot(ds_time_range[i], cloud_base_in_m, marker="^", color="black", markersize=marker_size*1.5)
                            ze_ax.plot(ds_time_range[i], cloud_top_in_m, marker="v", color="red", markersize=marker_size*1.5)

                        # Single time marking
                        if (time_step == single_time) and plot_single_time:
                            cloud_base_ze = single_ze[cloud_base_gate].values
                            cloud_top_ze = single_ze[cloud_top_gate].values
                            time_ax.plot(cloud_base_ze, cloud_base_in_m, marker="^", color="black", markersize=marker_size*2.5)
                            time_ax.plot(cloud_top_ze, cloud_top_in_m, marker="v", color="red", markersize=marker_size*2.5)
    
            # Append the cloud layers detected in this time step to the overall list for the radar
            all_detected_cloud_layer_per_radar.append((time_step, cloud_layers_in_time_step))

        print(f"------ ✅ Finished cloud layer detection for: {radar_band}\n")
        
        # Creating new dataset with cloud layer information
        print(f"💾 Creating new dataset with cloud layer information for radar: {radar_band}")
        # Process all_layer_per_time_range for adding to dataset
        max_layer_time_step, max_n_layers = get_max_layers_in_time_range(all_detected_cloud_layer_per_radar, debug)

        # Pre-allocating numpy arrays with shape (time, max_layers)
        base_in_gates = np.full((ds_time_range.size, max_n_layers), np.nan)
        top_in_gates = np.full((ds_time_range.size, max_n_layers), np.nan)
        thickness_in_gates = np.full((ds_time_range.size, max_n_layers), np.nan)

        base_in_m = np.full((ds_time_range.size, max_n_layers), np.nan)
        top_in_m = np.full((ds_time_range.size, max_n_layers), np.nan)
        thickness_in_m = np.full((ds_time_range.size, max_n_layers), np.nan)

        n_layers = np.zeros((ds_time_range.size,), dtype=int)

        # Filling the numpy arrays
        for time_index, (_, cloud_layers_data) in enumerate(all_detected_cloud_layer_per_radar):
            n_layers[time_index] = len(cloud_layers_data)
            if debug: print(f"Time index {time_index} has {n_layers[time_index]} layers.")

            for layer_index, layer_data in enumerate(cloud_layers_data):
                if debug: print(f"Layer_index: {layer_index}, layer_data: {layer_data}")
                data_in_gates = layer_data[0]
                data_in_height = layer_data[1]
                cloud_base_gate, cloud_top_gate, cloud_thickness_in_gates = data_in_gates[0], data_in_gates[1], data_in_gates[2]
                cloud_base_in_m, cloud_top_in_m, cloud_thickness_in_m = data_in_height[0], data_in_height[1], data_in_height[2]
            
                base_in_gates[time_index, layer_index] = cloud_base_gate
                top_in_gates[time_index, layer_index] = cloud_top_gate
                thickness_in_gates[time_index, layer_index] = cloud_thickness_in_gates

                base_in_m[time_index, layer_index] = cloud_base_in_m
                top_in_m[time_index, layer_index] = cloud_top_in_m
                thickness_in_m[time_index, layer_index] = cloud_thickness_in_m
        print(f"Finished filling cloud layer data arrays for radar: {radar_band}")
    

        # Adding the cloud layer data to the dataset
        layer_coord = np.arange(1, max_n_layers+1)
        ds_out = ds.copy()

        ds_out = ds_out.assign_coords({"layer": layer_coord})

        ds_out["layer"].attrs = {
        "long_name": "Cloud layer index",
        "description": f"Per-profile cloud layer number. Lowest layer is 1, maximum number of layers is {max_n_layers+1}.",
        }

        ds_out["cloud_base_gate"] = xr.DataArray(
        base_in_gates, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
        attrs={"long_name": "Cloud base gate index", "fill_value": -1}
        )
        ds_out["cloud_top_gate"] = xr.DataArray(
            top_in_gates, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
            attrs={"long_name": "Cloud top gate index", "fill_value": -1}
        )
        ds_out["cloud_thickness_gate"] = xr.DataArray(
            thickness_in_gates, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
            attrs={"long_name": "Cloud thickness in gates", "fill_value": -1}
        )

        ds_out["cloud_base_in_m"] = xr.DataArray(
            base_in_m, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
            attrs={"long_name": "Cloud base height", "units": "m"}
        )
        ds_out["cloud_top_in_m"] = xr.DataArray(
            top_in_m, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
            attrs={"long_name": "Cloud top height", "units": "m"}
        )
        ds_out["cloud_thickness_in_m"] = xr.DataArray(
            thickness_in_m, dims=("time", "layer"), coords={"time": ds.time, "layer": ds_out.layer},
            attrs={"long_name": "Cloud thickness", "units": "m"}
        )

        ds_out["n_layers"] = xr.DataArray(
            n_layers, dims=("time",), coords={"time": ds.time},
            attrs={"long_name": "Number of detected cloud layers",
            "description": "Number of detected cloud layers per time step.",
            "max_layers": f"{max_n_layers} at time {max_layer_time_step}"}
        )


        # Saving the new dataset
        radar_datasets[radar_slug] = ds_out
        print(f"---- 💾 ✅ New dataset with cloud layer information created and stored in radar_datasets for radar: {radar_band}\n")

        # Actual plotting
        if show_plots:
            # Both plots: Reflectivity over time and single time profile
            if plot_ze and plot_single_time:
                radar_title = radar_band if big_figure_for_multiple_radars else None
                # Reflectivity over time plot
                ze.plot(ax=ze_ax, y="height", cmap="turbo", vmin=ze_min, vmax=ze_max)
                ze_ax.axvline(x=single_time, ymin=0, ymax=1, color="purple", linestyle=":", linewidth=single_time_line_width, label=f"Single Time: {time_str}")
                ze_ax.set_ylim(height_min,height_max)
                ze_ax.set_xlim(np.datetime64(time_settings["test_time_range"][0]), np.datetime64(time_settings["test_time_range"][1]))
                ze_ax.grid(which='both')
                ze_ax.set_ylabel(f"{radar_title}\nHeight (m)")
                if n_rows == 1:
                    ze_ax.set_title(f"{radar_band}")
                else:
                    ze_ax.set_title(f"Reflectivity and Cloud Detection")

                # Plotting single time ze
                time_ax = plot_single_time_stamp(time_ax, ds, single_time, plot_settings, cloud_detection_settings, radar_band)
                if n_rows == 1:
                    time_ax.set_title(f"Reflectivity at {time_str}")
                else:
                    time_ax.set_title(f"Reflectivity at {time_str}")
        
            # Only Reflectivity over time
            elif plot_ze and not plot_single_time:
                ze.plot(ax=ze_ax, y="height", cmap="turbo", vmin=ze_min, vmax=ze_max)

            # Only plot single time
            elif not plot_ze and plot_single_time:
                time_ax = plot_single_time_stamp(time_ax, ds, single_time, plot_settings, cloud_detection_settings, radar_band)
    
    return radar_datasets