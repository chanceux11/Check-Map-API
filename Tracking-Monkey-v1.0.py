import requests
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from iso3166 import countries
import pandas as pd
from tkinter import filedialog
import os
import threading

def get_tracking_data(api_key, country, date_from, date_to, city):
    api_key = api_key.strip()
    
    try:
        if isinstance(date_from, str):
            date_from = pd.to_datetime(date_from).strftime('%Y-%m-%d')
            
        if isinstance(date_to, str):
            date_to = pd.to_datetime(date_to).strftime('%Y-%m-%d')
    except Exception as e:
        return f"Date format error: {str(e)}"

    url = "https://monkey-tools.co/api/v2/non-us/tracking-requests"
    payload = {
        "country": country,
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

def process_excel_file(api_key):
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
            
            # Đọc file Excel và chỉ định dtype là object cho tất cả các cột
            with pd.ExcelWriter(file_path, mode='a', if_sheet_exists='overlay', engine='openpyxl') as writer:
                # Đọc Excel và chỉ định dtype là object cho tất cả các cột
                df = pd.read_excel(file_path, dtype=str)
                original_columns = df.columns.tolist()
                
                # Tìm các cột cần thiết (không phân biệt hoa thường)
                column_mapping = {
                    'country': next((col for col in df.columns if 'buyer country' in col.lower()), None),
                    'city': next((col for col in df.columns if 'buyer city' in col.lower()), None),
                    'start_date': next((col for col in df.columns if 'start monkey' in col.lower()), None),
                    'end_date': next((col for col in df.columns if 'end monkey' in col.lower()), None)
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
                    if result_columns['tracking'] in df.columns and not pd.isna(df.at[index, result_columns['tracking']]):
                        print(f"Skipping row {index + 2}: Already has tracking number")
                        continue
                        
                    country_name = str(row[column_mapping['country']]).strip()
                    city = str(row[column_mapping['city']]).strip()
                    date_from = str(row[column_mapping['start_date']]).strip()
                    date_to = str(row[column_mapping['end_date']]).strip()
                    
                    # Bỏ qua nếu thiếu thông tin
                    if (pd.isna(country_name) or pd.isna(city) or 
                        pd.isna(date_from) or pd.isna(date_to)):
                        print(f"Skipping row {index + 2}: Missing data")
                        continue
                        
                    country_code = get_country_code(country_name)
                    if not country_code:
                        print(f"Invalid country name at row {index + 2}: {country_name}")
                        continue
                    
                    api_call_count += 1
                        
                    result = get_tracking_data(api_key, country_code, date_from, date_to, city)
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
                
            if success_count > 0:
                messagebox.showinfo("Success", 
                    f"Excel file has been updated successfully!\n"
                    f"Processed {api_call_count} rows\n"
                    f"Updated {success_count} tracking numbers")
            else:
                messagebox.showwarning("Warning", 
                    f"No data was updated.\n"
                    f"Processed {api_call_count} rows but found no valid tracking numbers.")
            
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
    
    # API Key input
    api_key_label = ttk.Label(excel_frame, text="API-Key:")
    api_key_label.grid(row=0, column=0, sticky=tk.W)
    api_key_entry = ttk.Entry(excel_frame, width=40)
    api_key_entry.grid(row=0, column=1, pady=5)
    
    # Process button
    process_button = ttk.Button(
        excel_frame,
        text="Process Excel File",
        command=lambda: process_excel_file(api_key_entry.get()) if api_key_entry.get().strip() else messagebox.showerror("Error", "Please enter API key")
    )
    process_button.grid(row=1, column=0, columnspan=2, pady=10)
    
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

def setup_gui():
    global root
    root = tk.Tk()
    root.title("Tracking Data Tool")
    
    # Tạo notebook để chứa các tab
    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, expand=True)
    
    # Tab API
    api_frame = create_api_frame(notebook)
    notebook.add(api_frame, text="API Tracking Data")
    
    # Tab Excel
    excel_frame = create_excel_tab(notebook)
    notebook.add(excel_frame, text="Excel Processing")
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
