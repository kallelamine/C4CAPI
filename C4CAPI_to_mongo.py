import os
import json
import requests
import time
from datetime import datetime, timedelta
import pickle
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Convert /Date(...) format to a readable datetime string
def convert_to_readable_date(date_string):
    try:
        timestamp = int(date_string[6:-2])
        readable_date = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
        return readable_date
    except Exception as e:
        print(f"Error converting date: {e}")
        return "NONE"

# Extract fields and convert date formats
def extract_fields_with_time(contact_info):
    extracted_data = []
    for result in contact_info['d']['results']:
        created_date = convert_to_readable_date(result.get('CreationDateTime', 'NONE'))
        reported_date = convert_to_readable_date(result.get('RequestInitialReceiptdatetimecontent', 'NONE'))
        due_completion = convert_to_readable_date(result.get('CompleteDuedatetimeContent', 'NONE'))
        open_date = convert_to_readable_date(result.get('RequestInProcessdatetimeContent', 'NONE'))
        close_date = convert_to_readable_date(result.get('RequestCloseddatetimeContent', 'NONE'))
        
        priority = result.get('ServicePriorityCodeText', 'NONE')
        type_ = result.get('ProcessingTypeCodeText', 'NONE')
        id_ = result.get('ID', 'NONE')
        subject = result.get('Name', 'NONE')
        status = result.get('ServiceRequestUserLifeCycleStatusCodeText', 'NONE')
        contact = result.get('BuyerMainContactPartyName', 'NONE')
        client = result.get('BuyerPartyName', 'NONE')
        escalated = result.get('EscalationStatusCodeText', 'NONE')
        channel = result.get('DataOriginTypeCodeText', 'NONE')
        channel_1 = result.get('ZChannel2_KUTText', 'NONE')
        channel_2 = result.get('ZChannel2_KUT', 'NONE')
        created_by = result.get('createdby', 'NONE')
        assigned_to = result.get('ProcessorPartyID', 'NONE')
        team = result.get('ServiceSupportTeamPartyName', 'NONE')
        sector_service = result.get('ServiceTermsServiceIssueName', 'NONE')
        department = result.get('IncidentCategoryName', 'NONE')
        primary_classification = result.get('ObjectServiceIssueCategoryID', 'NONE')
        secondary_classification = result.get('CauseServiceIssueCategoryID', 'NONE')
        service_level_id = result.get('ServiceLevelObjectiveID', 'NONE')
        source = result.get('DataOriginTypeCodeText', 'NONE')
        
        extracted_data.append([priority, type_, id_, subject, status, contact, client, escalated, channel,
                               channel_1, channel_2, created_date, reported_date, due_completion, created_by, assigned_to,
                               team, sector_service, department, primary_classification, secondary_classification,
                               service_level_id, open_date, close_date, source])
    return extracted_data

# Connect to MongoDB
def connect_to_mongodb():
    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    client = MongoClient(uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("Connected to MongoDB.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return None
    return client


# Insert data into MongoDB
def insert_into_mongodb(db_name, collection_name, data):
    client = connect_to_mongodb()
    if client:
        db = client[db_name]
        collection = db[collection_name]
        try:
            collection.insert_many(data)
            print(f"Inserted {len(data)} documents into MongoDB.")
        except Exception as e:
            print(f"Failed to insert data into MongoDB: {e}")

# Get access token from API
def get_access_token():
    load_dotenv()
    url = os.getenv("OAUTH_URL")
    client_id = os.getenv("OAUTH_CLIENT_ID")
    client_secret = os.getenv("OAUTH_CLIENT_SECRET")
    
    payload = {'grant_type': 'client_credentials'}
    headers = {'X-CSRF-Token': 'Fetch'}
    auth = (client_id, client_secret)
    
    response = requests.post(url, headers=headers, data=payload, auth=auth)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print("Failed to get access token:", response.text)
        return None


# Get contact information from the API
def get_contact_info(access_token):
    load_dotenv()
    current_time = datetime.utcnow()
    time_minus_5_minutes = current_time - timedelta(minutes=2)
    formatted_time = time_minus_5_minutes.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    
    url = os.getenv("CONTACT_INFO_URL") + f"?$format=json&$filter=LastChangeDateTime ge datetimeoffset'{formatted_time}'"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'x-csrf-token': os.getenv("CSRF_TOKEN")
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as e:
            print("Failed to decode JSON:", e)
            return None
    else:
        print(f"Failed to retrieve contact info. Status Code: {response.status_code}")
        return None


# Main loop
if __name__ == "__main__":
    while True:
        token = get_access_token()
        if token:
            contact_info = get_contact_info(token)
            if contact_info:
                extracted_data = extract_fields_with_time(contact_info)
                
                # MongoDB insertion
                mongo_data = []
                for row in extracted_data:
                    mongo_data.append({
                        'أفضلية': row[0], 'النوع': row[1], 'المعرف': row[2], 'الموضوع': row[3], 'الحالة': row[4],
                        'جهة الاتصال': row[5], 'العميل': row[6], 'مصعَّد': row[7], 'القناة': row[8],
                        'القناة1': row[9], 'القناة 2': row[10], 'تاريخ الإنشاء': row[11], 'تاريخ الإبلاغ': row[12],
                        'استحقاق الاكتمال': row[13], 'المنشئ': row[14], 'معيّن إلى': row[15], 'الفريق': row[16],
                        'القطاع \\ الخدمة': row[17], 'الإدارة': row[18], 'التصنيف الأساسي': row[19],
                        'التصنيف الفرعي': row[20], 'معرف مستوى الخدمة': row[21], 'تاريخ فتح البلاغ': row[22],
                        'تاريخ إغلاق البلاغ': row[23], 'Source': row[24], 'timestamp': datetime.now()
                    })
                insert_into_mongodb('mim_c4c', 'service final', mongo_data)
        
        time.sleep(120)
