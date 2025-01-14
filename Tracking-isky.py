import requests
import json
from urllib.parse import quote
from datetime import datetime, timedelta
import random
import zipcodes

def get_tracking_data(zipcode):
    url = "https://api.iskytracking.com/v2/tracking"
    headers = {
        'Authorization': 'Bearer WILWW5LLB0FL1X4QUIPP',
        'Content-Type': 'application/json'
    }

    # Lấy tổng số records
    initial_payload = {
        "country": "1",
        "zipcode": zipcode,
        "tracking_type": 1,
        "start": 0,
        "city": 0,
        "date_range": "01/01/2025 - 01/05/2025",
        "ship_or_deliver": "p",
        "limit": 1
    }

    initial_response = requests.post(url, headers=headers, data=json.dumps(initial_payload))
    initial_data = initial_response.json()
    total_records = initial_data.get('total', 0)

    if total_records == 0:
        return None

    # Lấy tất cả records
    payload = {
        "country": "1",
        "zipcode": zipcode,
        "tracking_type": 1,
        "start": 0,
        "city": 0,
        "date_range": "01/01/2025 - 01/05/2025",
        "ship_or_deliver": "p",
        "limit": total_records
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def find_suitable_record(tracking_data, min_days_diff=3):
    if 'data' not in tracking_data:
        return None

    max_time_diff = 0
    selected_item = None

    for item in tracking_data['data']:
        if item['status'].strip() == "Delivered":
            packed_time = datetime.strptime(item['packed_at'], "%Y-%m-%d %H:%M:%S")
            delivery_time = datetime.strptime(item['scheduled_delivery'], "%Y-%m-%d %H:%M:%S")
            time_diff = (delivery_time - packed_time).total_seconds()
            days_diff = time_diff / (24 * 3600)
            
            if days_diff >= min_days_diff and time_diff > max_time_diff:
                max_time_diff = time_diff
                selected_item = item

    return selected_item, max_time_diff if selected_item else (None, 0)

# Lấy tất cả zipcode của US
all_zipcodes = [z['zip_code'] for z in zipcodes.list_all()]
used_zipcodes = set()  # Theo dõi các zipcode đã thử

while len(used_zipcodes) < len(all_zipcodes):
    # Chọn zipcode chưa được sử dụng
    available_zipcodes = [z for z in all_zipcodes if z not in used_zipcodes]
    random_zipcode = random.choice(available_zipcodes)
    used_zipcodes.add(random_zipcode)
    
    print(f"Trying zipcode: {random_zipcode} ({len(used_zipcodes)}/{len(all_zipcodes)})")
    
    # Lấy dữ liệu tracking
    tracking_data = get_tracking_data(random_zipcode)
    if not tracking_data:
        print(f"No data found for zipcode {random_zipcode}")
        continue

    # Tìm record phù hợp
    selected_item, max_time_diff = find_suitable_record(tracking_data)
    
    if selected_item:
        # Giải mã tracking number và lưu kết quả
        decode_url = "https://api.iskytracking.com/v2/tracking/ups"
        headers = {
            'Authorization': 'Bearer WILWW5LLB0FL1X4QUIPP',
            'Content-Type': 'application/json'
        }

        try:
            encrypted_tracking = selected_item['tracking_number']
            encoded_tracking = quote(encrypted_tracking) + "___1"
            
            data = {
                "tracking_number": encoded_tracking
            }
            
            decode_response = requests.post(decode_url, headers=headers, data=json.dumps(data))
            decoded_data = decode_response.json()
            
            output = {
                "tracking_number": decoded_data.get('rs', 'N/A'),
                "status": selected_item['status'],
                "packed_at": selected_item['packed_at'],
                "scheduled_delivery": selected_item['scheduled_delivery'],
                "tracking_type": selected_item['tracking_type'],
                "days_difference": round(max_time_diff / (24 * 3600), 2),
                "zipcode": random_zipcode
            }
            
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(json.dumps(output, indent=2))
            print(f"Found suitable record in zipcode {random_zipcode}")
            print(f"Days difference: {output['days_difference']}")
            break
            
        except Exception as e:
            print(f"Error processing tracking: {e}")
            continue
    else:
        print(f"No suitable records found for zipcode {random_zipcode}")

if len(used_zipcodes) == len(all_zipcodes):
    print("Tried all zipcodes but found no suitable data")
        
