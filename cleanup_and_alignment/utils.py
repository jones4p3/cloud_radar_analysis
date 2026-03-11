import pandas as pd


def add_uptime_attributes_to_dataset(data, params, ds):
    ds.attrs["campaign_start_time"] = str(data.time_range.start)
    ds.attrs["campaign_end_time"] = str(data.time_range.end)
    ds.attrs["sampling_interval_in_minutes"] = params.uptime_alignment.sampling_interval_in_minutes
    ds.attrs["max_sampling_time_in_seconds"] = params.uptime_alignment.max_sampling_time_in_seconds
    ds.attrs["threshold_for_interval"] = params.uptime_alignment.threshold_for_uptime
    return ds

def build_interval_start_times(ds, sampling_interval_in_minutes_str):
    campaign_start_time, campaign_end_time = (
        ds.attrs["campaign_start_time"],
        ds.attrs["campaign_end_time"],
    )
    interval_start_times = pd.date_range(
        start=campaign_start_time,
        end=campaign_end_time,
        freq=sampling_interval_in_minutes_str,
    )
    return interval_start_times