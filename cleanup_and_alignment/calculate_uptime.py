import pandas as pd
import numpy as np
from .utils import *

def uptime_from_interval_times(
    interval_times,
    interval_start_time,
    interval_end_time,
    max_sampling_time=10,
    debug=False,
):
    """
    Fraction of window covered_seconds by data, assuming each sample covers backwards
    up to max_sampling_time seconds, clipped by next sample and window end.
    """
    # No samples in interval
    if len(interval_times) == 0:
        return 0.0

    # Forcing all times to np.datetime64["s"]
    interval_start_time = np.datetime64(interval_start_time, "s")
    interval_end_time = np.datetime64(interval_end_time, "s")

    # Define interval_times as np.datetime64["s"] and get interval in seconds
    interval_times = np.sort(interval_times.astype("datetime64[s]"))
    total_interval_in_seconds = interval_end_time - interval_start_time
    if total_interval_in_seconds <= 0:
        return 0.0

    # Convert max_sampling_time to np.timedelta64 in seconds
    max_sampling_time = np.timedelta64(int(max_sampling_time), "s")

    # Variable to save total covered_seconds time by radar
    covered_seconds = np.timedelta64(0, "s")

    # Debuging prints
    if debug:
        print("interval_start_time:", interval_start_time)
        print("interval_end_time:", interval_end_time)
        print("interval_times:", interval_times.size)
        print("total_interval_in_seconds:", total_interval_in_seconds)
        print("max_sampling_time (s):", max_sampling_time)
        print("covered_seconds (s):", covered_seconds)

    # Variable to keep track of seconds which have been cut off due to interval limits
    start_cut_off_count = 0
    end_assumed_added_count = 0
    end_assumed_added_seconds = 0

    # Iterate over samples in interval
    for time_idx_in_interval in range(interval_times.size):
        # Handle the first sample in the interval
        if time_idx_in_interval == 0:
            if debug:
                print(f"--- Processing interval with {interval_times.size} samples ---")

            # Check if the first time sample starts after interval_start_time
            if interval_times[time_idx_in_interval] > interval_start_time:
                if debug:
                    print(
                        f"First sample {interval_times[time_idx_in_interval]} after interval start {interval_start_time}"
                    )
                # Get the minimum from the difference betweend the first sample and interval start time and max_sampling_time
                # E.g Start: 18:00:00 First sample: 18:00:20 -> difference: 20s < max_sampling_time: 30s -> covered_seconds: 20s
                # E.g Start: 18:00:00 First sample: 18:06:00 -> difference: 360s > max_sampling_time: 30s -> covered_seconds: 30s (this assumes that the radar started sampling max_sampling_time before the first sample)
                passed_seconds_after_starting_time = (
                    interval_times[time_idx_in_interval] - interval_start_time
                )
                if passed_seconds_after_starting_time > max_sampling_time:
                    covered_seconds += max_sampling_time
                    start_cut_off_count += 1
                else:
                    covered_seconds += passed_seconds_after_starting_time
                if debug:
                    print(
                        f"  Total covered_seconds (s): {covered_seconds} from {total_interval_in_seconds} [{(covered_seconds/total_interval_in_seconds):.4f}]"
                    )

        # Last sample in the interval
        elif time_idx_in_interval == (interval_times.size - 1):
            current_sample_end_time = interval_times[time_idx_in_interval]
            seconds_until_interval_end = interval_end_time - current_sample_end_time
            if (
                seconds_until_interval_end < max_sampling_time
            ):  # If it is less than max_sampling_time, we can only add the remaining time until the interval end assuming the radar was measuring in this interval and saving in the next at 00:00:00 or 00:00:01 etc..
                covered_seconds += seconds_until_interval_end
                end_assumed_added_count += 1
                end_assumed_added_seconds += seconds_until_interval_end

        # All other samples in the interval
        else:
            # Check wether the current sample is within the interval
            previous_sample_end_time = interval_times[time_idx_in_interval - 1]
            current_sample_end_time = interval_times[time_idx_in_interval]
            difference_between_samples = (
                current_sample_end_time - previous_sample_end_time
            )
            if current_sample_end_time < interval_start_time:
                print(
                    f"⚠️ WARNING: Sample {time_idx_in_interval}: {current_sample_end_time} before interval start {interval_start_time}"
                )
                current_sample_end_time = interval_start_time
            if current_sample_end_time > interval_end_time:
                print(
                    f"⚠️ WARNING: Sample {time_idx_in_interval}: {current_sample_end_time} after interval end {interval_end_time}"
                )
                continue

            # Check for downtime longer than max_sampling_time
            if difference_between_samples > (max_sampling_time):
                if debug:
                    print(
                        f"  Downtime longer than max_sampling_time between sample {time_idx_in_interval-1} and {time_idx_in_interval}: {difference_between_samples} seconds"
                    )
                covered_seconds += max_sampling_time
                start_cut_off_count += 1
            else:
                covered_seconds += difference_between_samples

    # Uptime in interval
    uptime_in_interval = covered_seconds / total_interval_in_seconds
    if debug:
        print(
            f"--------- Uptime in interval: {uptime_in_interval:.2f} (covered_seconds {covered_seconds} seconds of {total_interval_in_seconds} seconds)"
        )
    return (
        float(uptime_in_interval),
        start_cut_off_count,
        end_assumed_added_count,
        end_assumed_added_seconds,
    )


def calculate_uptime(
    ds,
    max_sampling_time_in_seconds,
    sampling_interval_in_minutes,
    threshold_for_interval,
):

    print("Calculating uptime...")
    # Convert sampling interval to pandas frequency string
    sampling_interval_in_minutes_str = f"{sampling_interval_in_minutes}min"

    # Build the interval start times based on samppling interval
    interval_start_times = build_interval_start_times(ds, sampling_interval_in_minutes_str)

    # Sort dataset time values and create pandas datetime index and series
    dataset_time_values = pd.to_datetime(
        ds["time"].sortby("time").values
    )
    
    # Create sorted pandas datetime index
    dataset_time_series = pd.Series(dataset_time_values, index=dataset_time_values)

    # Group observed times into intervals based on sampling interval and campaign start time
    grouped_dataset_time_series = dataset_time_series.groupby(
        pd.Grouper(freq=sampling_interval_in_minutes_str, origin=interval_start_times[0])
    )  # Groups the times into intervals, where the origin is the campaign start time e.g every time between 2025-02-01 00:00:00 and 2025-02-01 00:09:59 will be grouped together if the sampling interval is 10 minutes
    
    # Get uptime for each interval
    uptime_per_interval = []
    total_start_cut_off_count = 0
    total_end_added_count = 0

    # Iterrating through the interval start times 18:10, 18:20, 18:30 etc...
    for interval_start_time in interval_start_times:
        interval_end_time = interval_start_time + pd.Timedelta(
            sampling_interval_in_minutes_str
        )  # End time of the interval

        # Get times within the current interval
        try:
            interval_times = grouped_dataset_time_series.get_group(
                interval_start_time
            ).values
        except (
            KeyError
        ):  # KeyError occurs if the dataset has no samples in this interval
            interval_times = np.array([])

        # Check interval times
        if interval_times.size == 0:
            uptime_in_interval = 0.0
            start_cut_off_count = 0
            end_added_count = 0
            end_added_seconds = 0
            ignore_time = True
        else:
            # Calculate uptime for the n-th interval
            (
                uptime_in_interval,
                start_cut_off_count,
                end_added_count,
                end_added_seconds,
            ) = uptime_from_interval_times(
                interval_times,
                interval_start_time=interval_start_time,
                interval_end_time=interval_end_time,
                max_sampling_time=max_sampling_time_in_seconds,
            )

        # Accumulate totals
        total_start_cut_off_count += start_cut_off_count
        total_end_added_count += end_added_count

        # Determine if interval should be ignored based on threshold
        threshold_for_interval = ds.attrs.get("threshold_for_interval", None)
        if threshold_for_interval is None:
            raise ValueError("Dataset attribute 'threshold_for_interval' not found.")
        ignore_time = uptime_in_interval < threshold_for_interval
        uptime_per_interval.append(
            (
                interval_start_time,
                interval_end_time,
                uptime_in_interval,
                ignore_time,
                len(interval_times),
                start_cut_off_count,
                end_added_count,
                end_added_seconds,
            )
        )

    return pd.DataFrame(
        uptime_per_interval,
        columns=[
            "interval_start_time",
            "interval_end_time",
            "uptime",
            "ignore_time",
            "n_samples",
            "start_cut_off_count",
            "end_added_count",
            "end_added_seconds",
        ],
    )
