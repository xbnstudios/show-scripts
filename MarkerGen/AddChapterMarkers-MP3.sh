#!/bin/bash

# v.2
# Add chapter info from the metadata generator to mp3 files
# supply preformatted metadata files

echo "Requirements: ffmpeg"
echo -e "\nThis script will go through the metadata folder and replace metadata on every mp3 it can find metadata files for.\nDelete *_metadata for episodes that you don't want to be processed.\n"
read -p "Path to .mp3 files: " srcpath
read -p "Replace source files? [y/N] " delete
read -e -p "Path to the metadata folder: " -i "./metadata" meta
if [[ "$delete" == "y" ]]; then
	dstpath="$srcpath"
else
	read -e -p "Where to store processed files: " -i "$srcpath" dstpath
fi

# change container from mp3 to m4a
for file in $meta/*; do
	name=`basename $file | cut -d'_' -f1`;
	echo $name;
	ffmpeg -i "$srcpath/$name.mp3" -i "$file" -map_metadata 1 -c:a copy -id3v2_version 3 -write_id3v1 1 "$dstpath/${name}-withchapters.mp3" # embed new metadata
	if [[ "$delete" == "y" ]]; then mv "$dstpath/$name-withchapters.mp3" "$srcpath/$name.mp3"; fi
done

echo "Program completed sucessfully."
exit 0