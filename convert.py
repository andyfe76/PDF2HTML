import io
import time
import json
import base64
import requests
import os

from lxml import etree, html
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload

import logging
logging.basicConfig(level=logging.ERROR)



def replace_images_with_base64(content):
    '''
    Replace all image URLs in an HTML string with base64-encoded data URLs
    '''
    tree = html.fromstring(content)

    # Find all img elements in the tree
    images = tree.xpath('//img')

    for image in images:
        # Get the src attribute of the image
        src = image.get('src')

        # Download the image data
        try:
            response = requests.get(src)
        except Exception as e:
            print('Error downloading image', e)
            continue

        # Check if the response is successful (HTTP status code 200)
        if response.status_code == 200:
            # Get the image's content type (e.g. 'image/png')
            content_type = response.headers['Content-Type']

            # Convert the image data to base64
            img_base64 = base64.b64encode(response.content).decode()

            # Create a new src attribute with the base64 data
            new_src = f"data:{content_type};base64,{img_base64}"

            # Replace the old src attribute with the new one
            image.set('src', new_src)

    # Convert the modified tree back to an HTML string
    return etree.tostring(tree, pretty_print=True).decode()

def toHTML(driveAPI, pdf_file_path):
    '''
    Convert a PDF file to an HTML string using the Google Drive API
    '''

    file_name = os.path.basename(pdf_file_path)
    file_metadata = {
        'name': file_name,
        # Convert the file to Google Docs format
        'mimeType': 'application/vnd.google-apps.document',
        # Upload the file to folder
        # 'parents': [drive_folder_id]
    }

    # Upload the PDF file to Google Drive
    retry_count = 0
    while True:
        try:
            media = MediaFileUpload(pdf_file_path, mimetype='application/pdf', resumable=True)
            break
        except Exception as e:
            logging.error(f"GDrive media err: {e}")
            retry_count += 1
            if retry_count >= 5:
                return f"MediaFileUpload: {e}"
            time.sleep(2)
            
    
    # Create the file to Google Drive - this will convert the PDF to Google Docs format
    retry_count = 0
    file = None
    while True:
        try:
            file = driveAPI.files().create(body=file_metadata, media_body=media, fields='id').execute()
            break
        except Exception as e:
            retry_count += 1
            logging.error(f"GDrive file err: {e}, retry: {retry_count}")
            if retry_count >= 5:
                return f"driveAPI.files().create: {e}"
            time.sleep(2)
        
    if not file: return 'No file'
    fileID = file.get("id")

    # Export the Google Docs file to HTML
    try:
        export_req = driveAPI.files().export_media(fileId=fileID, mimeType='text/html')
    except Exception as e:
        logging.error(f"GDrive export_req err: {e}")
        return f"driveAPI.files().export_media: {e}"

    # Download the exported file
    try:
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, export_req)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            #print("Download %d%%." % int(status.progress() * 100))

        content_bytes = fh.getvalue()
        content_str = content_bytes.decode('utf-8')
    except Exception as e:
        logging.error(f"GDrive download err: {e}")
        return f"MediaIoBaseDownload: {e}"

    # Replace image URLs with base64-encoded data URLs
    try:
        content_str = replace_images_with_base64(content_str)
    except Exception as e:
        logging.error(f"replace_images_with_base64 err: {e}")
    
    #delete the file from drive
    try:
        driveAPI.files().delete(fileId=fileID).execute()
    except Exception as e:
        logging.error(f"GDrive delete err: {e}")
    
    return content_str


def convert(pdf_file_path: str, credentials_path: str = "credentials.json", token_path: str = "token.json"):
    if not os.path.exists(credentials_path):
        return 'Google Drive not configured'

    token_path = "token.json"
    if not os.path.exists(token_path):
        return 'Google Drive not authorized'

    creds = None
    try:
        creds = Credentials.from_authorized_user_info(json.load(open(token_path)))
    except Exception as e:
        return 'Google Auth failed: ' + str(e)

    if not creds:
        return 'Google Drive authorization failed'

    if creds.expired:
        try:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            creds = Credentials.from_authorized_user_info(json.load(open(token_path)))
        except Exception as e:
            return 'Google Drive refresh token failed: ' + str(e)
        
    try:
        driveAPI = build('drive', 'v3', credentials=creds)
    except Exception as e:
        return 'Google Drive API failed: ' + str(e)

    # Convert the PDF to HTML
    try:
        res = toHTML(driveAPI, pdf_file_path)
        return res
    except Exception as e:
        return 'Google Drive API failed: ' + str(e)


    
