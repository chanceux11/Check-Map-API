import tkinter as tk
from tkinter import ttk
import requests
import random
import time
import pyperclip  # Dùng thư viện pyperclip để sao chép vào clipboard
from datetime import timedelta
import threading  # Thêm thư viện threading để chạy tác vụ trong background

# Danh sách User-Agent để thay đổi ngẫu nhiên
user_agents = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
  "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
  "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/89.0",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
  "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
  "Mozilla/5.0 (Linux; U; Android 10; en-US; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
  "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
]

# Hàm lấy User-Agent ngẫu nhiên
def get_random_user_agent():
    return random.choice(user_agents)

# Hàm tạo địa chỉ IP giả ngẫu nhiên cho "X-Forwarded-For"
def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

# Hàm kiểm tra trạng thái của tài khoản eBay
def check_user_status(username):
    url = f"https://feedback.ebay.com/fdbk/feedback_profile/{username}"
    
    while True:  # Vòng lặp để thử lại khi gặp CAPTCHA
        headers = {
            "User-Agent": get_random_user_agent(),
            "Referer": "https://pages.ebay.com/services/forum/feedback-login.html",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Forwarded-For": get_random_ip(),
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            location = "Unknown"
            
            # Tìm location từ chuỗi "Member since"
            if "Member since:" in response.text:
                member_info = response.text.split("Member since:")[1]
                if " in " in member_info:
                    location = member_info.split(" in ")[1].split("<")[0].strip()
            
            if "Please verify yourself to continue" in response.text:
                time.sleep(1)  # Đợi 1 giây trước khi thử lại
                continue  # Quay lại đầu vòng lặp để thử lại
            if "Oops. There seems to be a problem loading the page." in response.text:
                return "SUSPEND", location
            if "Not a registered user" in response.text:
                return "SUSPEND", location
            else:
                return "ACTIVE", location
                
        except requests.RequestException:
            return "ERROR", "Unknown"

# Thêm hàm kiểm tra username hợp lệ
def is_valid_username(username):
    # Kiểm tra username chỉ chứa chữ, số và dấu gạch ngang
    return all(c.isalnum() or c == '-' or c == '_' for c in username)

# Hàm xử lý các username nhập vào và kiểm tra
def check_users():
    global captcha_count
    captcha_count = 0
    
    start_time = time.time()
    usernames = user_input.get("1.0", "end-1c").split("\n")
    checked_users = 0
    captcha_count = 0
    
    # Dictionary để lưu thống kê theo location
    location_stats = {}
    # Dictionary để lưu kết quả tạm thời theo index
    results = {}

    result_label.config(text="")
    copy_label.config(text="")
    result_tree.delete(*result_tree.get_children())
    stats_tree.delete(*stats_tree.get_children())
    result_label.config(text="Checking...")

    def worker(username, index):
        nonlocal checked_users
        username = username.replace('"', '')

        if username == "":  # Nếu là dòng trống
           results[index] = ("", "", "")
           return
           
        if not is_valid_username(username):  # Kiểm tra username hợp lệ
           results[index] = (username, "INVALID", "")  # Đánh dấu username không hợp lệ
           return
        
        status, location = check_user_status(username)
        
        if location not in location_stats:
            location_stats[location] = {"total": 0, "active": 0, "suspend": 0}
        
        location_stats[location]["total"] += 1
        if status == "ACTIVE":
            location_stats[location]["active"] += 1
        elif status == "SUSPEND":
            location_stats[location]["suspend"] += 1
            
        checked_users += 1
        results[index] = (username, status, location)

    # Chạy các threads
    threads = []
    for index, username in enumerate(usernames):
        if username.strip() == '"':  # Bỏ qua dòng chỉ chứa dấu ngoặc kép
            continue
        thread = threading.Thread(target=worker, args=(username, index))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Insert kết quả theo thứ tự ban đầu
    for i in range(len(usernames)):
        if i in results:
            username, status, location = results[i]
            result_tree.insert("", "end", values=(username, status, location))

    # Hiển thị thống kê location
    for loc, stats in location_stats.items():
        stats_tree.insert("", "end", values=(
            loc,
            stats["total"],
            stats["active"],
            stats["suspend"]
        ))

    end_time = time.time()
    elapsed_time = timedelta(seconds=int(end_time - start_time))
    result_label.config(text=f"Checked {checked_users} users, {captcha_count} CAPTCHA.\nTime: {str(elapsed_time)}")

# Hàm sao chép cả Username và Status vào clipboard
def copy_data():
    copied_data = ""
    for item in result_tree.get_children():
        username = result_tree.item(item)['values'][0]
        status = result_tree.item(item)['values'][1]
        location = result_tree.item(item)['values'][2]
        copied_data += f"{username}\t{status}\t{location}\n"

    pyperclip.copy(copied_data)
    copy_label.config(text="Data copied!")

# Tạo giao diện với Tkinter
root = tk.Tk()
root.title("Check Live Ebay v1.0")
root.geometry("600x725")

# Thêm label cho việc nhập username
label = tk.Label(root, text="Ebay Usernames:", font=("Arial", 12))
label.pack(pady=10)

# Thêm textbox để nhập danh sách username
user_input = tk.Text(root, height=10, width=50, font=("Arial", 12))
user_input.pack(pady=10)

# Thêm nút để bắt đầu kiểm tra
check_button = tk.Button(root, text="Check Status", font=("Arial", 12), command=lambda: threading.Thread(target=check_users).start())
check_button.pack(pady=10)

# Thêm bảng để hiển thị kết quả
columns = ("Username", "Status", "Location")
result_tree = ttk.Treeview(root, columns=columns, show="headings", height=6)
result_tree.heading("Username", text="Username")
result_tree.heading("Status", text="Status")
result_tree.heading("Location", text="Location")
result_tree.pack(pady=10)
result_tree.column("Username", width=150)  # Cột Location rộng hơn
result_tree.column("Status", width=150, anchor="center")
result_tree.column("Location", width=150, anchor="center")

# Thêm bảng thống kê location
stats_tree = ttk.Treeview(root, columns=("Location", "Total", "Active", "Suspend"), show="headings", height=5)
stats_tree.heading("Location", text="Location")
stats_tree.heading("Total", text="Total Users")
stats_tree.heading("Active", text="Active")
stats_tree.heading("Suspend", text="Suspend")
stats_tree.pack(pady=10)

stats_tree.column("Location", width=200)  # Cột Location rộng hơn
stats_tree.column("Total", width=100, anchor="center")
stats_tree.column("Active", width=100, anchor="center")
stats_tree.column("Suspend", width=100, anchor="center")

# Label để hiển thị kết quả kiểm tra
result_label = tk.Label(root, text="", font=("Arial", 12), fg="green")
result_label.pack(pady=2)

# Nút sao chép
copy_button = tk.Button(root, text="Copy Data", font=("Arial", 12), command=copy_data)
copy_button.pack(pady=5)

# Label để hiển thị thông báo sao chép
copy_label = tk.Label(root, text="", font=("Arial", 12), fg="blue")
copy_label.pack(pady=2)



# Chạy giao diện
root.mainloop()
