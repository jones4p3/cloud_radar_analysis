import json
import sys
from classes import Parameters, SensitivityParameters, OccurrenceParameters, UptimeAlignmentParameters
from dataclasses import asdict

from classes.parameters import CloudDetectionParameters



def load_parameter_settings(parameter_settings_path):
    try:
        with open(parameter_settings_path, 'r') as f:
            parameter_settings = json.load(f)
        
        sensitivty_params = SensitivityParameters(**parameter_settings.get("sensitivity", False))
        occurrence_params = OccurrenceParameters(**parameter_settings.get("occurrence", False))
        uptime_alignment_params = UptimeAlignmentParameters(**parameter_settings.get("uptime_alignment", False))
        cloud_detection_params = CloudDetectionParameters(**parameter_settings.get("cloud_detection", False))

        if not all([sensitivty_params, occurrence_params, uptime_alignment_params, cloud_detection_params]):
            raise ValueError("One or more parameter categories are missing in the parameter settings JSON.")

        params = Parameters(
            sensitivity=sensitivty_params,
            occurrence=occurrence_params,
            uptime_alignment=uptime_alignment_params,
            cloud_detection=cloud_detection_params,
            debug=bool(parameter_settings.get("debug", False))
        )
        return params
    except Exception as e:
        print(f"Error loading parameter settings: {e}")
        sys.exit(1)
        return None

def print_parameter_settings(params):
    print(
    f"✅ Parameter settings loaded with:"
)
    params_dict = asdict(params)
    for param_category, param_values in params_dict.items():
        print(f"   - {param_category}:")
        if isinstance(param_values, dict):
            for key, value in param_values.items():
                print(f"       - {key}: {value}")
        else:
            print(f"       - {param_values}")
    