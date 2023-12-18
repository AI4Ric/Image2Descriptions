import os
import re
import pandas as pd
import requests
import openai
from django.conf import settings
import time
import logging
import base64
from urllib.parse import urlparse
from django.core.files.storage import default_storage
from io import StringIO
import posixpath
from django.core.files.base import ContentFile
from io import BytesIO


logger = logging.getLogger(__name__)

def create_dataframe(file_urls, include_vendor_no=False, include_category=False):
    # Initialize a list to store the data
    data = []

    # Define default values for Vendor No and Category
    default_vendor_no = 'C99999'
    default_category = 'No Category'

    # Iterate through the file paths and extract the Lot No
    for file_url in file_urls:
        parsed_url = urlparse(file_url)
        file_name = os.path.basename(parsed_url.path)
        name, extension = os.path.splitext(file_name)

        if extension.lower() == '.jpg':
            parts = name.split('_')

            lot_no = parts[0] if parts[0].isdigit() else None

            if lot_no is None:
                continue

            # Conditional extraction based on the checkboxes and the number of parts
            if include_vendor_no and len(parts) > 1:
                vendor_no = 'C' + parts[1]
            else:
                vendor_no = default_vendor_no

            if include_category and len(parts) > (2 if include_vendor_no else 1):
                # If vendor number is not included, category would be in parts[1]
                category_index = 2 if include_vendor_no else 1
                category = parts[category_index]
            else:
                category = default_category

            data.append((lot_no, vendor_no, category, '', '', 0, 0, 1, file_name))

    if not data:
        return "No valid files were processed."
    
    df = pd.DataFrame(data, columns=[
        'Lot No', 
        'Vendor', 
        'Category', 
        'Description', 
        'Reserve', 
        'Low estimate', 
        'High estimate', 
        'Starting bid', 
        'ImageName'
    ])

    df = df.sort_values(by='Lot No', ascending=True)
    df = df.reset_index(drop=True)

    return df

api_keys_string = os.getenv("API_KEYS", "")
api_keys = api_keys_string.split(',') if api_keys_string else []

prompt_path = os.path.join(settings.BASE_DIR, 'extraR', 'prompt.txt')
with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt = file.read()

# Function to encode the image
def encode_image(image_key):
    if default_storage.exists(image_key):
        with default_storage.open(image_key, "rb") as image_file:
            # Read the image file in a buffer
            buffer = BytesIO(image_file.read())
            # Encode the buffer content in base64
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return base64_image
    else:
        # Handle the case where the image file does not exist
        return None 
    
def parse_wait_time(error_message):
    match = re.search(r"Please try again in ([\d.]+)s", error_message)
    wait_time = float(match.group(1)) if match else 5
    logger.info(f"Parsed wait time: {wait_time} seconds for message: {error_message}")
    return wait_time

def update_descriptions(csv_file_key, api_key, images_folder_path, session, prompt, progress_callback=None):
    if default_storage.exists(csv_file_key):
        with default_storage.open(csv_file_key, 'r') as csv_file:
            csv_content = csv_file.read()
            df = pd.read_csv(StringIO(csv_content))
    #df = pd.read_csv(csv_path)
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
                    original_image_key = posixpath.join(images_folder_path, original_image_name)

                    image_name = f"{row['Lot No']}.JPG"
                    image_key = posixpath.join(images_folder_path, image_name)
                    logger.info(f"Trying to access original image at: {original_image_key}")
                    logger.info(f"Trying to access/rename image at: {image_key}")

                    #if default_storage.exists(original_image_key):
                    #    default_storage.save(image_key, default_storage.open(original_image_key))
                    #    default_storage.delete(original_image_key)
                    #elif not default_storage.exists(image_key):
                    #    logger.error(f"Image file not found for Lot {row['Lot No']}")
                    #    continue

                    # Import image
                    base64_image = encode_image(image_key)
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
                    print(f"Updated Lot {row['Lot No']} with new description.")
                    try_again = False

                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_buffer.seek(0)  # Rewind the buffer to the beginning

                    # Save the buffer content to S3
                    default_storage.save(csv_file_key, ContentFile(csv_buffer.read()))
                    if progress_callback:
                        progress_callback(index + 1, total_rows)

                except requests.exceptions.HTTPError as http_err:
                    logger.error(f"HTTP error occurred: {http_err}")
                    if http_err.response.status_code == 429:
                        error_content = http_err.response.json()
                        print(f"Rate Limit Error Response: {error_content}")

                        error_message = error_content.get("error", {}).get("message", "")
                        if "RPD" in error_message or "insufficient_quota" in error_content.get("error", {}).get("type", ""):
                            rate_limit_reached = True
                            logger.info(f"Daily limit or insufficient quota reached. Switching API key. Error: {error_message}")
                            return df, rate_limit_reached
                        elif "RPM" in error_message or "TPM" in error_message:
                            wait_time = parse_wait_time(error_message)
                            logger.info(f"Per minute limit reached. Waiting {wait_time} seconds to retry... Error: {error_message}")
                            time.sleep(wait_time)
                        else:
                            logger.error("Encountered an HTTP 429 error without a recognized rate limit message.")
                        attempts += 1
                    else:
                        logger.error(f"HTTP error occurred: {http_err}")
                        attempts += 1

                except requests.exceptions.RequestException as req_err:
                    logger.error(f"Request error occurred: {req_err}")
                    attempts += 1

                except Exception as e:
                    logger.exception(f"An error occurred for Lot {row.get('Lot No', 'Unknown')}")  # Logs the error with traceback
                    failed_lots.append(row.get('Lot No', 'Unknown'))
                    break
                finally:
                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_buffer.seek(0)  # Rewind the buffer to the beginning

                    # Save the buffer content to S3
                    default_storage.save(csv_file_key, ContentFile(csv_buffer.read()))

            if attempts >= 3:
                logger.info(f"Max retries reached for Lot {row.get('Lot No', 'Unknown')}. Moving to next lot.")
                failed_lots.append(row['Lot No'])
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Maximum consecutive failures reached. Stopping the process.")
                    break
            else:
                consecutive_failures = 0

    logger.info(f"Type of df at end of update_descriptions: {type(df)}")
    return df, rate_limit_reached

def generate_descriptions(csv_file_key, images_folder_path, progress_callback=None):
    logger.info("Starting description generation")

    try:
        if default_storage.exists(csv_file_key):
            with default_storage.open(csv_file_key, 'r') as csv_file:
                csv_content = csv_file.read()
                df = pd.read_csv(StringIO(csv_content))

            with requests.Session() as session:
                openai.requestssession = session
                for api_key in api_keys:
                    df, rate_limit_reached = update_descriptions(csv_file_key, api_key, images_folder_path, session, prompt, progress_callback)
                    if rate_limit_reached:
                        logger.info(f"Rate limit reached for key. Switching to next key.")
                        continue
                    if not df['Description'].isna().any() and not (df['Description'] == '').any():
                        return True
                openai.requestssession = None
            if df['Description'].isna().any() or (df['Description'] == '').any():
                logger.error("Not all descriptions updated. Missing descriptions remain.")
                return False
            else:
                return True
        else:
            logger.error(f"CSV file not found at key: {csv_file_key}")
            return False
        
    except Exception as e:
        logger.exception(f"Error in generate_descriptions: {e}")
        return False


