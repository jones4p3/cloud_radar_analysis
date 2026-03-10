# import numpy as np

# def get_occurrences_min_max_from_datasets(datasets, use_aligned = False):
#     """
#     Get the global minimum and maximum occurrence values across multiple datasets.

#     Parameters:
#     datasets (dict): A dictionary where keys are dataset names and values are xarray Datasets containing 'occurrences' variable.
#     Returns:
#     tuple: A tuple containing the global minimum and maximum occurrence values.
#     """
#     global_occurrences_min = np.inf
#     global_occurrences_max = -np.inf

#     for dataset_handle, ds in datasets.items():
#         if use_aligned and "occurrences_aligned" in ds:
#             occurrences = ds["occurrences_aligned"]
#         else:
#             occurrences = ds["occurrences"]
#         occurrences_min = occurrences.attrs.get("min", np.nan)
#         occurrences_max = occurrences.attrs.get("max", np.nan)

#         if occurrences_min < global_occurrences_min:
#             global_occurrences_min = occurrences_min
#             print(f"New global minimum occurrences found: {global_occurrences_min}% from dataset {dataset_handle}")
#         if occurrences_max > global_occurrences_max:
#             global_occurrences_max = occurrences_max
#             print(f"New global maximum occurrences found: {global_occurrences_max}% from dataset {dataset_handle}")

#     return global_occurrences_min, global_occurrences_max