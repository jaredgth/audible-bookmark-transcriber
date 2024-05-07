from openai import OpenAI
import os
import json


class Transcriber:
    def __init__(self, openai_key=None):
        self.transcriber_config_dir = f"{os.getcwd()}/data/transcriber_configs"
        self.transcriber_config_file = f"{self.transcriber_config_dir}/transcriber.json"
        self.client = None

        # If an OpenAI API key is provided, save it to the config file
        if openai_key is not None:
            self.openai_key = openai_key
            self.client = OpenAI(api_key=self.openai_key)
            os.makedirs(self.transcriber_config_dir, exist_ok=True)
            with open(self.transcriber_config_file, "w") as f:
                json.dump({"openai_key": self.openai_key}, f)
        # Otherwise, attempt to load the key from the config file
        else:
            # Raise an error if the config file does not exist
            # if not os.path.exists(self.transcriber_config_file):
            #     raise FileNotFoundError(
            #         "Transcriber config file does not exist. Please run `python main.py login` to provide an OpenAI API key."
            #     )
            # else:
            # print("Loading OpenAI API key from config file.")
            if os.path.exists(self.transcriber_config_file):
                with open(self.transcriber_config_file, "r") as f:
                    self.openai_key = json.load(f)["openai_key"]
                if self.openai_key is not None:
                    self.client = OpenAI(api_key=self.openai_key)

    def transcribe(self, clip_file_path):
        audio_file = open(clip_file_path, "rb")
        transcription = self.client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        return transcription.text
