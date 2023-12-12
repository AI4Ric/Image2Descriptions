import os
import re
import pandas as pd
import requests
import openai
from django.conf import settings
import time
import logging
import base64

logger = logging.getLogger(__name__)

def create_dataframe(file_paths):

    # Initialize lists to store the data
    lot_numbers = []
    vendor_numbers = []
    file_names = []

    # Iterate through the file paths and extract the lot number
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        if file_name.lower().endswith('.jpg') and re.match(r"^\d+_\d+_.+\.jpg$", file_name):
            parts = file_name.split('_')
            lot_number, vendor_number = parts[0], parts[1]
            lot_numbers.append(int(lot_number))
            vendor_numbers.append("C" + vendor_number)
            file_names.append(file_name)


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
        'Starting bid': [1] * len(lot_numbers),
        'ImageName': file_names
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

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def parse_wait_time(error_message):
    match = re.search(r"Please try again in ([\d.]+)s", error_message)
    wait_time = float(match.group(1)) if match else 5
    logger.info(f"Parsed wait time: {wait_time} seconds for message: {error_message}")
    return wait_time

def update_descriptions(csv_path, api_key, images_folder_path, session, prompt, progress_callback=None):
    df = pd.read_csv(csv_path)
    logger.info(f"Type of df at start of update_descriptions: {type(df)}")
    df['Description'] = df['Description'].astype('object')
    failed_lots = []
    rate_limit_reached = False
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    total_rows = len(df)
    consecutive_failures = 0
    max_consecutive_failures = 3
    for index, row in df.iterrows():
        if pd.isna(row['Description']) or row['Description'] == '':
            try_again = True
            attempts = 0
            

            while try_again and attempts < 3:
                try:
                    original_image_name = row['ImageName']
                    original_image_path = os.path.join(images_folder_path, original_image_name)

                    image_name = f"{row['Lot number']}.JPG"
                    image_path = os.path.join(images_folder_path, image_name)

                    if os.path.exists(original_image_path):
                        os.rename(original_image_path, image_path)
                    elif not os.path.exists(image_path):
                        logger.error(f"Image file not found for Lot {row['Lot number']}")
                        continue

                    # Import image
                    base64_image = encode_image(image_path)
                    # Initialize the message
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high",
                                    }
                                }
                            ]
                        }
                    ]
                    # Construct payload
                    payload = {
                        "model": "gpt-4-vision-preview",
                        "messages": messages,
                        "max_tokens": 800
                    }

                    # Get GPT4 response
                    response = session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                    response_json = response.json()
                    if response_json.get('error'):
                        raise requests.exceptions.RequestException(f"Server error: {response_json['error']}")
                    usage = response_json['usage']
                    choice = response_json['choices'][0] if 'choices' in response_json and response_json['choices'] else None
                    if not choice:
                        raise ValueError("No valid choices found in response.")
                    message = choice['message']['content']
                    df.at[index, 'Description'] = message
                    df.at[index, 'total_tokens'] = usage['total_tokens']
                    print(f"Updated Lot {row['Lot number']} with new description.")
                    try_again = False
                    df.to_csv(csv_path, index=False)
                    if progress_callback:
                        progress_callback(index + 1, total_rows)

                except requests.exceptions.HTTPError as http_err:
                    logger.error(f"HTTP error occurred: {http_err}")
                    if http_err.response.status_code == 429:
                        error_content = http_err.response.json()
                        print(f"Rate Limit Error Response: {error_content}")

                        error_message = error_content.get("error", {}).get("message", "")
                        if "RPD" in error_message:
                            rate_limit_reached = True
                            print("Daily request limit reached. Exiting script. Please try again later.")
                            return df, rate_limit_reached

                        wait_time = parse_wait_time(error_message)
                        logger.info(f"Received rate limit error message: {error_message}")
                        print(f"Rate limit reached. Waiting {wait_time} seconds to retry...")
                        time.sleep(wait_time)

                    attempts += 1

                except requests.exceptions.RequestException as req_err:
                    logger.error(f"Request error occurred: {req_err}")
                    attempts += 1

                except Exception as e:
                    logger.exception(f"An error occurred for Lot {row.get('Lot number', 'Unknown')}")  # Logs the error with traceback
                    failed_lots.append(row.get('Lot number', 'Unknown'))
                    break
                finally:
                    df.to_csv(csv_path, index=False)

            if attempts >= 3:
                logger.info(f"Max retries reached for Lot {row.get('Lot number', 'Unknown')}. Moving to next lot.")
                failed_lots.append(row['Lot number'])
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Maximum consecutive failures reached. Stopping the process.")
                    break
            else:
                consecutive_failures = 0

    logger.info(f"Type of df at end of update_descriptions: {type(df)}")
    return df, rate_limit_reached

def generate_descriptions(csv_path, images_folder_path, progress_callback=None):
    logger.info("Starting description generation")

    try:
        df = pd.read_csv(csv_path)
        with requests.Session() as session:
            openai.requestssession = session
            for api_key in api_keys:
                df, rate_limit_reached = update_descriptions(csv_path, api_key, images_folder_path, session, prompt, progress_callback)
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


