import os
import re
import pandas as pd
import requests
import openai
from django.conf import settings
import time
import logging

logger = logging.getLogger(__name__)

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

api_keys_string = os.getenv("API_KEYS", "")
api_keys = api_keys_string.split(',') if api_keys_string else []

prompt_path = os.path.join(settings.BASE_DIR, 'extraR', 'prompt.txt')
with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt = file.read()

# dummy
def update_descriptions(csv_path, api_key, images_folder_path, session, prompt):
    df = pd.read_csv(csv_path)
    # Initialize variables for failed lots and rate limit status
    failed_lots = []
    rate_limit_reached = False
    df['Description'] = df['Description'].astype(str)

    # Simulate updating descriptions for each row
    for index, row in df.iterrows():
        # Simulating progress
        progress = (index + 1) / len(df) * 100

        # Mocking description update
        df.at[index, 'Description'] = f"Description for Lot {row['Lot number']} using secret api_key"

        # Simulate a delay to mimic network request
        time.sleep(1)

    # Mocking a final CSV update
    df['total_tokens'] = 800  # Dummy value for total tokens
    df.to_csv(csv_path, index=False)

    # Yield the final state
    return df, failed_lots, rate_limit_reached

def generate_descriptions(csv_path, images_folder_path):
    logger.info("Starting description generation")

    try:
        df = pd.read_csv(csv_path)
        with requests.Session() as session:
            openai.requestssession = session
            for api_key in api_keys:
                df, failed_lots, rate_limit_reached = update_descriptions(csv_path, api_key, images_folder_path, session, prompt)
                if not df['Description'].isna().any() and not (df['Description'] == '').any():
                    return True
                if not rate_limit_reached:
                    break
            openai.requestssession = None
        if df['Description'].isna().any() or (df['Description'] == '').any():
            logger.error("Not all descriptions updated. Missing descriptions remain.")
            return False
        else:
            return True
    except Exception as e:
        logger.exception(f"Error in generate_descriptions: {e}")
        return False
