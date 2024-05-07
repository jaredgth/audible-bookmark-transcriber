# Audible bookmark transcriber

## Introduction

This is a small tool for [Audible](https://audible.com) users to easily extract their bookmarks from the audio books as text. By default, it uses the state-of-the-art speech-to-text AI model called [Whisper by OpenAI](https://openai.com/index/whisper).

> [!IMPORTANT]
> This tool is only meant to help users download and use the Audible books they **actually own**.

## Limitations
- It only supports English books for now.
- It has only been tested on MacOS. Linux will probably work, but Windows is unlikely.

## User guide
Follow these steps to get started.

### Clone this repo.


### Install the necessary dependencies.
1. `ffmpeg` (if you need to install `brew`, follow the instructions [here](https://brew.sh/))
```
brew install ffmpeg
```  
2. `jq`
```
brew install jq
```  
3. The rest are Python dependencies that can be installed by running the following command. Consider using an environment management tool such as [Conda](https://docs.conda.io/en/latest/).
```
pip install -r requirements.txt
```
 

### Log in to your Audible account and provide an OpenAI API key
Run:
```
python main.py login
```
The command will ask for a few information:
- Your Audible user name (for some users, this is your Amazon user name)
- Your Audible password. This will only be used for authenticating to your Audible account.
- The counry/region of your Audible account.
- Your OpenAI API key. If you don't have one, follow [the steps here](https://platform.openai.com/docs/quickstart).

### Get a list of your Audible books
Run:
```
python main.py list
```
If everything works as expected, you should see a list of Audible books (ASIN + title) printed.

### Extract bookmarks and transcribe
Run:
```
python main.py transcribe_bookmarks <ASIN>
```
where `<ASIN>` is the book ID you want to use.

### Wait for the code to run
It will take a while. Basically the code performs the following steps:
1. Download the original audio book file, remove the DRM using your Audible user credential, and save it as a `.mp4` file.
> [!IMPORTANT]
> The converted `.mp4` file is only meant for your personal use. DO NOT distribute! After the code finish running, you should delete this file to avoid leaks.

2. Extract the bookmarks you created for this book, specifically, the start and end time of each clip.
3. Extract each clip as separate audio files.
4. Call the Whisper API to transcribe the audio clips.

### Completed.
The transcribed notes will be saved in this file: `data/audio/<ASIN>/transcribed_notes.json`.
