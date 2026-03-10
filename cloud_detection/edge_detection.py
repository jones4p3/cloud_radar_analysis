import numpy as np
import sys

def find_cloud_edges(ze_profile, detailed_debug=False):
    if detailed_debug: print("   - Finding cloud edges in reflectivity profile.")
    # Mask for differentiating between: True = non-NaN and False - NaN values
    ze_mask_for_value_detection = ~np.isnan(ze_profile)
    ze_mask = ze_mask_for_value_detection.astype(int)


    # Find switch from non-NaN (cloud) to NaN (no-cloud)
    # +1: NO cloud -> Cloud => Cloud base
    # -1: Cloud -> NO cloud => Cloud top
    cloud_base_edges = np.diff(ze_mask.astype(int), prepend=0)
    cloud_top_edges = np.diff(ze_mask.astype(int), append=0)

    cloud_base_idx = np.where(cloud_base_edges == +1)[0]
    cloud_top_idx = np.where(cloud_top_edges == -1)[0]
    
    if detailed_debug: 
        print(f"      - Cloud base indices: {cloud_base_idx}")
        print(f"      - Cloud top indices: {cloud_top_idx}")
        print(f"   -- RESULT: Found {len(cloud_base_idx)} cloud bases and {len(cloud_top_idx)} cloud tops.\n")
    return cloud_base_idx, cloud_top_idx

def check_cloud_boundaries(cloud_bases, cloud_tops, time_step):
    n_bases = len(cloud_bases)
    n_tops = len(cloud_tops)
    if n_bases != n_tops:
        if n_bases > n_tops:
            sys.exit(f"⚠️ WARNING: Endless cloud detected: {time_step.values}")
        elif n_bases < n_tops:
            sys.exit(f"⚠️ WARNING: There is no bottom for a cloud: {time_step.values}")