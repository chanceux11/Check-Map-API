import tkinter as tk
from tkinter import ttk, messagebox
from geopy.geocoders import Nominatim
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import os
current_dir = os.path.dirname(__file__)
icon_path = os.path.join(current_dir, "logo.ico")

# Configure Geolocator
geolocator = Nominatim(user_agent="address_checker", timeout=10)

# Function to calculate similarity ratio
def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

# Geocode function for OpenStreetMap
def geocode_address(address):
    try:
        location = geolocator.geocode(address)
        if location:
            name = location.raw.get("name", "")
            similarity = similarity_ratio(address.lower(), name.lower())
            if similarity > 0.5:
                return address, None
            else:
                return None, address
    except Exception as e:
        print(f"Error with address '{address}': {e}")
        return None, address
    return None, address

# Selenium function for Google Maps
def check_address_google(driver, address):
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'searchboxinput'))
        )
        search_box.clear()
        search_box.send_keys(address)
        search_box.send_keys(Keys.RETURN)
        time.sleep(0.5)

        # Wait for the result to load
        WebDriverWait(driver, 0.5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'DkEaL'))
        )

        # Get the address shown on the map
        map_address = driver.find_element(By.CLASS_NAME, 'DkEaL').text
        return map_address  # Trả về địa chỉ hiển thị trên bản đồ
    except Exception as e:
        print(f"Error with address '{address}': {e}")
        return None  # Trả về None nếu có lỗi


# Handle OpenStreetMap method
def check_addresses_osm_thread():
    addresses = input_text.get("1.0", "end-1c").splitlines()
    addresses = [addr.strip() for addr in addresses if addr.strip()]

    if not addresses:
        messagebox.showerror("Error", "Please enter at least one address.")
        return

    status_label.config(text="Đang kiểm tra địa chỉ bằng OpenStreetMap, vui lòng đợi...")
    root.update_idletasks()  # Cập nhật giao diện ngay lập tức

    valid_addresses = []
    invalid_addresses = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(geocode_address, addresses))

    for valid, invalid in results:
        if valid:
            valid_addresses.append(valid)
        if invalid:
            invalid_addresses.append(invalid)

    elapsed_time = time.time() - start_time

    output_text.delete("1.0", "end")
    output_text.insert("end", "\n".join(valid_addresses) + "\n")

    invalid_output.delete("1.0", "end")
    invalid_output.insert("end", "\n".join(invalid_addresses) + "\n")

    output_label.config(text=f"Valid Addresses ({len(valid_addresses)}):")
    invalid_label.config(text=f"Invalid Addresses ({len(invalid_addresses)}):")

    result_label.config(text=f"Checked {len(addresses)} addresses in {elapsed_time:.2f} seconds.")
    status_label.config(text="Hoàn thành kiểm tra.")

def check_addresses_osm():
    threading.Thread(target=check_addresses_osm_thread, daemon=True).start()

def check_addresses_google_maps():
    addresses = input_text.get("1.0", "end-1c").splitlines()
    addresses = [addr.strip() for addr in addresses if addr.strip()]

    if not addresses:
        messagebox.showerror("Error", "Please enter at least one address.")
        return

    status_label.config(text="Đang kiểm tra địa chỉ bằng Google Maps, vui lòng đợi...")
    root.update_idletasks()  # Cập nhật giao diện ngay lập tức

    # Lấy giá trị từ checkbox và ô nhập thời gian
    headless_mode = is_headless.get()
    timeout = wait_time.get()

    # Cấu hình Chrome driver
    options = Options()
    if headless_mode:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)
    driver.get('https://www.google.com/maps')

    valid_addresses = []
    invalid_addresses = []
    start_time = time.time()

    for address in addresses:
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'searchboxinput'))
            )
            search_box.clear()
            time.sleep(0.2)
            search_box.send_keys(address)
            search_box.send_keys(Keys.RETURN)
            time.sleep(0.5)

            # Sử dụng thời gian chờ tùy chỉnh
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'DkEaL'))
            )
            map_address = driver.find_element(By.CLASS_NAME, 'DkEaL').text
            valid_addresses.append(f"{map_address}")
        except Exception as e:
            print(f"Error with address '{address}': {e}")
            invalid_addresses.append(address)

    driver.quit()

    # Loại bỏ trùng lặp
    # valid_addresses = list(set(valid_addresses))
    # invalid_addresses = list(set(invalid_addresses))

    valid_addresses = list((valid_addresses))
    invalid_addresses = list((invalid_addresses))

    # Sắp xếp danh sách (tuỳ chọn nếu cần hiển thị gọn gàng)
    # valid_addresses.sort()
    # invalid_addresses.sort()

    elapsed_time = time.time() - start_time

    output_text.delete("1.0", "end")
    output_text.insert("end", "\n".join(valid_addresses) + "\n")

    invalid_output.delete("1.0", "end")
    invalid_output.insert("end", "\n".join(invalid_addresses) + "\n")

    output_label.config(text=f"Valid Addresses ({len(valid_addresses)}):")
    invalid_label.config(text=f"Invalid Addresses ({len(invalid_addresses)}):")

    result_label.config(text=f"Checked {len(addresses)} addresses in {elapsed_time:.2f} seconds.")
    status_label.config(text="Hoàn thành kiểm tra.")



def add_link_to_addresses():
    link = link_entry.get().strip()
    addresses = addlink_text.get("1.0", "end-1c").splitlines()
    addresses = [addr.strip() for addr in addresses if addr.strip()]

    if not link or not addresses:
        messagebox.showerror("Error", "Please enter both a link and at least one address.")
        return

    linked_addresses = [f"{link}{address}" for address in addresses]

    linked_output.delete("1.0", "end")
    linked_output.insert("end", "\n".join(linked_addresses))

# Function to clear the input and result fields
def clear_fields():
    # Clear input and result fields in Tab 1
    input_text.delete("1.0", "end")
    output_text.delete("1.0", "end")
    invalid_output.delete("1.0", "end")
    result_label.config(text="")
    status_label.config(text="")
    
    # Clear input and result fields in Tab 2
    addlink_text.delete("1.0", "end")
    linked_output.delete("1.0", "end")
    link_entry.delete(0, "end")
    link_entry.insert(0, "https://www.google.com/maps/place/")

# Main GUI setup
root = tk.Tk()
root.title("Address Checker")
root.geometry("600x800")

# Thêm các biến toàn cục để lưu trạng thái
is_headless = tk.BooleanVar(value=True)  # Mặc định là chế độ ẩn
wait_time = tk.DoubleVar(value=1)      # Mặc định là 5 giây

# Thêm logo cho cửa sổ
# root.iconbitmap(icon_path)

# Center the window on the screen
window_width = 600
window_height = 850

# Get the screen width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate position
x_pos = (screen_width - window_width) // 2
y_pos = (screen_height - window_height) // 2

# Set the position of the window
root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

style = ttk.Style()
style.configure("TButton", font=("Arial", 10))
style.configure("TLabel", font=("Arial", 12))

# Create notebook (tabs)
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Tab 1 - Address Checker
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text="Address Checker")

# Input frame for Address Checker
input_frame = ttk.LabelFrame(tab1, text="Input Addresses", padding=10)
input_frame.pack(fill="x", padx=10, pady=10)

input_text = tk.Text(input_frame, height=10, width=60)
input_text.pack(padx=5, pady=5)

# Method selection for Address Checker
method_frame = ttk.Frame(tab1, padding=10)
method_frame.pack(fill="x", padx=10, pady=5)


# Thêm giao diện cho các tùy chọn trình duyệt
options_frame = ttk.LabelFrame(tab1, text="Browser Options", padding=10)
options_frame.pack(fill="x", padx=10, pady=5)
# Checkbox để chọn trình duyệt ẩn
headless_checkbox = ttk.Checkbutton(
    options_frame, text="Run browser in headless mode", variable=is_headless
)
headless_checkbox.pack(side="left", padx=10)
# Ô nhập thời gian chờ
wait_label = ttk.Label(options_frame, text="Wait time (seconds):")
wait_label.pack(side="left", padx=5)
wait_entry = ttk.Entry(options_frame, textvariable=wait_time, width=5)
wait_entry.pack(side="left", padx=5)
# Cập nhật chiều cao cửa sổ
root.geometry(f"{window_width}x{window_height+50}+{x_pos}+{y_pos}")



# Pack buttons with equal space on both sides
osm_button = ttk.Button(method_frame, text="Check with OpenStreetMap", command=check_addresses_osm)
osm_button.pack(side="left", padx=10, expand=True)

# Add "Clear" button to clear all fields
clear_button = ttk.Button(method_frame, text="Clear All", command=clear_fields)
clear_button.pack(side="left", padx=10, expand=True)

google_button = ttk.Button(method_frame, text="Check with Google Maps", command=lambda: threading.Thread(target=check_addresses_google_maps).start())
google_button.pack(side="left", padx=10, expand=True)



# Status label for Address Checker
status_label = ttk.Label(tab1, text="", font=("Arial", 15), foreground="blue")
status_label.pack(pady=5)
result_label = ttk.Label(tab1, text="", font=("Arial", 12))
result_label.pack(pady=10)

# Results frame for Address Checker (inside Tab 1)
results_frame = ttk.LabelFrame(tab1, text="Results", padding=10)
results_frame.pack(fill="both", expand=True, padx=10, pady=10)

output_label = ttk.Label(results_frame, text="Valid Addresses:")
output_label.pack(anchor="w", padx=5)

output_text = tk.Text(results_frame, height=10, width=60, bg="#e8f5e9")
output_text.pack(padx=5, pady=5)

invalid_label = ttk.Label(results_frame, text="Invalid Addresses:")
invalid_label.pack(anchor="w", padx=5)

invalid_output = tk.Text(results_frame, height=10, width=60, bg="#ffebee")
invalid_output.pack(padx=5, pady=5)



# Tab 2 - AddLink
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text="AddLink")

# AddLink frame
addlink_frame = ttk.LabelFrame(tab2, text="Add Link to Addresses", padding=10)
addlink_frame.pack(fill="x", padx=10, pady=10)

link_label = ttk.Label(addlink_frame, text="Enter link (e.g., https://www.google.com/maps/place/):")
link_label.pack(padx=5, pady=5)

link_entry = tk.Entry(addlink_frame, width=60)
link_entry.insert(0, "https://www.google.com/maps/place/")
link_entry.pack(padx=5, pady=5)

addlink_text = tk.Text(addlink_frame, height=10, width=60)
addlink_text.pack(padx=5, pady=5)

addlink_button = ttk.Button(addlink_frame, text="Add Link to Addresses", command=add_link_to_addresses)
addlink_button.pack(side="left", padx=10, expand=True)

# Add "Clear" button to clear all fields
clear_button = ttk.Button(addlink_frame, text="Clear All", command=clear_fields)
clear_button.pack(side="left", padx=10, expand=True)

# Display added links in AddLink
linked_output_frame = ttk.LabelFrame(tab2, text="Addresses with Links", padding=10)
linked_output_frame.pack(fill="both", expand=True, padx=10, pady=10)

linked_output = tk.Text(linked_output_frame, height=10, width=60, bg="#e8f5e9")
linked_output.pack(padx=5, pady=5)

# Start the GUI
root.mainloop()
