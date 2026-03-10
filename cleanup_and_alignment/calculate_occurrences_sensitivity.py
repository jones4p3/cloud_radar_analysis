import numpy as np
import xarray as xr
def create_global_bin_edges(radar_datasets, bin_size=0.1):
    print("Creating global bin edges for all radars.")
    mins = []
    maxs = []
    for _, ds in radar_datasets.items():
        ze = ds["ze"]
        mins.append(float(ze.min(skipna=True)))
        maxs.append(float(ze.max(skipna=True)))
    min_ze = np.nanmin(mins)
    max_ze = np.nanmax(maxs)
    bin_edges = np.arange(min_ze, max_ze + bin_size, bin_size)
    print(f"Global bin edges created from {min_ze} to {max_ze} with bin size {bin_size}.")
    return bin_edges

def calculate_occurrences(ds, bin_edges, use_aligned=False):
    radar_name = ds.attrs.get("radar_name", "Unknown Radar")
    bin_size = bin_edges[1] - bin_edges[0]
    print(f"Calculating occurrences for radar: {radar_name} with bin size: {bin_size}")

    # Get reflectivity values
    ds = ds.copy()  # Work on a copy to avoid modifying the original dataset
    ze = ds["ze"].compute()

    # Define bins for histogram
    bin_edges = bin_edges
    bin_centers = bin_edges[:-1] + bin_size / 2  # Calculate bin centers
    nbins = len(bin_centers)

    # Information printing
    print(f"Reflectivity min: {bin_edges[0]:.2f}, max: {bin_edges[-1]:.2f}, #Bins: {len(bin_centers)}, Lower edge first bin: {bin_edges[0]:.2f}, Upper edge last bin: {bin_edges[-1]:.2f}")

    # Grab shape info
    ntime, nheight = ze.shape

    # Initialize occurrences array
    counts_for_each_height = np.zeros((nheight, nbins), dtype=int) # Array with shape (nheight, nbins)

    # Calculate occurrences for each height level
    for current_height in range(nheight):
        # Extract reflectivity values at the current height level
        ze_at_height = ze[:, current_height] # Shape: (ntime,)
        ze_at_height = ze_at_height[~np.isnan(ze_at_height)]  # Remove NaN values

        # Compute histogram for the current height level
        counts_at_current_height, _ = np.histogram(ze_at_height, bins=bin_edges) #counts_at_current_height contains the counts for each bin shape: (nbins,)

        # Store the histogram counts in the occurrences array
        counts_for_each_height[current_height, :] = counts_at_current_height
    
    height = np.asarray(ds["height"].values).squeeze()
    # Wrap back into xarray with correct dims/coords
    bin_name = "bin_aligned" if use_aligned else "bin"
    counts_name = "counts_aligned" if use_aligned else "counts"
    occ_name = "occurrences_aligned" if use_aligned else "occurrences"

    xr_da = xr.DataArray(
        counts_for_each_height, # Writes the numpy array
        dims=["height", bin_name], # Dims names
        coords={
            "height": height,
            bin_name: bin_centers,
        },
        name=counts_name,
        attrs={
            "description": f"Reflectivity counts over the selected time range with a {bin_size} bin size.",
            "long_name": f"Reflectivity counts ({bin_size} dBZ bins)",
            "units": "counts",
        }
    )
    ds[xr_da.name] = xr_da  # Add DataArray to the original dataset


    # Calculate the occurrence percentages
    n_measurements = ds.sizes["time"]
    occurrences = (counts_for_each_height / n_measurements) * 100 # Convert occurrences to percentage
    xr_da_occurrences = xr.DataArray(
        occurrences,
        dims=["height", bin_name],
        coords={
            "height": height,
            bin_name: bin_centers,
        },
        name=occ_name,
        attrs={
            "description": f"Reflectivity occurrences over the selected time range with a {bin_size} bin size.",
            "long_name": f"Reflectivity occurrences ({bin_size} dBZ bins)",
            "units": "percentage (%)",
            "min": occurrences.min().item(),
            "max": occurrences.max().item(),
        }
    )
    xr_da_occurrences["height"].attrs.update(
        long_name="Height above ground level",
        units="m"
    )
    xr_da_occurrences[bin_name].attrs.update(
        long_name="Reflectivity",
        units="dBZ"
    )
    ds[xr_da_occurrences.name] = xr_da_occurrences  # Add DataArray to the original dataset

    return ds

def calculate_sensitivity(ds, threshold=0.999, min_samples_threshold=50):
    print(f"Calculating sensitivity for threshold: {threshold}")
    occurrences_sorted = ds["occurrences"].sortby("bin", ascending=True)  # Ensure bins are sorted in ascending order

    # Probalilty density function (PDF)
    # The pdf answers the question of "how likely is it to observe a certain reflectivity value" so thats why we normalize by the sum over all bins (which is our x-axis) So we get a distribution that sums to 1 over all bins.
    # e.g if we have 10 bins and each bin has an occurrence of 10% then the pdf will be 0.1 for each bin and the sum will be 1.0 this is done for each height level independently. e.g [0.1, 0.1, 0.1, ..., 0.1] sum = 1.0
    pdf = occurrences_sorted / occurrences_sorted.sum(dim="bin")

    # Cumulative distribution function (CDF)
    # This takes the cumulative sum of the pdf so it answers the question "what is the probability of observing a reflectivity value less than or equal to a certain value", where we can use this to find the reflectivity value at which we have a certain probability (threshold) of observing a reflectivity value less than or equal to that value. e.g [0.1, 0.2, 0.3, ..., 1.0]
    cdf = pdf.cumsum(dim="bin")

    # As we are looking for the lowest reflectivity after which we can observe the amount of reflectivity values defined by the threshold. 
    sensitivity_threshold = 1 - threshold 
    sensitvity = cdf["bin"].where(cdf >= sensitivity_threshold).min(dim="bin") # Looks for the minimum bin value where the cdf is greater than or equal to the sensitivity threshold for each height level

    print(f"Removing sensitivity values which dont pass the threshold of having at least {min_samples_threshold} occurrences in the bin")
    n_samples = ds["counts"].sum(dim="bin") # Total number of samples for each height level
    sensitvity = sensitvity.where(n_samples >= min_samples_threshold, np.nan)

    ds["sensitivity"] = sensitvity
    ds["sensitivity"].attrs.update(
        description=f"Reflectivity sensitivity at which {threshold*100}% of the reflectivity values are observed above this value.",
        long_name="Reflectivity sensitivity",
        units="dBZ"
    )
    
    return ds
