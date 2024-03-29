#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple script to write profile data to human-readable file."""
import os
import pstats

INPUT_FILE = os.environ.get(
    'PROFILE_INPUT_FILE',
    default=os.path.join('..', 'BookingBot-data', 'profile-data.bin')
)
OUTPUT_FILE = os.environ.get(
    'PROFILE_OUTPUT_FILE',
    default=os.path.join('..', 'BookingBot-data', 'profile-data.txt')
)


def main() -> None:
    """Execute script."""
    with open(OUTPUT_FILE, 'w') as stream:
        p = pstats.Stats(INPUT_FILE, stream=stream)
        p.sort_stats('cumtime')
        p.print_stats()


if __name__ == '__main__':
    main()
