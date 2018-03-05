#!/bin/bash

# v.1
# Losslessly convert .mp3 files to .m4a and add chapter info from the metadata generator.
# supply preformatted metadata file

echo "Requirements: AtomicParsley (for album art embedding), ffmpeg."
read -p "Install them using apt-get now? [y/N] " aptget
if [[ "$aptget" == "y" ]]; then sudo apt-get update && sudo apt-get install atomicparsley ffmpeg --no-install-recommends ; fi
echo -e "\nThis script will go through the metadata folder and convert every .mp3 file it can find metadata for. Delete metadata for episodes that you don't want converted.\n"
read -p "Path to .mp3 files: " srcpath
read -p "Delete source files? [y/N] " delete
read -e -p "Path to metadata folder: " -i "./metadata" meta
read -e -p "Where to store .m4a files: " -i "$srcpath" dstpath

# change container from mp3 to m4a
for file in $meta/*; do
	name=`basename $file | cut -d'_' -f1`;
	echo $name;
	ffmpeg -i "$srcpath/$name.mp3" -i "$file" -map_metadata 1 -codec copy -f mp4 "$dstpath/${name}.m4a" # convert to m4a and embed new metadata
	ffmpeg -i "$srcpath/$name.mp3" -an -vcodec copy "/tmp/${name}_cover.jpg" # extract cover art from mp3
	AtomicParsley "$dstpath/${name}.m4a" --artwork "/tmp/${name}_cover.jpg" --overWrite # and embed it into m4a (ffmpeg STILL doesn't support embedding m4a album art)
	rm "/tmp/${name}_cover.jpg"
	if [[ "$delete" == "y" ]]; then rm "$srcpath/$name.mp3"; fi
done

echo "Program completed sucessfully."
exit 0