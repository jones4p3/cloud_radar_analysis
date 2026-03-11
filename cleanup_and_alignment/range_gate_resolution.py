import numpy as np


def calculate_range_gate_resolution(data, params):
    debug = params.debug
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

        if debug:
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
        if debug:
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
    return data, unique_range_gate_sizes