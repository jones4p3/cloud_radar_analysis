import logging
import matplotlib.pyplot as plt
import os
import scienceplots
import numpy as np

# Plotting configuration
plt.style.use(['science', 'grid'])  # Using SciencePlots style for prettier plots and adding grid
plt.rcParams.update(
     {
         "text.usetex": True, # Use LaTeX for text rendering
         "font.family": "serif",
         "figure.dpi": '200' # Set higher DPI for better quality
     }
 )  

logger = logging.getLogger("cloud_plotting")

# ---------------
# Radar Sensitivity Profiles
# ---------------
def plot_radar_sensitivity_profiles(data):
    fig, ax = plt.subplots(figsize=(6,4), layout="constrained")
    sensitivity_add_in_dbz = 3
    colors = plt.get_cmap("tab10").colors
    for idx, (radar_slug, ds) in enumerate(data.radar_datasets.items()):
        band = ds.attrs["band"]
        sensitivity = ds["sensitivity"]
        # cloud_detection_sensitivity = sensitivity + sensitivity_add_in_dbz
        sensitivity.plot(y="height", linestyle='-', color=colors[idx], label=f"{band}")
        # cloud_detection_sensitivity.plot(y="height", label=f"{band}", linestyle="--", color=colors[idx])
    ax.set_title("Radar sensitivity profiles")
    ax.set_ylabel("Height (m)")
    ax.set_xlabel("Radar Reflectivity $Z_{e}$ (dBZ)")
    ax.legend(title=f"Solid: Cloud detection sensitivity +{sensitivity_add_in_dbz} dBZ\nDashed: Sensitivity",ncol=2, loc='upper left', frameon=True, handlelength=1.5, columnspacing=5, title_fontsize=11, fontsize=9)
    ax.legend(loc="upper left")
    plt.savefig(os.path.join(data.figure_folder, "radar_sensitivity_profiles.png"), dpi=300, bbox_inches='tight')
    logger.info("🖼️  Radar sensitivity profiles saved.")


# ---------------
# Time Fraction Plots
# ---------------
def plot_time_fraction_profiles(data):
    vars = ["clear_sky_fraction", "cloudiness_fraction", "precipitation_fraction", "multilayer_fraction"]  # Variable to plot
    plot_colors = plt.get_cmap("tab10").colors

    for var in vars:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8, 4.5), constrained_layout=False)
    
        # Plot each radar dataset
        for (radar_slug, ds), color in zip(data.radar_datasets.items(), plot_colors):

            # Grab var - data
            var_frct = ds[var]
            var_prct = var_frct * 100

            # Calculate mean for legend
            var_mean = var_prct.mean(dim="time_interval")
            var_mean = var_mean.compute()

            # Get band name for legend
            band = ds.attrs.get("band", "Unknown Band")
        
            # Plot 
            var_prct.plot(label=f"{band} ({var_mean:.2f}\\%)", color=color, marker=".")
            ax.axhline(var_mean, color=color, linestyle="--", linewidth=0.85, alpha=0.8)
        plt.title(f"Daily {var.replace('_', ' ').title()} Profiles")
        plt.ylabel(f"Daily {var.replace('_', ' ').title()} (\\%)")
        plt.xlabel("Date")
        plt.legend(fontsize="small")
        plt.savefig(os.path.join(data.figure_folder, f"daily_{var}.png"), dpi=300, bbox_inches="tight")
        logger.info(f"🖼️  Daily {var.replace('_', ' ').title()} plot saved.")

def plot_cloud_fraction(data):
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(6, 4), constrained_layout=True)
    colors = plt.get_cmap("tab10").colors
    cloud_fractions_results = {}
    # Cloud fraction per height over campaign
    for (radar_slug, ds), color in zip(data.radar_datasets.items(), colors):
        logger.debug(f"Plotting cloud fraction per height for radar: {radar_slug}")
        band = ds.attrs.get("band", "Unknown Band")
        cloud_fraction_campaign = ds["cloud_fraction_binned"].mean(dim="time") * 100 # Convert to percentage
        cloud_fractions_results[radar_slug] = cloud_fraction_campaign

        # Plot cloud fractions campaign
        cloud_fraction_campaign.plot(ax=ax, y="height_bin", label=band, color=color)

        # Plot percentiles
    ax.set_title("Cloud Fraction per Height over Campaign")
    ax.set_ylabel("Height (m)")
    ax.set_xlabel(r"Cloud Fraction (\%)")
    # ax.grid()
    ax.legend()
    plt.savefig(os.path.join(data.figure_folder, f"cloud_fraction_per_height.png"), dpi=300, bbox_inches="tight")
    logger.info("🖼️  Cloud fraction per height plot saved.")

def plot_general_vertical_distribution(data, plot_start_height=151):
    var_to_plot = ["cloud_base_in_m_fraction_binned", "cloud_top_in_m_fraction_binned", "cloud_thickness_in_m_fraction_binned"]
    var_to_mean = ["cloud_base_in_m", "cloud_top_in_m", "cloud_thickness_in_m"]
    y_labels = ["Height (m)", None, "Cloud Thickness (m)"]
    titles = ["Cloud Base Height", "Cloud Top Height", "Cloud Thickness"]
    percentiles_to_plot = [25, 50, 75, 90]
    line_styles_percentiles = [("v", ":"),("x", "-"),("o", "--"),("^", "-.")] # marker, linestyle
    marker_size = 2.5
    plot_start_height = plot_start_height # in meters

    # Create a big figure to hold all subplots
    big_fig, big_axes = plt.subplots(nrows=1, ncols=3, figsize=(8,4.5), constrained_layout=True)
    plot_colors = plt.get_cmap("tab10").colors

    # Plot each variable
    for var, var_mean, y_label, ax in zip(var_to_plot, var_to_mean, y_labels, big_axes):

        # Array to store the switches
        range_gates_lines = []

        # Choose dims
        if var == "cloud_thickness_in_m_fraction_binned":
            dim_name = "thickness_bin"

        else:
            dim_name = "height_bin"

        # Plot cloud variables
        for (radar_slug, ds), color in zip(data.radar_datasets.items(), plot_colors):
            logger.debug(f"Plotting binned {var} for radar: {radar_slug}")
            band = ds.attrs.get("band", "Unknown Band")

            # Grab unique range gate sizes and their indices
            unique_gates, idx = np.unique(ds["rounded_range_gate_sizes"], return_index=True)

            # Extract cloud variable
            cloud_var = ds[var] * 100 # Convert to percentage
            logger.debug(f"------------------- LOWEST PERCETANGE: {cloud_var.values[0]}")
            mean_value = ds[var_mean].mean(dim=["time", "layer"]).compute()
            cdf = cloud_var.cumsum(dim=dim_name)
            # print(f"Comapre: {len(cdf)} to {len(cloud_var)}")
            for (percentile, (marker, linestyle)) in zip(percentiles_to_plot, line_styles_percentiles):
                percentile_value = np.where(cdf >= percentile)[0][0]
                percentile_height = ds[dim_name].isel({dim_name: percentile_value})
                # ax.axhline(percentile_height, color=color, linestyle=linestyle, linewidth=0.8, alpha=0.7, xmin=0, xmax=0.3, label=f"{band} {percentile}th pct.")
                ax.plot(0, percentile_height, color=color, marker=marker, ms=marker_size, ls=None)
                logger.debug(f"{percentile}th percentile for {var} in radar {radar_slug}: {percentile_height.values} m")

            logger.debug(f"Distribution sum: {cloud_var.sum().values}")
            logger.debug(f"Mean value for {var_mean} in radar {radar_slug}: {mean_value.values}%")

            # Limit to start height
            if var == "cloud_base_in_m_fraction_binned":
                start_idx = np.searchsorted(ds[dim_name].values, plot_start_height)
                cloud_var = cloud_var.isel({dim_name: slice(start_idx, None)})
                logger.debug(f"Limiting cloud base distribution to start height of {plot_start_height} m")
                logger.debug(f"Start index for height bin: {start_idx}")

        

            # Limit to start height
            if var == "cloud_base_in_m_fraction_binned":
                # start_idx = ds[dim_name].sel(height_bin=plot_start_height, method="nearest").values
                logger.debug(f"Limiting cloud base distribution to start height of {plot_start_height} m")
                logger.debug(f"Start index for height bin: {start_idx}")

                cloud_var = cloud_var.sel(height_bin=slice(start_idx, None))

            # Add horizontal lines for range gate transitions only once per subplot
            if range_gates_lines == []:
                for idx_gate in idx:
                    gate_height = ds["height"][idx_gate].values
                    binned_gate_height = ds[dim_name].sel({dim_name: gate_height}, method="nearest").values
                    logger.debug(f"Adding range gate line at height: {gate_height} m (binned: {binned_gate_height} m)")
                    range_gates_lines.append(binned_gate_height)

            # Plotting
            cloud_var.plot(ax=ax, y=dim_name, label=band, color=color)
            # mean_line = ax.axhline(mean_value, color=color, linestyle="-.", linewidth=1, alpha=1, xmin=0, xmax=100, label=f"{radar_slug}:{mean_value.values:.2f}m")


        # Add horizontal lines for range gate transitions     
        # for height in range_gates_lines:
            # ax.axhline(height, color="purple", linestyle="--", linewidth=0.8, alpha=0.7, xmin=0, xmax=100)

        # Finalize plots
        if "thickness" in var: ax.legend(loc="upper right")
        # ax.legend()
        ax.set_title(titles[var_to_plot.index(var)])
        ax.set_ylabel(y_label)
        ax.set_xlabel(r"Frequency of Occurrence (\%)")
    big_fig.suptitle("General Vertical Distribution of Cloud Layers")
    big_fig.savefig(os.path.join(data.figure_folder, f"all_layers_distribution_{plot_start_height}.png"), dpi=300, bbox_inches="tight")
    logger.info("🖼️  General layer distribution plot saved.")

def plot_per_layer_vertical_distribution(data, plot_start_height=151):
    layers_to_process = [1, 2, 3, 4]
    var_to_plot = ["cloud_base", "cloud_top", "cloud_thickness"]
    mean_var_to_plot = ["cloud_base_in_m", "cloud_top_in_m", "cloud_thickness_in_m"]
    start_height = plot_start_height  # in meters
    percentiles_to_plot = [25, 50, 75, 90]
    line_styles_percentiles = [("v", ":"),("x", "-"),("o", "--"),("^", "-.")] # marker, linestyle
    marker_size = 2.5
    colors = plt.get_cmap("tab10").colors

    overview_fig, overview_axes = plt.subplots(nrows=len(layers_to_process), ncols=3, figsize=(8,10), constrained_layout=True) #(9,12)
    # Build variable names
    for layer, ov_rows in zip(layers_to_process, overview_axes):
        vars_to_plot = [f"{var}_fraction_binned_layer_{layer}" for var in var_to_plot] 

        for var, ov_col, mean_var in zip(vars_to_plot, ov_rows, mean_var_to_plot):
            range_gates_lines = []

            # Choose dims
            if "thickness" in var:
                dim_name = "thickness_bin"
                y_label = f"Cloud Thickness (m)"
            else:
                dim_name = "height_bin"
                y_label = f"Layer {layer}\nHeight (m)"

            # Plot cloud variables
            for (radar_slug, ds), color in zip(data.radar_datasets.items(), colors):
                logger.debug(f"Plotting binned {var} for radar: {radar_slug}, layer: {layer}")
                band = ds.attrs.get("band", "Unknown Band")
            
                # Grab unique range gate sizes and their indices
                unique_gates, idx = np.unique(ds["rounded_range_gate_sizes"], return_index=True)
            
                cloud_var = ds[var] * 100 # Convert to percentage
                cdf = cloud_var.cumsum(dim=dim_name)
                for (percentile, (marker, linestyle)) in zip(percentiles_to_plot, line_styles_percentiles):
                    percentile_value = np.where(cdf >= percentile)[0][0]
                    percentile_height = ds[dim_name].isel({dim_name: percentile_value})
                    # ov_col.axhline(percentile_height, color=color, linestyle=linestyle, linewidth=0.8, alpha=0.7, xmin=0, xmax=0.3, label=f"{band} {percentile}th pct.")
                    ov_col.plot(0, percentile_height.values, color=color, marker=marker, ms=marker_size, ls=None)
                    logger.debug(f"{percentile}th percentile for {var} in radar {radar_slug}: {percentile_height.values} m")

                mean_value = ds[mean_var].sel(layer=layer).mean(dim=["time"])
                logger.debug(f"Distribution sum: {cloud_var.sum().values}")
                logger.debug(f"Mean value for {mean_var} in radar {radar_slug}, layer {layer}: {mean_value.values}")

                # Limit to start height
                if var == f"cloud_base_fraction_binned_layer_{layer}":
                    start_idx = np.searchsorted(cloud_var[dim_name].values, start_height)
                    cloud_var = cloud_var.isel({dim_name: slice(start_idx, None)})

                if range_gates_lines == []:
                    for idx_gate in idx:
                        gate_height = ds["height"][idx_gate].values
                        binned_gate_height = ds[dim_name].sel({dim_name: gate_height}, method="nearest").values
                        # ov_col.axhline(binned_gate_height, color="purple", linestyle="--", linewidth=0.7, alpha=0.5, xmin=0, xmax=100)

                # Plotting
                cloud_var.plot(ax=ov_col, y=dim_name, label=band)
                # mean_line = ov_col.axhline(mean_value, color="black", linestyle="-.", linewidth=1, alpha=1, xmin=0, xmax=100)

            
                if "top" in var:
                    ov_col.set_ylabel(None)
                else:
                    ov_col.set_ylabel(y_label)
                ov_col.set_xlabel("Frequency of Occurrence (\\%)")

            if "thickness" in var:
                ov_col.legend(loc="upper right")
        
    # Label the overview plot
    first_row = overview_axes[0]
    first_row[0].set_title("Cloud Base Height")
    first_row[1].set_title("Cloud Top Height")
    first_row[2].set_title("Cloud Thickness")

    for row in range(len(layers_to_process)):
        col_0 = overview_axes[row,0]
        col_1 = overview_axes[row,1]
        col_1.sharey(col_0)

    overview_fig.suptitle("Per Layer Vertical Distribution")
    overview_fig.savefig(f"{data.figure_folder}per_layer_overview.png", dpi=300, bbox_inches="tight")
    logger.info("🖼️  Per layer vertical distribution overview plot saved.")