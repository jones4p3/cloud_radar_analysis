import matplotlib.pyplot as plt
import os

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
    # ax.set_title("Radar sensitivity profiles")
    ax.set_ylabel("Height (m)")
    ax.set_xlabel("Radar Reflectivity $Z_{e}$ (dBZ)")
    ax.legend(title=f"Solid: Cloud detection sensitivity +{sensitivity_add_in_dbz} dBZ\nDashed: Sensitivity",ncol=2, loc='upper left', frameon=True, handlelength=1.5, columnspacing=5, title_fontsize=11, fontsize=9)
    ax.legend(loc="upper left")
    plt.savefig(os.path.join(data.figure_folder, "radar_sensitivity_profiles.png"), dpi=300, bbox_inches='tight')
    
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
        plt.ylabel(f"Daily {var.replace('_', ' ').title()} (\\%)")
        plt.xlabel("Date")
        plt.legend(fontsize="small")
        plt.savefig(os.path.join(data.figure_folder, f"daily_{var}.png"), dpi=300, bbox_inches="tight")