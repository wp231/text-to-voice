import json

CONFIG_FILE_PATH = "config.json"


class ConfigDAO:
    def __init__(self, config_file: str) -> None:
        self.config_file = config_file
        self.config = self.read()

    def read(self):
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def get_voice_name(self) -> str:
        return self.config['voice_name']

    def get_voice_rate(self) -> int:
        return self.config['voice_rate']

    def get_voice_pitch(self) -> int:
        return self.config['voice_pitch']

    def get_voice_volume(self) -> float:
        return self.config['voice_volume']


config_dao = ConfigDAO(CONFIG_FILE_PATH)
