#!/bin/bash
if [ -z "$(which ffmpeg)" ] || [ -z "$(which audible)" ] || [ -z "$(which jq)" ]; then
    echo "Error: Needs ffmpeg, audible-cli, and jq installed"
    exit 1
fi

# Check for correct usage
if [[ -z "$1" || -z "$2" ]]; then
    echo "Usage: ./convert.sh <ASIN> <outFile> [--aax]"
    audible library list
    exit 1
fi

ext="${4:-}"
asin="$1"
script_dir=$(dirname "$0")
dir="${script_dir}/data/audio/$1"

# Create tmp directory if it doesn't exist
mkdir -p "$dir"
echo "Using directory: $dir"

if [ "$ext" == "--aax" ]; then
    aax="--aax-fallback"
else
    aax="--aaxc"
fi

audible download -a "$asin" "$aax" --cover --cover-size 1215 --chapter --annotation -o "$dir"

info=$(audible api -p response_groups="media,contributors,series,category_ladders" /1.0/library/"$asin" | jq '.item')

chapter_txt="$dir/chapters.txt"
series_info=$(echo "$info" | jq '.series | if (length > 0) then sort_by(.sequence | if . != "" then tonumber else 0 end) | .[-1] else "" end')

# Check for .voucher files and process them
voucher_files=(${dir}/*.voucher)
if [ ${#voucher_files[@]} -gt 0 ]; then
    echo "Preparing to decrypt aacx file"
    key=$(jq -r '.content_license.license_response.key' <"${voucher_files[0]}")
    iv=$(jq -r '.content_license.license_response.iv' <"${voucher_files[0]}")
    decrypt="-audible_key $key -audible_iv $iv"
else
    echo "Preparing to decrypt aax file"
    decrypt="-activation_bytes $(audible activation-bytes)"
fi
echo "$decrypt"

# Check for copyright information
echo "Checking for copyright"
copyright=$(ffprobe $decrypt "$dir"/*.aax* 2>&1 | grep copyright | sed 's/^.*: //')

# Write book metadata
echo "Writing metadata"
echo ";FFMETADATA1
    title=$(echo "$info" | jq -r '.title')
    artist=$(echo "$info" | jq -r '.authors | [.[].name] | join(", ")')
    composer=$(echo "$info" | jq -r '.narrators | [.[].name] | join(", ")')
    year=$(echo "$info" | jq -r '.release_date | sub("-[0-9][0-9]-[0-9][0-9]"; "")')
    copyright=$copyright
    language=$(echo "$info" | jq -r '.language')
    description=$(echo "$info" | jq -r '.merchandising_summary | sub("</?[a-z]+>"; ""; "g")')
    asin=$asin
    " >"$chapter_txt"

if [ "$series_info" != '""' ]; then
    echo "series=$(echo "$series_info" | jq -r '.title')
        series-part=$(echo "$series_info" | jq -r '.sequence')
        " >>"$chapter_txt"
fi

# Write chapter timestamps to txt
echo "Writing chapter timestamps"
json_files=(${dir}/*.json)
if [ ${#json_files[@]} -gt 0 ]; then
    jq -r 'def flat:
    reduce .[] as $c ([]; if $c.chapters? then .+[$c | del(.chapters)]+[$c.chapters | flat] else .+[$c] end) | flatten;
    .content_metadata.chapter_info.chapters
    | flat
    | .[] |
    "[CHAPTER]
    TIMEBASE=1/1000
    START=\((.start_offset_ms))
    END=\((.start_offset_ms + .length_ms))
    title=\((.title | gsub("\""; "")) | gsub("\\n"; " "))"  # Escaping quotes and newlines
    "' <"${json_files[0]}" >>"$chapter_txt"
else
    echo "No JSON file found in $dir"
fi

# Reencode the file with ffmpeg
if [ ! -f "$dir/$2" ]; then
    echo "Reencoding file"
    # Save as mp4 and route the output for Python to capture
    ffmpeg $decrypt \
        -y -i "$dir"/*.aax* -i "$dir"/*.jpg -i "$chapter_txt" \
        -map 0:a -map 1:v -map_metadata 2 -map_chapters 2 -c:v copy \
        -c:a aac \
        -id3v2_version 3 \
        -disposition:v attached_pic -movflags +faststart -movflags +use_metadata_tags \
        -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" \
        -metadata:s:a language="$(echo "$info" | jq -r '.language | .[0:3]')" \
        "$dir/tmp_$2" 2>&1 | tee ffmpeg_output.log

    echo "Finished reencoding file, renaming file"
    mv "$dir/tmp_$2" "$dir/$2"
else
    echo "File $dir/$2 already exists, skipping reencoding"
fi
