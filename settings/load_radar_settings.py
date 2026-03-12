
import json
import sys
from classes import RadarSettings, RadarAttributes, RadarDimensions

def load_radar_settings(radar_settings_path: str) -> dict:
    try:
        with open(radar_settings_path, 'r') as file:
            # Load radar settings from the specified JSON file
            radar_settings = json.load(file)

        # Create RadarSettings objects for each radar and store them in a dictionary
        radar_settings_dict = {}
        for radar_slug, settings in radar_settings.items():
            radar_settings_dict[radar_slug] = RadarSettings(
                slug=settings['slug'],
                data_path=settings['data_path'],
                attributes=RadarAttributes(**settings['attributes']),
                convert_linear_to_dBZ=settings['convert_linear_to_dBZ'],
                add_to_range=settings['add_to_range'],
                vars_to_keep=settings['vars_to_keep'],
                dimension_names=RadarDimensions(**settings['dimension_names'])
                )
        return radar_settings_dict

    except Exception as e:
        print(f"❌ Error loading radar settings: {e}")
        sys.exit(1)
        return None