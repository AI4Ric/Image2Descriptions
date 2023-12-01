import os
import re
import pandas as pd

def create_dataframe(file_paths):
    # Initialize lists to store the data
    lot_numbers = []
    vendor_numbers = []

    # Iterate through the file paths and extract the lot number
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        if file_name.lower().endswith('.jpg') and re.match(r"^\d+_\d+_.+\.jpg$", file_name):
            parts = file_name.split('_')
            lot_number, vendor_number = parts[0], parts[1]
            lot_numbers.append(int(lot_number))
            vendor_numbers.append(vendor_number)

    # Check if any valid files were processed
    if not lot_numbers:
        return "No valid files were processed."

    # Create a DataFrame
    data = {
        'Lot number': lot_numbers,
        'Vendor number': vendor_numbers,
        'Description': [''] * len(lot_numbers),
        'Reserve': [''] * len(lot_numbers),
        'Low estimate': [0] * len(lot_numbers),
        'High estimate': [0] * len(lot_numbers),
        'Starting bid': [1] * len(lot_numbers)
        # ... other fields ...
    }

    df = pd.DataFrame(data)
    df = df.sort_values(by='Lot number', ascending=True)
    df = df.reset_index(drop=True)

    return df