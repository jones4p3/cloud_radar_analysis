# ------------------------------------------------------
# Clean up and alignment of the datasets
# ------------------------------------------------------
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import os
from .calculate_uptime import calculate_uptime

# Set the arrays for storing results
uptime_results = {}
combined_downtime = []
combined_uptime = []
combined_assumed_starting_seconds = 0
combined_longer_than_30_seconds_counts = 0


def cleanup_and_align_datasets(data, params):

    # Define time range & calculating total minutes in range
    campaign_start_time = np.datetime64(data.time_range.start)
    campaign_end_time = np.datetime64(data.time_range.end)
    time_range_total_minutes = (
        (np.datetime64(campaign_end_time))
        - (np.datetime64(campaign_start_time))
        + np.timedelta64(1, "s")
    ) / np.timedelta64(1, "m")
    print(
        f"Using full campaign time range from {campaign_start_time} to {campaign_end_time}"
    )

    # Extracting parameters for uptime calculation
    sampling_interval_in_minutes = params.uptime_alignment.sampling_interval_in_minutes
    max_sampling_time_in_seconds = params.uptime_alignment.max_sampling_time_in_seconds
    threshold_for_interval = params.uptime_alignment.threshold_for_uptime

    # Define time range tuple for easy slicing
    time_range = (campaign_start_time, campaign_end_time)

    # Calculate the uptime for each radar in each interval
    for idx, (radar_name, radar_data) in enumerate(data.radar_datasets.items()):
        print(f"---------------- Calculating uptime for {radar_name} ----------------")
        # Extract dataset for each radar
        ds = radar_data.sel(time=slice(*time_range))
        ds_start = ds.time.min().values
        ds_end = ds.time.max().values
        ds_total_minutes = (
            (np.datetime64(ds_end) - np.datetime64(ds_start)) + np.timedelta64(1, "s")
        ) / np.timedelta64(1, "m")

        # Adding time range, sampling interval, max sampling time and threshold information
        ds.attrs["campaign_start_time"] = str(campaign_start_time)
        ds.attrs["campaign_end_time"] = str(campaign_end_time)
        ds.attrs["sampling_interval_in_minutes"] = sampling_interval_in_minutes
        ds.attrs["max_sampling_time_in_seconds"] = max_sampling_time_in_seconds
        ds.attrs["threshold_for_interval"] = threshold_for_interval

        # Print time range information
        print(f"Given time range: from {time_range[0]} to {time_range[1]}")
        print(f"Dataset scliced into time range from {ds_start} to {ds_end}")

        # Callculate uptime per sampling_interval
        dataset_uptime_df = calculate_uptime(
            ds,
            max_sampling_time_in_seconds=max_sampling_time_in_seconds,
            sampling_interval_in_minutes=sampling_interval_in_minutes,
            threshold_for_interval=threshold_for_interval,
        )

        # Add radar name column to dataframe to keep track of radars afterwards
        dataset_uptime_df["radar_name"] = radar_name

        # Store results
        uptime_results[radar_name] = dataset_uptime_df
    print("Uptime calculation completed for all radars.")

    # Accumulate downtime
    # Accumalte the downtime and uptime across all radars
    total_downtime = []
    total_uptime = []

    for radar_name, dataset_uptime_df in uptime_results.items():
        # Get the downtime
        downtime_mask = dataset_uptime_df["ignore_time"] == True
        downtime = dataset_uptime_df[downtime_mask]
        total_downtime.append(downtime)

        # Get the uptime
        uptime = dataset_uptime_df[~downtime_mask]
        total_uptime.append(uptime)

    total_downtime_df = pd.concat(total_downtime, ignore_index=True)
    total_uptime_df = pd.concat(total_uptime, ignore_index=True)

    unique_total_downtime_df = (
        total_downtime_df.drop_duplicates(subset=["interval_start_time"])
        .reset_index(drop=True)
        .sort_values(by="interval_start_time")
    )  # Remove duplicate intervals across radars, keeps first occurrence
    unique_total_uptime_df = (
        total_uptime_df.drop_duplicates(subset=["interval_start_time"])
        .reset_index(drop=True)
        .sort_values(by="interval_start_time")
    )  # Remove duplicate intervals across radars, keeps first occurrence
    # "Substracting" downtime intervals from uptime intervals to get cleaned uptime intervals
    cleaned_uptime_df = unique_total_uptime_df[
        ~unique_total_uptime_df["interval_start_time"].isin(
            unique_total_downtime_df["interval_start_time"]
        )
    ]
    cleaned_uptime_start_cut_off_minutes = (
        cleaned_uptime_df["start_cut_off_count"].sum() / 2
    )  # Each count is 30 seconds, so divide by 2 to get minutes
    cleaned_uptime_end_added_minutes = (
        cleaned_uptime_df["end_added_seconds"].sum().astype(float) / 60
    )  # Each row is in seconds, so divide by 60 to get minutes
    cleaned_uptime_total_minutes = len(cleaned_uptime_df) * sampling_interval_in_minutes
    print(
        f"Total downtime size: {len(total_downtime_df)}, Total uptime size: {len(total_uptime_df)}, Total combined: {len(total_downtime_df) + len(total_uptime_df)}"
    )
    print(
        f"Unique downtime size: {len(unique_total_downtime_df)}, Unique uptime size: {len(unique_total_uptime_df)}, Unique combined: {len(unique_total_downtime_df) + len(unique_total_uptime_df)}"
    )
    print(f"Cleaned uptime size: {len(cleaned_uptime_df)}")
    print(
        f"Cleaned uptime intervals cover from {cleaned_uptime_df['interval_start_time'].min()} to {cleaned_uptime_df['interval_end_time'].max()}"
    )
    print(
        f"Total uptime: {len(cleaned_uptime_df) * sampling_interval_in_minutes} minutes -- {(len(cleaned_uptime_df) / 4032)*100:.2f}% of total campaign time"
    )
    print(
        f"Cleaned uptime starting cut-offs: {cleaned_uptime_start_cut_off_minutes} minutes -- {(cleaned_uptime_start_cut_off_minutes / cleaned_uptime_total_minutes)*100:.2f}% of cleaned uptime"
    )
    print(
        f"Cleaned uptime ending added time: {cleaned_uptime_end_added_minutes} minutes -- {(cleaned_uptime_end_added_minutes / cleaned_uptime_total_minutes)*100:.2f}% of cleaned uptime"
    )

    # Create a combined dataframe of unique downtime and uptime
    unique_total_df = pd.concat(
        [unique_total_downtime_df, unique_total_uptime_df], ignore_index=True
    )
    unique_total_df["ignore_time"] = unique_total_df["ignore_time"].astype(
        bool
    )  # Making double sure the column is boolean
    unique_total_df = unique_total_df.sort_values(
        ["interval_start_time", "ignore_time"], ascending=[True, False]
    )  # Sorting by time and putting ignore_time=True first
    # Now drop_duplicates to keep only the first occurrence (which is ignore_time=True if there is a duplicate)
    unique_total_df = (
        unique_total_df.drop_duplicates(subset=["interval_start_time"], keep="first")
        .reset_index(drop=True)
        .sort_values(by="interval_start_time")
    )

    uptime_results["Total"] = (
        unique_total_df  # Store combined results under "Total" key
    )

    import matplotlib.dates as mdates
    from matplotlib.patches import Patch

    n_rows = len(uptime_results)
    fixed, ax = plt.subplots(figsize=(10, 0.8 * n_rows + 2), constrained_layout=True)
    # dataset = list(uptime_results.keys())
    dataset = [name for name in data.radar_datasets.keys()] + ["Total"]
    label_names = []

    for row_idx, radar_name in enumerate(dataset):
        df = uptime_results[radar_name]
        band = (
            data.radar_datasets[radar_name].attrs["band"]
            if radar_name in data.radar_datasets
            else "Common Periods"
        )
        label_names.append(f"{band.title()}")

        # Ensure datetime dtype
        df["interval_start_time"] = pd.to_datetime(df["interval_start_time"])
        df["interval_end_time"] = pd.to_datetime(df["interval_end_time"])

        # Set the colors
        color_uptime = "green"  # Green for uptime
        color_downtime = "red"  # Red for downtime

        # Compute widths int matplotlib date format
        left = mdates.date2num(df["interval_start_time"])
        right = mdates.date2num(df["interval_end_time"])
        widths = right - left

        # Uptime (ignore_time == False)
        mask_uptime = ~df["ignore_time"].astype(bool).to_numpy()
        ax.barh(
            y=row_idx,
            width=widths[mask_uptime],
            left=left[mask_uptime],
            height=0.8,
            color=color_uptime,
        )

        # Downtime (ignore_time == True)
        mask_downtime = df["ignore_time"].astype(bool).to_numpy()
        ax.barh(
            y=row_idx,
            width=widths[mask_downtime],
            left=left[mask_downtime],
            height=0.8,
            color=color_downtime,
        )

    # Y-axis formatting
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(label_names)
    ax.invert_yaxis()  # Invert y-axis to have the first radar on top

    # x-axis formatting
    ax.set_xlabel("Date")
    ax.set_xlim(campaign_start_time, campaign_end_time)
    # ax.set_title("Uptime and Downtime Periods for Each Radar And Common Periods")

    # Date formatting
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=24))

    # Single legend
    handles = [
        Patch(facecolor=color_uptime, label="Uptime"),
        Patch(facecolor=color_downtime, label="Downtime"),
    ]
    ax.legend(handles=handles, ncols=2, loc="lower right", bbox_to_anchor=(1, -0.1))

    plt.savefig(
        os.path.join(
            data.figure_folder,
            f"uptime_downtime_{sampling_interval_in_minutes}min_{max_sampling_time_in_seconds}s_threshold_{int(threshold_for_interval*100)}.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    # -------------------------------------------------------
    # HEIGHT RESOLUTION
    # -------------------------------------------------------
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
        print(f"Original height size: {height_size} gates")
        print(f"Sliced height size: {ds_sliced['height'].size} gates")
        print(f"    New min height: {new_min_height} m")
        print(f"    New max height: {new_max_height} m")
        data.radar_datasets[radar] = ds_sliced

    # -------------------------------------------------------
    # RANGE GATE RESOLUTION
    # -------------------------------------------------------
    fig, ax = plt.subplots(1, 4, figsize=(5 * 3, 6), layout="constrained", sharey=True)

    radar_range_gate_sizes = {}
    rounding_tolerance = 1

    for idx, (radar, ds) in enumerate(data.radar_datasets.items()):
        # Grab ds information
        radar_name = ds.attrs["name"]
        height = ds["height"]
        height = height.compute().to_numpy().flatten()

        # Calculate the edges from 1 to n-1
        edges = np.empty(height.size + 1)
        edges[1:-1] = 0.5 * (height[:-1] + height[1:])

        # Adding outer edges
        edges[0] = height[0] - 0.5 * (height[1] - height[0])
        edges[-1] = height[-1] + 0.5 * (
            height[-1] - height[-2]
        )  # Here n is the last index, and n-1 is the second last index

        # Calculate the differences between edges to get range gate sizes
        range_gate_sizes = np.diff(edges)
        rounded_range_gate_sizes = np.round(
            range_gate_sizes, decimals=rounding_tolerance
        )

        # Get unique range gate sizes, their first occurrence index and counts_per_unique_range_gate_size
        (
            unique_range_gate_sizes,
            first_occurrence_index,
            counts_per_unique_range_gate_size,
        ) = np.unique(
            rounded_range_gate_sizes, return_index=True, return_counts=True
        )  # Get unique range gate sizes, their first occurrence first_occurrence_index and counts_per_unique_range_gate_size

        # Filter by the amount of counts
        correct_counts = np.where(counts_per_unique_range_gate_size > 1)
        assigned_range_sizes, assigned_range_sizes_index = (
            unique_range_gate_sizes[correct_counts],
            first_occurrence_index[correct_counts],
        )

        print(f"------------ Radar: {radar_name} ------------")
        print(
            f"Range gate sizes [{len(unique_range_gate_sizes)}]:\t{unique_range_gate_sizes}"
        )
        print(f"Counts: \t\t{counts_per_unique_range_gate_size:}")
        print(f"Index: \t\t\t{first_occurrence_index}\n")

        print(
            f"Correct Range gate sizes [{len(assigned_range_sizes)}]: {assigned_range_sizes}"
        )
        gate_height = ds["height"].isel(height=assigned_range_sizes_index).values
        print(f"Gate heights for correct range gate sizes: {gate_height}")
        print(f"Correct Index: {assigned_range_sizes_index}")

        # Creating an array for the range sizes with height for assigned range gate sizes
        assigned_range_sizes_with_height = []

        # Accumalte the new array with unique range sizes [4 chirp settings assumed]
        for height_idx in range(height.size):
            # First chirp setting
            if (
                assigned_range_sizes_index[0]
                <= height_idx
                < assigned_range_sizes_index[1]
            ):
                assigned_range_sizes_with_height.append(assigned_range_sizes[0])
            # Second chirp setting
            elif (
                assigned_range_sizes_index[1]
                <= height_idx
                < assigned_range_sizes_index[2]
            ):
                assigned_range_sizes_with_height.append(assigned_range_sizes[1])
            # Third chirp setting
            elif (
                assigned_range_sizes_index[2]
                <= height_idx
                < assigned_range_sizes_index[3]
            ):
                assigned_range_sizes_with_height.append(assigned_range_sizes[2])
            # Fourth chirp setting
            else:
                assigned_range_sizes_with_height.append(assigned_range_sizes[3])
        assigned_range_sizes_with_height = np.array(assigned_range_sizes_with_height)

        # Check for consistency
        print(
            f"Check for consistency: {height.size} vs {assigned_range_sizes_with_height.size}"
        )
        if height.size != assigned_range_sizes_with_height.size:
            print("❌ Mismatch in height gates and range size gates!")
            continue
        # Adding the range gate sizes to the dictionary
        ds["range_gate_sizes"] = (("height"), range_gate_sizes)
        ds["range_gate_sizes"].attrs.update(
            units="m",
            long_name="Range gate size",
            description="Vertical range gate size as a function of height.",
        )

        # Adding the assigned range sizes with height to the dataset
        ds["rounded_range_gate_sizes"] = (("height"), assigned_range_sizes_with_height)
        ds["rounded_range_gate_sizes"].attrs.update(
            units="m",
            long_name="Range gate size",
            description=f"Vertical range gate size as a function of height. Sizes are: {unique_range_gate_sizes} meters.",
        )
        data.radar_datasets[radar] = ds

        # Create plots
        ax[idx].plot(range_gate_sizes, height, ls="-", marker="o")
        ax[idx].plot(
            assigned_range_sizes_with_height,
            height,
            ls="--",
            color="red",
            label="Assigned range gate size",
        )
        colors = plt.cm.tab10.colors
        for color_id, (range_size, range_index) in enumerate(
            zip(assigned_range_sizes, assigned_range_sizes_index)
        ):
            if range_index > 0:
                range_index = range_index
            range_switch_height = height[range_index]
            ax[idx].axhline(
                y=range_switch_height,
                xmin=0,
                xmax=1,
                ls="--",
                color=colors[color_id],
                label=f"Range gate size switch [at {range_index}] to {range_size:.2f} m",
            )
        # ax[idx].axhline(y=height[0], xmin=0, xmax=1, ls="--", color="black", label="Lowest height")
        ax[idx].legend()
        ax[idx].set_title(radar_name)
        ax[idx].set_xlabel("Height resolution for a range gate")
        ax[idx].set_ylabel("Height")

    plt.savefig(
        os.path.join(data.figure_folder, f"radar_range_gate_sizes_all_radars.png"),
        dpi=450,
    )

    # -------------------------------------------------------
    # Cleaning
    # -------------------------------------------------------

    def split_ds_by_intervals(
        ds: xr.Dataset,
        intervals: pd.DataFrame,
        time_dim: str = "time",
        start_col: str = "interval_start_time",
        end_col: str = "interval_end_time",
        flag_col: str = "ignore_time",
    ) -> tuple[xr.Dataset, xr.Dataset]:
        """
        Split an xarray Dataset into (kept_ds, ignored_ds) based on intervals.
        intervals is the source of truth and must contain start/end + ignore flag.
        """

        if time_dim not in ds.dims and time_dim not in ds.coords:
            raise ValueError(f"Dataset has no '{time_dim}' dimension/coord.")

        # Ensure datetime dtype in the dataframe
        df = intervals.copy()
        df[start_col] = pd.to_datetime(df[start_col])
        df[end_col] = pd.to_datetime(df[end_col])
        times = ds[time_dim].values
        if not np.issubdtype(times.dtype, np.datetime64):
            raise TypeError(f"ds['{time_dim}'] must be datetime64, got {times.dtype}")

        # Build masks by OR-ing all interval conditions
        keep_mask = np.zeros(times.shape, dtype=bool)
        ign_mask = np.zeros(times.shape, dtype=bool)

        # Define interval inclusion
        for row in df.itertuples(index=False):
            start = np.datetime64(getattr(row, start_col), "s")
            end = np.datetime64(getattr(row, end_col), "s")
            ignore = bool(getattr(row, flag_col))
            in_interval = (times >= start) & (
                times < end
            )  # Left-inclusive, right-exclusive [start, end)]

            # Build masks
            if ignore:
                ign_mask |= in_interval
            else:
                keep_mask |= in_interval

        # If something is in both (overlaps), let "ignore" win (usually safest for QC)
        keep_mask &= ~ign_mask

        kept_ds = ds.isel({time_dim: keep_mask})
        ignored_ds = ds.isel({time_dim: ign_mask})

        return kept_ds, ignored_ds

    for radar_slug, ds in data.radar_datasets.items():
        print(f"Cleaning dataset for {radar_slug}...")
        radar_title = ds.attrs.get("radar_name", radar_slug)

        # Dropping time intervals with downtime
        ds_clean, ds_ignored = split_ds_by_intervals(
            ds,
            uptime_results["Total"],
            time_dim="time",
            start_col="interval_start_time",
            end_col="interval_end_time",
            flag_col="ignore_time",
        )

        print(
            f"Original dataset length: {ds.sizes['time']} -- {ds_clean.sizes['time']} after cleaning -- {ds_ignored.sizes['time']} removed"
        )
        print(f"Cleaned dataset length:  {ds_clean.sizes['time']}")
        n_removed_timesteps = ds.sizes["time"] - ds_clean.sizes["time"]
        print(
            f"Removed {n_removed_timesteps} timestamps. [{(n_removed_timesteps/ds.sizes['time'])*100:.2f}%]"
        )

        ds_clean.attrs.update(
            description=f"Dataset cleaned by removing timestamps during downtime periods as calculated with a {sampling_interval_in_minutes}minute window, max sampling time of {max_sampling_time_in_seconds}s, and threshold of {threshold_for_interval*100:.0f}% per {sampling_interval_in_minutes} minutes. This dataset only contains data from the highest minimum height ({highest_minimum_height["height"]:.2f} m) up to the lowest maximum height across all radars ({lowest_maximum_height["height"]:.2f} m) and includes range gate size information as well as sensitivity curve information.",
            max_sampling_time_seconds=max_sampling_time_in_seconds,
            uptime_threshold=threshold_for_interval,
            sampling_interval_minutes=sampling_interval_in_minutes,
            sensitivity_min_value=float(ds_clean["sensitivity"].min().values),
            sensitivity_max_value=float(ds_clean["sensitivity"].max().values),
        )

        # Renamging dimensions, height and reflectivity to standard names
        ds_clean["ze"].attrs.update(
            units="dBZ",
            long_name="Radar Reflectivity",
            description="Radar reflectivity factor representing the power returned to the radar from targets in the atmosphere.",
            min_value=float(ds_clean["ze"].min().values),
            max_value=float(ds_clean["ze"].max().values),
        )

        ds_clean["height"].attrs.update(
            units="m",
            long_name="Height",
            description="Height above ground level corresponding to each range gate center.",
            min_value=float(ds_clean["height"].min().values),
            max_value=float(ds_clean["height"].max().values),
        )

        ds_clean["time"].attrs.update(
            long_name="Time",
            description="Timestamps corresponding to each radar measurement.",
        )

        print(
            f"--------------- OVER ALL DATASET INFORMATION FOR {radar_slug} ---------------"
        )
        print(
            f"Time range: from {ds_clean.time.min().values} to {ds_clean.time.max().values} \t || Total time steps: {ds_clean.sizes['time']}"
        )
        print(
            f"Height range: from {ds_clean.height.min().values} to {ds_clean.height.max().values} \t\t\t\t\t || Total height gates: {ds_clean.sizes['height']}"
        )
        print(
            f"Range gate sizes included: {unique_range_gate_sizes} meters \t\t\t\t || Total unique sizes: {len(unique_range_gate_sizes)}"
        )
        print(
            f"Sensitivity curve included  \t\t\t\t\t\t\t\t || Min to max: {ds_clean.sensitivity.min().values:.2f} to {ds_clean.sensitivity.max().values:.2f} dBZ"
        )
        print("---------------------------------------------------------------")

        data.radar_datasets[radar_slug] = ds_clean
        print(f"✅ Time-matched data for {radar_slug} written successfully")
    return data