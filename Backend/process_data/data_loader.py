# process_data/data_loader.py
"""
Module to handle loading of Quran data from JSON file.
"""

import json

def load_quran_data(filepath):
    """
    Load and parse JSON file containing Quran data.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        list: Parsed JSON data.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)
    
def load_hadith_data(filepath):
    """
    Load and parse JSON file containing Hadith data.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        list: Parsed JSON data.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


