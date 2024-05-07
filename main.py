from audible_manager import AudibleManager
from transcriber import Transcriber
import sys


def has_valid_configs(transcriber, manager):
    return (
        transcriber.client is not None
        and manager.auth is not None
        and manager.username is not None
    )


def check_for_valid_configs():
    transcriber = Transcriber()
    manager = AudibleManager(transcriber=transcriber)
    if not has_valid_configs(transcriber=transcriber, manager=manager):
        print(
            "Please run `python main.py login` to authenticate to Audible and OpenAI."
        )
        return None, None
    return transcriber, manager


def get_user_info():
    username = input("Enter your Audible username: ")
    password = input("Enter your Audible password: ")

    # Mapping of country codes to descriptions
    country_codes = {
        "us": "US and all other countries not listed",
        "ca": "Canada",
        "uk": "UK and Ireland",
        "au": "Australia and New Zealand",
        "fr": "France, Belgium, Switzerland",
        "de": "Germany, Austria, Switzerland",
        "jp": "Japan",
        "it": "Italy",
        "in": "India",
        "es": "Spain",
        "br": "Brazil",
    }

    # Display the country codes to the user
    print(
        "Please enter the two-letter Audible account country code from the following options:"
    )
    for code, description in country_codes.items():
        print(f"- {code}: {description}")

    # Get valid country code from the user
    country_code = input("Enter your country code: ").lower()
    while country_code not in country_codes:
        print(
            "Invalid country code. Please enter a valid two-letter country code from the list above."
        )
        country_code = input("Enter your country code: ").lower()

    openai_key = input("Enter your OpenAI API key: ")

    return username, password, country_code, openai_key


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "login":
            transcriber = Transcriber()
            manager = AudibleManager(transcriber=transcriber)

            if has_valid_configs(transcriber=transcriber, manager=manager):
                print(
                    f"You are already logged in as {manager.username}. If you would like to log in as a different user, please delete the following two folders under the `data` directory: \n - audible_configs \n - transcriber_configs"
                )
                return

            username, password, country_code, openai_key = get_user_info()

            transcriber = Transcriber(openai_key=openai_key)

            manager = AudibleManager(transcriber=transcriber)

            if manager.auth is not None:
                print("You are already logged in.")
            else:
                manager.authenticate(
                    username=username, password=password, country_code=country_code
                )

            manager.save_library()
        elif command == "list":
            transcriber, manager = check_for_valid_configs()
            if transcriber and manager:
                manager.save_library()
                library = manager.load_library()
                print("ASIN\t\t Title")
                for book in library:
                    print(f"{book['asin']}\t {book['title']}")

        elif command == "transcribe_bookmarks":
            if len(sys.argv) < 3:
                print(
                    "Please provide the ASIN of the book you want to transcribe.\n Usage: python main.py transcribe_bookmarks <ASIN>\n To get a list of ASINs, run `python main.py list`"
                )
                return
            transcriber, manager = check_for_valid_configs()
            if transcriber and manager:
                asin = sys.argv[2]
                book = manager.get_book_by_asin(asin)
                if book is None:
                    print("Book not found in library.")
                    return

                print(f"Downloading book {book['title']}. This may take a few minutes.")
                manager.download_and_convert_book(asin)

                print(f"Extracting bookmarked clips from {book['title']}.")
                manager.extract_audio_clips(asin)

                print(f"Transcribing bookmarked clips from {book['title']}.")
                manager.transcribe_audio_clips(asin)

        else:
            print("Unknown command")
    else:
        print("No command provided")


if __name__ == "__main__":
    main()
