import os
import audible
import toml
import json
import subprocess
import math
from utils import format_time


class AudibleManager:
    def __init__(self, transcriber):
        # Attempt to load the Audible API credentials from the config file. If the config file does not exist, silently set auth to None.
        self.transcriber = transcriber
        AUDIBLE_CONFIG_DIR = f"{os.getcwd()}/data/audible_configs/"
        os.environ["AUDIBLE_CONFIG_DIR"] = AUDIBLE_CONFIG_DIR
        self.auth = None

        if not os.path.exists(f"{os.getcwd()}/data/audible_configs/audible.json"):
            return
        else:
            # Load the Audible API credentials from the config file
            self.audible_config_dir = f"{os.getcwd()}/data/audible_configs/"
            self.auth_file = f"{self.audible_config_dir}/audible.json"
            self.username_file = f"{self.audible_config_dir}/username.json"
            self.library_file = f"{self.audible_config_dir}/library.json"

            self.auth = audible.Authenticator.from_file(self.auth_file)
            self.username = json.load(open(self.username_file, "r"))["username"]

    def _generate_toml_config(self, title, primary_profile, country_code):
        """
        Generate a TOML config file for the Audible API.
        """
        file_path = f"{self.audible_config_dir}/config.toml"
        config = {
            "title": title,
            "APP": {"primary_profile": primary_profile},
            "profile": {
                primary_profile: {
                    "auth_file": "audible.json",
                    "country_code": country_code,
                }
            },
        }
        with open(file_path, "w") as file:
            toml.dump(config, file)

    def _find_annotation_file(self, book_dir):
        """
        Find the annotation file for the book (which contains the clips bookmarked by the user) in the given directory.
        """
        for filename in os.listdir(book_dir):
            if filename.endswith("-annotations.json"):
                return os.path.join(book_dir, filename)
        return None

    def _extract_clips_metadata(self, asin):
        """
        Based on the annotation file of the book, extract the metadata (start and end positions) of the audio clips.
        """
        book_dir = f"{os.getcwd()}/data/audio/{asin}"
        annotation_file_path = self._find_annotation_file(book_dir)
        if not annotation_file_path:
            print(f"Annotation file not found for {asin}.")
            return None
        with open(annotation_file_path, "r", encoding="utf-8") as f:
            all_clips = json.load(f)["payload"]["records"]
        return [record for record in all_clips if record.get("type") == "audible.clip"]

    def authenticate(self, username, password, country_code):
        """
        Authenticate the user with the Audible API and store the credentials in a file.
        """
        self.username = username
        self.audible_config_dir = f"{os.getcwd()}/data/audible_configs/"
        self.auth_file = f"{self.audible_config_dir}/audible.json"
        self.username_file = f"{self.audible_config_dir}/username.json"
        self.library_file = f"{self.audible_config_dir}/library.json"

        if os.path.exists(self.auth_file) and os.path.exists(self.username_file):
            self.username = json.load(open(self.username_file, "r"))["username"]
            print(f"Loading config of user {self.username} from {self.auth_file}.")
            self.auth = audible.Authenticator.from_file(self.auth_file)
        else:
            print("Creating new credentials and config files.")
            self.auth = audible.Authenticator.from_login(
                self.username, password, locale=country_code, with_username=False
            )
            if self.auth is None:
                print("Invalid credentials. Please try again.")
                return
            else:
                os.makedirs(self.audible_config_dir, exist_ok=True)
                self.auth.to_file(self.auth_file)
                # Append the username to the config file
                with open(self.username_file, "w") as f:
                    json.dump({"username": self.username}, f, indent=4)

                self._generate_toml_config(
                    "Audible Config File", "audible", country_code
                )
                print("Signed in successfully.")
        return self.auth

    def save_library(self):
        """
        Save the user's Audible library to a JSON file.
        """
        with audible.Client(auth=self.auth) as client:
            library = client.get(
                "1.0/library",
                num_results=1000,
                response_groups="product_desc, product_attrs, customer_rights",
                sort_by="-PurchaseDate",
            )
        with open(self.library_file, "w", encoding="utf-8") as f:
            json.dump(library["items"], f, ensure_ascii=False, indent=4)

    def load_library(self):
        with open(self.library_file, "r", encoding="utf-8") as f:
            library = json.load(f)
        return library

    def get_book_by_asin(self, asin):
        """
        Get the book details from the library using the ASIN.
        """
        library = self.load_library()
        for book in library:
            if book["asin"] == asin:
                return book
        return None

    def download_and_convert_book(self, asin):
        """
        Download the book with the given ASIN and convert it to an MP4 file.

        The conversion is done using a shell script called audible-convert.sh which loads the user credentials from the config file to remove the DRM.
        """
        with subprocess.Popen(
            ["./audible-convert.sh", asin, f"{asin}.mp4"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
        ) as proc:
            while True:
                output = proc.stdout.readline()
                if proc.poll() is not None and output == "":
                    break
                if output:
                    print(output.strip())
            stderr = proc.stderr.read()
            if stderr:
                print("STDERR:", stderr.strip())
            return proc.returncode

    def extract_audio_clips(self, asin):
        """
        Extract audio clips from the book and save them as individual audio files.
        """
        clips_metadata = self._extract_clips_metadata(asin)
        book_dir = f"{os.getcwd()}/data/audio/{asin}"
        audio_clips_dir = f"{book_dir}/clips"
        os.makedirs(audio_clips_dir, exist_ok=True)
        for clip in clips_metadata:
            startPosition = clip["startPosition"]
            endPosition = clip["endPosition"]
            duration = math.floor((int(endPosition) - int(startPosition)) / 1000)
            with subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    f"{book_dir}/{asin}.mp4",
                    "-ss",
                    format_time(int(startPosition)),
                    "-t",
                    str(duration),
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-acodec",
                    "libmp3lame",
                    f"{audio_clips_dir}/clip_{startPosition}.mp3",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
            ) as proc:
                while True:
                    output = proc.stdout.readline()
                    if proc.poll() is not None and output == "":
                        break
                    if output:
                        print(output.strip())
                stderr = proc.stderr.read()
                if stderr:
                    print("STDERR:", stderr.strip())

    def transcribe_audio_clips(self, asin):
        book_dir = f"{os.getcwd()}/data/audio/{asin}"
        clips_metadata = self._extract_clips_metadata(asin)
        audio_clips_dir = f"{book_dir}/clips"
        # if book_dir/transcriptions.json exists, load it
        # else create a new one
        transcribed_notes_file = f"{book_dir}/transcribed_notes.json"

        if os.path.exists(transcribed_notes_file):
            with open(transcribed_notes_file, "r", encoding="utf-8") as f:
                transcribed_notes = json.load(f)
        else:
            transcribed_notes = {}

        # Transcribe the audio clips
        for clip in clips_metadata:
            startPosition = clip["startPosition"]
            clip_file_path = os.path.join(audio_clips_dir, f"clip_{startPosition}.mp3")
            print(f"Transcribing {clip_file_path}.")
            if startPosition not in transcribed_notes:
                transcription = self.transcriber.transcribe(clip_file_path)
                transcribed_notes[startPosition] = transcription
            else:
                print(f"Transcription for {startPosition} already exists.")

        # Save the transcriptions to the file
        with open(transcribed_notes_file, "w", encoding="utf-8") as f:
            json.dump(transcribed_notes, f, ensure_ascii=False, indent=4)

        print(f"Succeeded. Transcriptions saved to {transcribed_notes_file}.")
