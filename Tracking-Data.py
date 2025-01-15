import requests
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from iso3166 import countries
import pandas as pd
from tkinter import filedialog
import os
import threading
import json
import zipcodes
import random
import requests
import json
from datetime import datetime, timedelta

# Global variable to store used zipcodes during the session
USED_ZIPCODES = set()

def convert_excel_date(excel_date):
    try:
        print(f"Converting date: {excel_date}, type: {type(excel_date)}")  # Debug log
        
        # Kiểm tra giá trị rỗng
        if not excel_date or str(excel_date).strip() == '':
            print("Empty date value")
            return None
            
        # Nếu là số, chuyển về datetime
        if isinstance(excel_date, (int, float)) or (isinstance(excel_date, str) and excel_date.replace('.', '').isdigit()):
            # Chuyển về số nguyên nếu là số thập phân
            excel_num = int(float(excel_date))
            # Excel bắt đầu từ 1/1/1900 và có lỗi năm 1900
            base_date = datetime(1900, 1, 1)
            date = base_date + timedelta(days=excel_num - 2)
            result = date.strftime('%m/%d/%Y')
            print(f"Converted {excel_date} to {result}")  # Debug log
            return result
            
        # Nếu đã là định dạng ngày, giữ nguyên
        print(f"Keeping original date format: {excel_date}")  # Debug log
        return excel_date
        
    except Exception as e:
        print(f"Error converting date: {str(e)}, value: {excel_date}")  # Debug log
        return None

def get_isky_tracking(country, city, purchase_date):
    global USED_ZIPCODES
    url = "https://api.iskytracking.com/v2/tracking"
    decode_url = "https://api.iskytracking.com/v2/tracking/ups"
    headers = {
        'Authorization': 'Bearer WILWW5LLB0FL1X4QUIPP',
        'Content-Type': 'application/json'
    }

    # Kiểm tra purchase_date
    if not purchase_date or str(purchase_date).strip() == '':
        print("Purchase date is empty")
        return None

    # Chuyển đổi purchase_date nếu cần
    formatted_date = convert_excel_date(purchase_date)
    if not formatted_date:
        print(f"Invalid purchase date: {purchase_date}")  # Debug log
        return None

    # Tính toán date range
    try:
        print(f"Calculating date range from: {formatted_date}")  # Debug log
        base_date = datetime.strptime(formatted_date, '%m/%d/%Y')
        start_date = base_date + timedelta(days=1)
        end_date = base_date + timedelta(days=5)
        date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
        print("date_range", date_range)  # Debug log
    except Exception as e:
        print(f"Error calculating date range: {str(e)}, formatted_date: {formatted_date}")  # Debug log
        return None

    # Get all available zipcodes excluding used ones
    all_zipcodes = set(z['zip_code'] for z in zipcodes.list_all()) - USED_ZIPCODES
    if city:
        city_zipcodes = set(z['zip_code'] for z in zipcodes.filter_by(city=city.upper())) - USED_ZIPCODES
        available_zipcodes = list(city_zipcodes if city_zipcodes else all_zipcodes)
    else:
        available_zipcodes = list(all_zipcodes)

    if not available_zipcodes:
        print("No unused zipcodes available")
        return None

    # Try all remaining zipcodes until we get valid data
    attempts = 0
    total_zipcodes = len(available_zipcodes)
    
    while available_zipcodes:
        attempts += 1
        current_zipcode = available_zipcodes.pop()
        USED_ZIPCODES.add(current_zipcode)

        try:
            print(f"Trying zipcode {current_zipcode} (Attempt {attempts}/{total_zipcodes})")
            
            # Initial request to get total records
            initial_payload = {
                "country": "1",  # 1 for US
                "zipcode": current_zipcode,
                "tracking_type": 1,
                "start": 0,
                "city": 0,
                "date_range": date_range,   # Sử dụng date_range đã tính
                "ship_or_deliver": "p",
                "limit": 1
            }

            initial_response = requests.post(url, headers=headers, data=json.dumps(initial_payload))
            initial_data = initial_response.json()
            total_records = initial_data.get('total', 0)

            if total_records == 0:
                print(f"No records found for zipcode {current_zipcode}")
                continue

            # Get all records
            payload = {**initial_payload, "limit": total_records}
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            tracking_data = response.json()

            # Find suitable record
            selected_item, max_time_diff = find_suitable_record(tracking_data)
            
            if selected_item:
                # Decode tracking number
                decode_data = {
                    "tracking_number": selected_item['tracking_number']
                }
                decode_response = requests.post(decode_url, headers=headers, data=json.dumps(decode_data))
                decoded_data = decode_response.json()

                # Check if we got a valid tracking number
                if decoded_data.get('rs') and decoded_data.get('rs') != 'N/A':
                    output = {
                        "carrier": selected_item['tracking_type'],
                        "tracking_number": decoded_data.get('rs'),
                        "status": selected_item['status'],
                        "ship_datetime": selected_item['packed_at'],
                        "delivery_datetime": selected_item['scheduled_delivery'],
                        "duration": round(max_time_diff / (24 * 3600), 2),
                        "zipcode": current_zipcode
                    }
                    print(f"Success with zipcode {current_zipcode} on attempt {attempts}")
                    return output
                else:
                    print(f"Invalid tracking number for zipcode {current_zipcode}")

        except Exception as e:
            print(f"Error with zipcode {current_zipcode}: {str(e)}")
            continue

    print(f"Failed to find valid tracking data after trying all {total_zipcodes} remaining zipcodes")
    return None

def calculate_duration(packed_at, scheduled_delivery):
    try:
        if packed_at and scheduled_delivery:
            ship_date = datetime.fromisoformat(packed_at.replace('Z', '+00:00'))
            delivery_date = datetime.fromisoformat(scheduled_delivery.replace('Z', '+00:00'))
            return (delivery_date - ship_date).days
        return 0
    except:
        return 0

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

def get_tracking_data(api_key, country, date_from, date_to, city):
    # For United States, use isky tracking
    if country.lower() in ["united states", "us", "usa"]:
        try:
            # Get tracking data from isky
            tracking_data = get_isky_tracking(country, city, date_from)
            if tracking_data:
                return (
                    f"Carrier: {tracking_data['carrier']}\n"
                    f"Tracking Number: {tracking_data['tracking_number']}\n"
                    f"Ship DateTime: {tracking_data['ship_datetime']}\n"
                    f"Delivery DateTime: {tracking_data['delivery_datetime']}\n"
                    f"Status: {tracking_data['status']}\n"
                    f"Duration: {tracking_data['duration']} days\n"
                )
            return "No suitable tracking found for US shipment"

        except Exception as e:
            print(f"Error in isky tracking: {str(e)}")
            return f"Error: {str(e)}"

    else:
        # Existing monkey-tools code for non-US countries
        # ... rest of the existing code ...
        api_key = api_key.strip()
        try:
            if isinstance(date_from, str):
                date_from = pd.to_datetime(date_from).strftime('%Y-%m-%d')
                
            if isinstance(date_to, str):
                date_to = pd.to_datetime(date_to).strftime('%Y-%m-%d')
        except Exception as e:
            return f"Date format error: {str(e)}"

        # Chỉ sử dụng monkey-tools cho non-US
        country_code = get_country_code(country)
        if not country_code:
            return f"Invalid country name: {country}"

        url = "https://monkey-tools.co/api/v2/non-us/tracking-requests"
        payload = {
            "country": country_code,
            "from": date_from,
            "to": date_to,
            "city": city
        }
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                if data.get("success"):
                    if "data" in data and isinstance(data["data"], dict) and "shipments" in data["data"]:
                        shipments = data["data"]["shipments"]
                    elif "data" in data and isinstance(data["data"], list):
                        return "No shipments found for this criteria."
                    else:
                        return "Invalid response format"
                else:
                    return f"API error: {data.get('message', 'Unknown error')}"
            else:
                return "Invalid response format"

            filtered_shipments = []
            for shipment in shipments:
                if isinstance(shipment, dict):
                    status = shipment.get("status")
                    ship_datetime_str = shipment.get("ship_datetime")
                    delivery_datetime_str = shipment.get("delivery_datetime")

                    if status in ["On the way", "Delivered"] and ship_datetime_str and delivery_datetime_str:
                        try:
                            ship_datetime = datetime.fromisoformat(ship_datetime_str.replace('Z', '+00:00'))
                            delivery_datetime = datetime.fromisoformat(delivery_datetime_str.replace('Z', '+00:00'))
                            duration_days = (delivery_datetime - ship_datetime).days

                            if duration_days >= 3:
                                filtered_shipments.append((shipment, duration_days))
                        except ValueError:
                            continue

            if not filtered_shipments:
                return "No shipments meet the criteria (duration >= 3 days)."

            longest_shipment, longest_duration = max(filtered_shipments, key=lambda x: x[1])

            shipment_info = (
                f"Carrier: {longest_shipment.get('carrier', 'N/A')}\n"
                f"Tracking Number: {longest_shipment.get('tracking_number', 'N/A')}\n"
                f"Ship DateTime: {longest_shipment.get('ship_datetime', 'N/A')}\n"
                f"Delivery DateTime: {longest_shipment.get('delivery_datetime', 'N/A')}\n"
                f"Status: {longest_shipment.get('status', 'N/A')}\n"
                f"Duration: {longest_duration} days\n"
            )

            return shipment_info

        except requests.exceptions.RequestException as e:
            return f"Request failed: {str(e)}"
        except Exception as e:
            return f"Error processing data: {str(e)}"

def get_isky_tracking_data(zipcode):
    url = "https://api.iskytracking.com/v2/tracking"
    headers = {
        'Authorization': 'Bearer WILWW5LLB0FL1X4QUIPP',
        'Content-Type': 'application/json'
    }

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

def get_zipcode_from_city(city):
    # You'll need to implement this function to get the zipcode from the city
    # For now, returning a sample zipcode
    return "90001"  # Example zipcode for Los Angeles

def get_country_code(country_name):
    country_name = country_name.strip()
    try:
        # Tìm kiếm chính xác trước
        for country in countries:
            if country_name.lower() == country.name.lower():
                return country.alpha2
                
        # Tìm kiếm một phần nếu không tìm thấy chính xác
        for country in countries:
            if (country_name.lower() in country.name.lower() or
                country_name.lower() == country.alpha2.lower() or
                country_name.lower() == country.alpha3.lower()):
                return country.alpha2
                
        return None
    except Exception as e:
        print(f"Error in get_country_code: {e}")
        return None

def on_submit():
    api_key = api_key_entry.get().strip()
    country_input = country_entry.get().strip()
    date_from = date_from_entry.get().strip()
    date_to = date_to_entry.get().strip()
    city = city_entry.get().strip()

    if not all([api_key, country_input, date_from, date_to, city]):
        messagebox.showerror("Input Error", "All fields are required.")
        return

    # Chuyển đổi tên quốc gia sang mã quốc gia
    country_code = get_country_code(country_input)
    if not country_code:
        messagebox.showerror("Input Error", f"Invalid country name: {country_input}")
        return

    result = get_tracking_data(api_key, country_code, date_from, date_to, city)
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, result)

def process_excel_file(monkey_api_key, isky_api_key):
    # Disable the process button immediately
    for widget in root.winfo_children():
        if isinstance(widget, ttk.Notebook):
            for tab in widget.winfo_children():
                for child in tab.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.configure(state='disabled')
    
    def process_in_thread():
        try:
            # Chọn file Excel
            file_path = filedialog.askopenfilename(
                title="Select Excel File",
                filetypes=[("Excel files", "*.xlsx")]
            )
            
            if not file_path:
                return
            
            # Biến đếm số lượng cập nhật thành công
            success_count = 0
            api_call_count = 0
            us_count = 0  # Thêm biến đếm cho US
            
            # Đọc file Excel với các tham số để giữ nguyên định dạng ngày
            with pd.ExcelWriter(file_path, mode='a', if_sheet_exists='overlay', engine='openpyxl') as writer:
                # Đọc Excel với các tham số để giữ nguyên định dạng ngày
                df = pd.read_excel(
                    file_path,
                    dtype=str,
                    parse_dates=False,
                    engine='openpyxl',
                    keep_default_na=False
                )
                original_columns = df.columns.tolist()
                
                # Tìm các cột cần thiết (không phân biệt hoa thường)
                column_mapping = {
                    'country': next((col for col in df.columns if 'buyer country' in col.lower()), None),
                    'city': next((col for col in df.columns if 'buyer city' in col.lower()), None),
                    'start_date': next((col for col in df.columns if 'start monkey' in col.lower()), None),
                    'end_date': next((col for col in df.columns if 'end monkey' in col.lower()), None),
                    'purchase_date': next((col for col in df.columns if 'ngày khách mua' in col.lower()), None)
                }
                
                # Kiểm tra các cột bắt buộc
                missing_columns = [k for k, v in column_mapping.items() if v is None]
                if missing_columns:
                    messagebox.showerror("Error", f"Missing required columns: {', '.join(missing_columns)}")
                    return
                    
                # Tìm hoặc tạo các cột kết quả với dtype là string
                result_columns = {
                    'tracking': 'TRACKING',
                    'carrier': 'Carrier',
                    'ship_datetime': 'Ship DateTime',
                    'delivery_datetime': 'Delivery DateTime',
                    'status': 'Status'
                }
                
                # Thêm các cột mới với dtype là string
                new_columns = []
                for col in result_columns.values():
                    if col not in df.columns:
                        df[col] = pd.Series(dtype=str)
                        new_columns.append(col)
                
                # Xử lý từng dòng
                for index, row in df.iterrows():
                    # Kiểm tra nếu đã có tracking number thì bỏ qua
                    if (result_columns['tracking'] in df.columns and 
                        pd.notna(df.at[index, result_columns['tracking']]) and 
                        str(df.at[index, result_columns['tracking']]).strip() != ''):
                        print(f"Skipping row {index + 2}: Already has tracking number")
                        continue
                        
                    country_name = str(row[column_mapping['country']]).strip()
                    city = str(row[column_mapping['city']]).strip()
                    date_from = str(row[column_mapping['start_date']]).strip()
                    date_to = str(row[column_mapping['end_date']]).strip()
                    date_mua = str(row[column_mapping['purchase_date']]).strip()
                    date_mua = convert_excel_date(date_mua)
                    print("date_mua", date_mua)
                    
                    # Debug print
                    print(f"Processing row {index + 2}: Country = '{country_name}'")
                    
                    # Bỏ qua nếu thiếu thông tin
                    if (pd.isna(country_name) or pd.isna(city) or 
                        pd.isna(date_from) or pd.isna(date_to)):
                        print(f"Skipping row {index + 2}: Missing data")
                        continue
                    
                    api_call_count += 1
                    
                    # Cải thiện việc kiểm tra United States
                    is_us = any(us_name in country_name.lower() for us_name in ["united states", "us", "usa"])
                    if is_us:
                        us_count += 1
                        print(f"Using iSky API for US shipment at row {index + 2}")
                        result = get_tracking_data(isky_api_key, country_name, date_mua, date_to, city)
                    else:
                        print(f"Using Monkey API for non-US shipment at row {index + 2}")
                        result = get_tracking_data(monkey_api_key, country_name, date_from, date_to, city)
                    
                    print(f"API Response for row {index + 2}: {result}")
                    
                    if isinstance(result, str) and "Carrier:" in result:
                        lines = result.split('\n')
                        updated = False
                        try:
                            for line in lines:
                                if "Carrier:" in line:
                                    df.at[index, result_columns['carrier']] = str(line.split(': ')[1]).strip()
                                    updated = True
                                elif "Tracking Number:" in line:
                                    df.at[index, result_columns['tracking']] = str(line.split(': ')[1]).strip()
                                elif "Ship DateTime:" in line:
                                    df.at[index, result_columns['ship_datetime']] = str(line.split(': ')[1]).strip()
                                elif "Delivery DateTime:" in line:
                                    df.at[index, result_columns['delivery_datetime']] = str(line.split(': ')[1]).strip()
                                elif "Status:" in line:
                                    df.at[index, result_columns['status']] = str(line.split(': ')[1]).strip()
                            if updated:
                                success_count += 1
                                print(f"Successfully updated row {index + 2}")
                        except Exception as e:
                            print(f"Error updating row {index + 2}: {str(e)}")
                    else:
                        print(f"No valid result for row {index + 2}: {result}")
                
                # Sắp xếp lại các cột
                final_columns = [col for col in original_columns if col not in new_columns] + new_columns
                df = df[final_columns]
                
                # Ghi lại vào file Excel
                df.to_excel(writer, index=False, sheet_name=writer.sheets.keys().__iter__().__next__())
                
            # Cập nhật thông báo thành công
            if success_count > 0:
                messagebox.showinfo("Success", 
                    f"Excel file has been updated successfully!\n"
                    f"Total rows processed: {api_call_count}\n"
                    f"US shipments: {us_count}\n"
                    f"Non-US shipments: {api_call_count - us_count}\n"
                    f"Successfully updated: {success_count} tracking numbers")
            else:
                messagebox.showwarning("Warning", 
                    f"No data was updated.\n"
                    f"Total rows processed: {api_call_count}\n"
                    f"US shipments: {us_count}\n"
                    f"Non-US shipments: {api_call_count - us_count}")
            
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
            print(f"Detailed error: {str(e)}")
        finally:
            # Re-enable the process button
            root.after(0, lambda: enable_buttons())
    
    def enable_buttons():
        for widget in root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for tab in widget.winfo_children():
                    for child in tab.winfo_children():
                        if isinstance(child, ttk.Button):
                            child.configure(state='normal')
    
    # Start processing in a separate thread
    thread = threading.Thread(target=process_in_thread)
    thread.daemon = True
    thread.start()

def create_excel_tab(notebook):
    excel_frame = ttk.Frame(notebook, padding="10")
    notebook.add(excel_frame, text="Excel Processing")
    
    # Monkey API Key input
    monkey_api_label = ttk.Label(excel_frame, text="Monkey API-Key:")
    monkey_api_label.grid(row=0, column=0, sticky=tk.W)
    monkey_api_entry = ttk.Entry(excel_frame, width=40)
    monkey_api_entry.grid(row=0, column=1, pady=5)
    
    # iSky API Key input
    isky_api_label = ttk.Label(excel_frame, text="iSky API-Key:")
    isky_api_label.grid(row=1, column=0, sticky=tk.W)
    isky_api_entry = ttk.Entry(excel_frame, width=40)
    isky_api_entry.grid(row=1, column=1, pady=5)
    
    # Process button
    process_button = ttk.Button(
        excel_frame,
        text="Process Excel File",
        command=lambda: process_excel_file(monkey_api_entry.get(), isky_api_entry.get()) 
            if monkey_api_entry.get().strip() and isky_api_entry.get().strip() 
            else messagebox.showerror("Error", "Please enter both API keys")
    )
    process_button.grid(row=2, column=0, columnspan=2, pady=10)
    
    return excel_frame

def create_api_frame(notebook):
    frame = ttk.Frame(notebook, padding="10")
    
    # API Key
    api_key_label = ttk.Label(frame, text="API-Key:")
    api_key_label.grid(row=0, column=0, sticky=tk.W)
    global api_key_entry
    api_key_entry = ttk.Entry(frame, width=40)
    api_key_entry.grid(row=0, column=1, pady=5)
    
    # Country
    country_label = ttk.Label(frame, text="Country Name:")
    country_label.grid(row=1, column=0, sticky=tk.W)
    global country_entry
    country_entry = ttk.Entry(frame, width=40)
    country_entry.grid(row=1, column=1, pady=5)
    
    # Date From
    date_from_label = ttk.Label(frame, text="Date From (YYYY-MM-DD):")
    date_from_label.grid(row=2, column=0, sticky=tk.W)
    global date_from_entry
    date_from_entry = ttk.Entry(frame, width=40)
    date_from_entry.grid(row=2, column=1, pady=5)
    
    # Date To
    date_to_label = ttk.Label(frame, text="Date To (YYYY-MM-DD):")
    date_to_label.grid(row=3, column=0, sticky=tk.W)
    global date_to_entry
    date_to_entry = ttk.Entry(frame, width=40)
    date_to_entry.grid(row=3, column=1, pady=5)
    
    # City
    city_label = ttk.Label(frame, text="City:")
    city_label.grid(row=4, column=0, sticky=tk.W)
    global city_entry
    city_entry = ttk.Entry(frame, width=40)
    city_entry.grid(row=4, column=1, pady=5)
    
    # Submit Button
    submit_button = ttk.Button(frame, text="Submit", command=on_submit)
    submit_button.grid(row=5, column=0, columnspan=2, pady=10)
    
    # Result Text Area
    global result_text
    result_text = tk.Text(frame, height=10, width=50)
    result_text.grid(row=6, column=0, columnspan=2, pady=5)
    
    return frame

def create_isky_tab(notebook):
    isky_frame = ttk.Frame(notebook, padding="10")
    notebook.add(isky_frame, text="iSky Tracking")
    
    # API Key
    api_key_label = ttk.Label(isky_frame, text="iSky API-Key:")
    api_key_label.grid(row=0, column=0, sticky=tk.W)
    api_key_entry = ttk.Entry(isky_frame, width=40)
    api_key_entry.grid(row=0, column=1, columnspan=2, pady=5)
    
    # Purchase Date
    date_label = ttk.Label(isky_frame, text="Purchase Date (MM/DD/YYYY):")
    date_label.grid(row=1, column=0, sticky=tk.W)
    date_entry = ttk.Entry(isky_frame, width=40)
    date_entry.grid(row=1, column=1, columnspan=2, pady=5)
    
    # Zipcode with Random button
    zipcode_label = ttk.Label(isky_frame, text="Zipcode:")
    zipcode_label.grid(row=2, column=0, sticky=tk.W)
    zipcode_entry = ttk.Entry(isky_frame, width=20)
    zipcode_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
    
    def random_zipcode():
        all_zipcodes = [z['zip_code'] for z in zipcodes.list_all()]
        available_zipcodes = list(set(all_zipcodes) - USED_ZIPCODES)
        if available_zipcodes:
            random_zip = random.choice(available_zipcodes)
            zipcode_entry.delete(0, tk.END)
            zipcode_entry.insert(0, random_zip)
    
    random_btn = ttk.Button(isky_frame, text="Random", command=random_zipcode)
    random_btn.grid(row=2, column=2, padx=5, pady=5)
    
    # Result Text Area
    result_text = tk.Text(isky_frame, height=10, width=50)
    result_text.grid(row=4, column=0, columnspan=3, pady=5)
    
    def get_isky_direct():
        api_key = api_key_entry.get().strip()
        purchase_date = date_entry.get().strip()
        zipcode = zipcode_entry.get().strip()
        
        if not all([api_key, purchase_date, zipcode]):
            messagebox.showerror("Error", "All fields are required")
            return
            
        try:
            # Convert purchase date if needed
            formatted_date = convert_excel_date(purchase_date)
            if not formatted_date:
                messagebox.showerror("Error", "Invalid purchase date format")
                return
                
            # Calculate date range
            base_date = datetime.strptime(formatted_date, '%m/%d/%Y')
            start_date = base_date + timedelta(days=1)
            end_date = base_date + timedelta(days=5)
            date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
            
            # API request
            url = "https://api.iskytracking.com/v2/tracking"
            decode_url = "https://api.iskytracking.com/v2/tracking/ups"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Initial request
            initial_payload = {
                "country": "1",
                "zipcode": zipcode,
                "tracking_type": 1,
                "start": 0,
                "city": 0,
                "date_range": date_range,
                "ship_or_deliver": "p",
                "limit": 1
            }
            
            initial_response = requests.post(url, headers=headers, data=json.dumps(initial_payload))
            initial_data = initial_response.json()
            total_records = initial_data.get('total', 0)
            
            if total_records == 0:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"No records found for zipcode {zipcode}")
                return
                
            # Get all records
            payload = {**initial_payload, "limit": total_records}
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            tracking_data = response.json()
            
            # Find suitable record
            selected_item, max_time_diff = find_suitable_record(tracking_data)
            
            if selected_item:
                # Decode tracking number
                decode_data = {"tracking_number": selected_item['tracking_number']}
                decode_response = requests.post(decode_url, headers=headers, data=json.dumps(decode_data))
                decoded_data = decode_response.json()
                
                if decoded_data.get('rs') and decoded_data.get('rs') != 'N/A':
                    USED_ZIPCODES.add(zipcode)  # Add to used zipcodes
                    result = (
                        f"Carrier: {selected_item['tracking_type']}\n"
                        f"Tracking Number: {decoded_data.get('rs')}\n"
                        f"Status: {selected_item['status']}\n"
                        f"Ship DateTime: {selected_item['packed_at']}\n"
                        f"Delivery DateTime: {selected_item['scheduled_delivery']}\n"
                        f"Duration: {round(max_time_diff / (24 * 3600), 2)} days\n"
                        f"Zipcode: {zipcode}"
                    )
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, result)
                else:
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, f"Invalid tracking number for zipcode {zipcode}")
            else:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"No suitable records found for zipcode {zipcode}")
                
        except Exception as e:
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"Error: {str(e)}")
    
    # Submit Button
    submit_button = ttk.Button(isky_frame, text="Get Tracking", command=get_isky_direct)
    submit_button.grid(row=3, column=0, columnspan=3, pady=10)
    
    return isky_frame

def setup_gui():
    global root
    root = tk.Tk()
    root.title("Tracking Data Tool")
    
    # Tạo notebook để chứa các tab
    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, expand=True)
    
    # Tab API
    api_frame = create_api_frame(notebook)
    notebook.add(api_frame, text="Monkey Tracking")
    
    # Tab Excel
    excel_frame = create_excel_tab(notebook)
    notebook.add(excel_frame, text="Excel Processing")
    
    # Tab iSky Direct
    isky_frame = create_isky_tab(notebook)
    notebook.add(isky_frame, text="iSky Tracking")
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
