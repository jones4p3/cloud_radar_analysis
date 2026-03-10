import numpy as np

def get_min_spacing_and_thickness(unique_range_gate_sizes, cloud_detection_settings, cloud_base_gate, cloud_top_gate, range_gate_sizes, detailed_debug=False):
    min_cloud_spacing_array = cloud_detection_settings.get("min_cloud_spacing_in_m", None)
    min_cloud_thickness_array = cloud_detection_settings.get("min_cloud_thickness_in_m", None)
    if min_cloud_spacing_array is None or min_cloud_thickness_array is None:
        raise ValueError("Minimum cloud spacing and thickness arrays must be provided in cloud_detection_settings.")
    # Get range gate sizes at base and top of cloud layer plus idx in unique sizes array
    base_range_gate_size = range_gate_sizes[cloud_base_gate].item() # The vertical resolution at the cloud base in meters
    top_range_gate_size = range_gate_sizes[cloud_top_gate].item()  # The vertical resolution at the cloud top in meters

    # Calculate difference in base,top range_gate_size to each unique range gate size
    diff_base = np.abs(unique_range_gate_sizes - base_range_gate_size)
    diff_top = np.abs(unique_range_gate_sizes - top_range_gate_size)

    # Choose the closest matching unique range gate size
    closest_base_idx = np.argmin(diff_base)
    closest_top_idx = np.argmin(diff_top)

    # Get the indices in the unique range gate sizes array
    idx_base_spacing_thickness = np.where(unique_range_gate_sizes == unique_range_gate_sizes[closest_base_idx])[0][0]
    idx_top_spacing_thickness = np.where(unique_range_gate_sizes == unique_range_gate_sizes[closest_top_idx])[0][0]

    if detailed_debug:
        print(f"   - Cloud base range gate size: {base_range_gate_size} m (idx: {idx_base_spacing_thickness})")
        print(f"   - Cloud top range gate size: {top_range_gate_size} m (idx: {idx_top_spacing_thickness})")

    # Check resolution for cloud layer
    # Same resolution throughout cloud layer
    if idx_base_spacing_thickness == idx_top_spacing_thickness:
        min_cloud_spacing_in_m = min_cloud_spacing_array[idx_base_spacing_thickness]
        min_cloud_thickness_in_m = min_cloud_thickness_array[idx_base_spacing_thickness]
            
        if detailed_debug: 
            print(f"   - Cloud layer has uniform range gate size of {base_range_gate_size} m, using min spacing {min_cloud_spacing_in_m} m and min thickness {min_cloud_thickness_in_m} m.")

    # Different resolutions within cloud layer -> use the top resolution for spacing and thickness
    else:
        # Spacing
        min_cloud_spacing_in_m = min_cloud_spacing_array[idx_top_spacing_thickness]

        # Thickness
        min_cloud_thickness_in_m = min_cloud_thickness_array[idx_top_spacing_thickness]

        if detailed_debug: 
            print(f"   - Cloud layer has varying range gate sizes from {base_range_gate_size:.2f} meters to {top_range_gate_size:.2f} meters, using top min spacing and thickness.")
            print(f"       - Using spacing top: {min_cloud_spacing_in_m} meters")
            print(f"       - Using thickness top: {min_cloud_thickness_in_m} meters")

    return min_cloud_spacing_in_m, min_cloud_thickness_in_m

def check_spacing_to_previous_layer(cloud_layers_in_time_step, cloud_base_in_m, min_cloud_spacing_in_m, detailed_debug=False):
    # Grab previous layer info
    previous_layer = cloud_layers_in_time_step[-1] # Getting the last added layer
    previous_cloud_top_in_m = previous_layer[1][1] # Getting the top height of the previous layer (gate[bottom, top, thickness], height[bottom, top, thickness], label)
    spacing_with_previous_layer_in_m = cloud_base_in_m - previous_cloud_top_in_m
    if spacing_with_previous_layer_in_m <= min_cloud_spacing_in_m:
        # Cloud is too close to previous layer to count as a new layer, add to previous layer
        if detailed_debug: print(f"🤏 ☁️ Cloud layer SPACING too close | Spacing: {spacing_with_previous_layer_in_m:.2f}m missing {min_cloud_spacing_in_m - spacing_with_previous_layer_in_m:.2f}m (should be {min_cloud_spacing_in_m} m) | Current base: {cloud_base_in_m}m | Previous top: {previous_cloud_top_in_m} previous layer.")
        return True
    else:
        if detailed_debug: print(f"✔️ ☁️ Cloud layer spacing okay")
        return False

def edit_previous_layer_with_new_cloud_layer(cloud_layers_in_time_step, cloud_top_gate, cloud_top_in_m, detailed_debug=False):
    # Grab previous layer data
    previous_layer = cloud_layers_in_time_step[-1]
    previous_gate_data = previous_layer[0] # (gate[bottom, top, thickness], height[bottom, top, thickness], label)
    previous_height_data = previous_layer[1]
    previous_layer_label = previous_layer[2]
    # Calculate new thickness
    layer_thickness_in_gates = cloud_top_gate - previous_gate_data[0] # New top - old bottom
    layer_thickness_in_m = cloud_top_in_m - previous_height_data[0] # New top - old bottom
    # Accumulate new top and thickness
    new_gate_data = (previous_gate_data[0], max(previous_gate_data[1], cloud_top_gate), layer_thickness_in_gates)
    new_height_data = (previous_height_data[0], max(previous_height_data[1], cloud_top_in_m), layer_thickness_in_m)
    # Update the previous layer
    cloud_layers_in_time_step[-1] = (new_gate_data, new_height_data, previous_layer_label)
    if detailed_debug:
        print(f"🛠️ Updated previous cloud layer [{previous_layer_label}] with new top at gate {new_gate_data[1]} and height {new_height_data[1]:.2f} m")
        print(f"✅ ☁️ Cloud layer added to previous layer [{previous_layer_label}] -- New Cloud top: {cloud_top_in_m:.2f} m, New Thickness: {layer_thickness_in_m:.2f} m")
        print(f"✅ ☁️ Cloud layer information -- Cloud base: {new_height_data[0]:.2f} m, Cloud top: {new_height_data[1]:.2f} m, Thickness: {new_height_data[2]:.2f} m")
    return cloud_layers_in_time_step

def analyze_possible_cloud_layers(height, range_gate_sizes, unique_range_gate_sizes, possible_cloud_layers, cloud_detection_settings, detailed_debug=False):
    if detailed_debug: print("- Analyzing possible cloud layers for spacing and thickness criteria.")
    layer_label = 0
    cloud_layers_in_time_step = []
    min_cloud_thickness_array = cloud_detection_settings.get("min_cloud_thickness_in_m", False)
    min_cloud_spacing_array = cloud_detection_settings.get("min_cloud_spacing_in_m", False)
    min_cloud_thickness_in_m = min_cloud_thickness_array[0]
    min_cloud_spacing_in_m = min_cloud_spacing_array[0]

    for layer_idx, cloud_parameters in enumerate(possible_cloud_layers):
        # Base
        cloud_base_gate = cloud_parameters[0] # This is the correct base gate, where the cloud starts in the center
        cloud_base_in_m = height[cloud_base_gate].item() # Base height in meters
            
        # Top
        cloud_top_gate = cloud_parameters[1] # This is the top gate, where the cloud ends in the center (last gate with Ze value)
        cloud_top_in_m = height[cloud_top_gate].item() # Top height in meters

        # Thickness
        cloud_thickness_in_gates = cloud_top_gate - cloud_base_gate # Number of gates in cloud layer doesnt adjust for range gate size switches!!
        if cloud_thickness_in_gates == 0:
            # Only one gate in cloud layer, use that gate's range gate size as thickness
            cloud_thickness_in_m = range_gate_sizes[cloud_base_gate].item() # Doesnt matter if base or top gate since they are the same
        else:
            cloud_thickness_in_m = cloud_top_in_m - cloud_base_in_m # Thickness in meters, where the last gate with Ze value is included, this thickness accounts for range gate size switches

        # Default not adding to previous layer until checked
        adding_to_previous_layer = False

        # Debug prints
        if detailed_debug:
            print(f"☁️ Analyzing possible cloud Layer [{layer_idx + 1} | {len(possible_cloud_layers)}]")
            print(f"   - Cloud base at gate {cloud_base_gate} ({cloud_base_in_m:.2f} m)")
            if cloud_thickness_in_gates == 0:
                print(f"   - Cloud layer consists of only one gate, using that gate's range gate size as thickness.")
            else:
                print(f"   - Cloud top at gate {cloud_top_gate} ({cloud_top_in_m:.2f} m)")
            print(f"   - Cloud thickness: {cloud_thickness_in_m:.2f} m ({cloud_thickness_in_gates} gates)")

        # Spacing and thickness checks
        # Only check spacing if there is already a layer to check with
        if len(cloud_layers_in_time_step) > 0:

            # Get min spacing and thickness for current cloud layer
            min_cloud_spacing_in_m, min_cloud_thickness_in_m = get_min_spacing_and_thickness(
                unique_range_gate_sizes,
                cloud_detection_settings,
                cloud_base_gate,
                cloud_top_gate,
                range_gate_sizes,
                detailed_debug
            )


            # Check spacing to previous layer, returns True/False
            adding_to_previous_layer = check_spacing_to_previous_layer(
                cloud_layers_in_time_step,
                cloud_base_in_m,
                min_cloud_spacing_in_m,
                detailed_debug
            )
            
        # If cloud is to be added to previous layer, do it and continue to next possible layer
        if adding_to_previous_layer:
            cloud_layers_in_time_step = edit_previous_layer_with_new_cloud_layer(
                cloud_layers_in_time_step,
                cloud_top_gate,
                cloud_top_in_m,
                detailed_debug
            )
            continue
            

        # Check minimum thickness if not adding to previous layer
        if cloud_thickness_in_m < min_cloud_thickness_in_m:
            if detailed_debug:
                print(f"👶 Cloud layer too thin ({cloud_thickness_in_m:.2f}m should be bigger than {min_cloud_thickness_in_m:.2f}m) and not added to previous layer, skipping layer.")
            continue

        # If passed all checks, add as new layer
        data_in_gates = (cloud_base_gate, cloud_top_gate, cloud_thickness_in_gates)
        data_in_height = (cloud_base_in_m, cloud_top_in_m, cloud_thickness_in_m)
        layer_label = layer_label + 1
        cloud_layers_in_time_step.append((data_in_gates, data_in_height, layer_label))
            
        if detailed_debug:
            print(f"✅ ☁️ Cloud layer added as new layer [{layer_label}] -- Cloud base: {cloud_base_in_m:.2f} m, Cloud top: {cloud_top_in_m:.2f} m, Thickness: {cloud_thickness_in_m:.2f} m")
    return cloud_layers_in_time_step, len(cloud_layers_in_time_step)

def get_max_layers_in_time_range(all_layers_per_time_range, debug=False):
    max_n_layers = 0
    max_layer_time_step = None
    for time_step, layers in all_layers_per_time_range:
        n_layers = len(layers)
        if n_layers > max_n_layers:
            max_n_layers = n_layers
            max_layer_time_step = time_step
            if debug: print(f"New max number of layers found: {max_n_layers} at time {time_step}")
    print(f"Max number of layers in any time step: {max_n_layers} at time {max_layer_time_step if max_layer_time_step is not None else 'N/A'}")
    return max_layer_time_step, max_n_layers
