
import json
from classes import RadarSettings


def load_radar_settings(radar_settings_path: str) -> dict:
    try:
        with open(radar_settings_path, 'r') as file:
            # Load radar settings from the specified JSON file
            radar_settings = json.load(file)

        # Create RadarSettings objects for each radar and store them in a dictionary
        radar_settings_dict = {}
        for radar_slug, settings in radar_settings.items():
            radar_settings_dict[radar_slug] = RadarSettings(**settings)

    except Exception as e:
        print(f"❌ Error loading radar settings: {e}")
    return radar_settings_dict