
"""
Contains common routines for interacting with Excel files.
"""

from openpyxl.utils import column_index_from_string

def column_name_to_index(name):
    """Convert an Excel column name into a 0-based index."""
    return column_index_from_string(name) - 1

def rgb2hex(colour):
    """Convert an RGB tuple to a string hex colour code."""
    return '{:02x}{:02x}{:02x}'.format(*colour)


def hex2rgb(colour):
    """Convert an RGB hex string to a tuple."""
    def hex2int(offset):
        """Convert the hex to an int"""
        return int(colour[offset:offset + 2], 16)
    return (hex2int(0), hex2int(2), hex2int(4))
