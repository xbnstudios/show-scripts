#!/usr/bin/env python3
"""
Convert markers between types.
"""

from PostShowV2 import MCS, EpisodeMetadata
import argparse
import sys


def determine_type(filename: str) -> int:
    if filename.endswith(".txt"):
        return MCS.AUDACITY
    elif filename.endswith(".cue"):
        return MCS.CUE
    elif filename.endswith(".lrc"):
        return MCS.LRC
    elif filename.endswith(".ffmetadata1"):
        return MCS.FFMETADATA1
    else:
        raise ValueError("Unsupported file type.")


def main(argv: list):
    parser = argparse.ArgumentParser(description="Convert marker types.")
    parser.add_argument(
        "in_file",
        help="the input marker file. Audacity " "Labels and LRC currently supported.",
    )
    parser.add_argument(
        "out_file", help="the output marker file. CUE and LRC " "currently supported."
    )
    parser.add_argument(
        "-m",
        "--media-file",
        default=None,
        help="the media file with which these markers are "
        "associated. Required for CUE output, ignored "
        "for others.",
    )
    namespace = parser.parse_args()
    out_type = determine_type(namespace.out_file)
    if (
        out_type == MCS.CUE or out_type == MCS.FFMETADATA1
    ) and namespace.media_file is None:
        raise ValueError(
            "You must pass --media-file when converting to CUE or FFMETADATA1."
        )
    mcs = MCS(media_filename=namespace.media_file)
    mcs.load(namespace.in_file)
    mcs.save(namespace.out_file, out_type)


if __name__ == "__main__":
    main(sys.argv)
