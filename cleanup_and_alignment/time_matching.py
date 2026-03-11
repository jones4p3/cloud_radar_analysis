import numpy as np
import matplotlib.pyplot as plt
import os
import xarray as xr
from .calculate_uptime import calculate_uptime
from .utils import *


def time_match_radars(data, params):
    uptime_results = {}

    # Define time range for given dataset settings 
    time_range = (np.datetime64(data.time_range.start), np.datetime64(data.time_range.end))
    print(
        f"Using full campaign time range from {time_range[0]} to {time_range[1]}"
    )

    # Extracting parameters for uptime calculation
    sampling_interval_in_minutes = params.uptime_alignment.sampling_interval_in_minutes
    max_sampling_time_in_seconds = params.uptime_alignment.max_sampling_time_in_seconds
    threshold_for_interval = params.uptime_alignment.threshold_for_uptime


    # Calculate the uptime for each radar in each interval
    for idx, (radar_slug, radar_ds) in enumerate(data.radar_datasets.items()):
        print(f"💻 Calculating uptime for {radar_slug}")
        # Extract dataset for each radar
        ds = radar_ds.sel(time=slice(*time_range))
        ds_start = ds.time.min().values
        ds_end = ds.time.max().values

        # Print time range information
        print(f"Dataset scliced into time range from {ds_start} to {ds_end}")

        # Adding time range, sampling interval, max sampling time and threshold information to the dataset attributes for later reference
        ds = add_uptime_attributes_to_dataset(data, params, ds)


        # Callculate uptime per sampling_interval
        dataset_uptime_df = calculate_uptime(
            ds,
            max_sampling_time_in_seconds=max_sampling_time_in_seconds,
            sampling_interval_in_minutes=sampling_interval_in_minutes,
            threshold_for_interval=threshold_for_interval,
        )

        # Add radar name column to dataframe to keep track of radars afterwards
        dataset_uptime_df["radar_name"] = radar_slug

        # Store results
        uptime_results[radar_slug] = dataset_uptime_df
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
    ax.set_xlim(time_range[0], time_range[1])
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

    return uptime_results

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

def remove_downtime_intervals_from_ds(data, params, highest_minimum_height, lowest_maximum_height, unique_range_gate_sizes, uptime_results):
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

        # Get params
        sampling_interval_in_minutes = params.uptime_alignment.sampling_interval_in_minutes
        max_sampling_time_in_seconds = params.uptime_alignment.max_sampling_time_in_seconds
        threshold_for_interval = params.uptime_alignment.threshold_for_uptime

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