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
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
    ]
# Danh sách Referer ngẫu nhiên
referers = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.ecosia.org/",
    "https://www.facebook.com/",
    "https://www.twitter.com/",
    "https://www.linkedin.com/",
    "https://www.amazon.com/",
    "https://www.reddit.com/"
    "https://pages.ebay.com/services/forum/feedback-login.html"
]

# Hàm lấy User-Agent ngẫu nhiên
def get_random_user_agent():
    return random.choice(user_agents)

# Hàm tạo địa chỉ IP giả ngẫu nhiên cho "X-Forwarded-For"
def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

# Hàm kiểm tra trạng thái của tài khoản eBay
def check_user_status(username, max_retries=5):

    def check_alternate_url(username):
        alt_url = f"https://www.ebay.com/usr/{username}"
        headers = {
            "User-Agent": get_random_user_agent(),
            "Referer": random.choice(referers),
            "Accept-Language": "en-US,en;q=0.9",
            "X-Forwarded-For": get_random_ip(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": "dp1=bpbl/US6475aa240^; ebay=%5Esbf%3D%23000000%5E",
            "Connection": "keep-alive"
        }
        
        try:
            response = requests.get(alt_url, headers=headers, timeout=5)
            
            # Check for suspension
            if "No longer a registered user." in response.text:
                return "SUSPEND", "Unknown"
                
            # If active, try to get location
            location = "Unknown"
            if '<span class="str-text-span BOLD">' in response.text:
                try:
                    location = response.text.split('<span class="str-text-span BOLD">')[1].split('</span>')[0].strip()
                except:
                    pass
                    
            return "ACTIVE", location
            
        except requests.RequestException:
            return None, None
    
    url = f"https://feedback.ebay.com/fdbk/feedback_profile/{username}"
    
    retry_count = 0
    while retry_count < max_retries:  # Try up to max_retries times
        headers = {
            "User-Agent": get_random_user_agent(),
            "Referer": random.choice(referers),
            "Accept-Language": "en-US,en;q=0.9",
            "X-Forwarded-For": get_random_ip(),
            # Add these headers to ensure English response
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": "dp1=bpbl/US6475aa240^; ebay=%5Esbf%3D%23000000%5E",
            "Connection": "keep-alive"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            location = "Unknown"
            
            # Tìm location từ chuỗi "Member since"
            if "Member since:" in response.text:
                member_info = response.text.split("Member since:")[1]
                if " en " in member_info:
                    location = member_info.split(" en ")[1].split("<")[0].strip()
                if " in " in member_info:
                    location = member_info.split(" in ")[1].split("<")[0].strip()
                
            
            if "Please verify yourself to continue" in response.text:
                time.sleep(1)
                continue
                
            # Check SUSPEND cases first
            if "Oops. There seems to be a problem loading the page." in response.text or "Not a registered user" in response.text:
                return "SUSPEND", location  # Return immediately for SUSPEND cases
            
            # If we reach here, the account is ACTIVE
            if location == "Unknown":
                alt_status, alt_location = check_alternate_url(username)
                if alt_status == "SUSPEND":
                    return "SUSPEND", "Unknown"
                elif alt_status == "ACTIVE":
                    # If ACTIVE but Unknown, retry up to 5 times
                    inner_retry = 0
                    while inner_retry < max_retries:
                        time.sleep(1)
                        alt_status, alt_location = check_alternate_url(username)
                        if alt_location != "Unknown":
                            return "ACTIVE", alt_location
                        inner_retry += 1
                    
                if retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(1)
                    continue
            
            return "ACTIVE", location
                
        except requests.RequestException:
            if retry_count < max_retries - 1:  # Still have retries left
                retry_count += 1
                time.sleep(1)
                continue
            return "ERROR", "Unknown"
            
        retry_count += 1
    
    # If we've exhausted all retries, try alternate URL one last time
    alt_status, alt_location = check_alternate_url(username)
    if alt_status:
        return alt_status, alt_location
        
    if "feedback_profile" in response.text:
        return "ACTIVE", "Unknown"
    return "ERROR", "Unknown"

# Thêm hàm kiểm tra username hợp lệ
def is_valid_username(username):
    # Kiểm tra username chỉ chứa chữ, số và dấu gạch ngang
    return all(c.isalnum() or c == '-' or c == '_' or c == '.' for c in username)

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
        username = username.strip()

        if username == "":  # Nếu là dòng trống
           results[index] = ("", "", "")
           return
           
        # if not is_valid_username(username):  # Kiểm tra username hợp lệ
        #    results[index] = (username, "INVALID", "")  # Đánh dấu username không hợp lệ
        #    return
        
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
    # Tính tổng số tài khoản và số tài khoản bị suspend
    total_accounts = 0
    total_suspend = 0
    for loc, stats in location_stats.items():
        total_accounts += stats["total"]
        total_suspend += stats["suspend"]

    # Cập nhật result_label với thông tin tổng hợp
    result_label.config(text=f"Checked {checked_users} users, {captcha_count} CAPTCHA.\n"
                            f"Time: {str(elapsed_time)}\n"
                            f"Total accounts: {total_accounts}, Suspended: {total_suspend}")

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
root.title("Check Live Ebay v1.4")
root.geometry("600x780")

# Thêm code để căn giữa cửa sổ
window_width = 600
window_height = 780
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
center_x = int(screen_width/2 - window_width/2)
center_y = int(screen_height/2 - window_height/2)
root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

# Khóa kích thước cửa sổ
root.resizable(False, False)

# Thêm label cho việc nhập username
label = tk.Label(root, text="Ebay Usernames:", font=("Arial", 12))
label.pack(pady=3)

# Thêm textbox để nhập danh sách username
user_input = tk.Text(root, height=10, width=50, font=("Arial", 12))
user_input.pack(pady=10)
# Thêm biến để lưu trạng thái hiển thị
show_results_var = None

# Thêm hàm để toggle hiển thị bảng kết quả
def toggle_results_display():
    if show_results_var.get():
        result_tree.pack(pady=10)
    else:
        result_tree.pack_forget()

# Thêm nút để bắt đầu kiểm tra
check_button = tk.Button(root, text="Check Status", font=("Arial", 12), command=lambda: threading.Thread(target=check_users).start())
check_button.pack(pady=10)

# Thay đổi giá trị mặc định của BooleanVar thành False
show_results_var = tk.BooleanVar(value=False)  # Mặc định không hiển thị
show_results_cb = tk.Checkbutton(root, text="Show Results Table", 
                                variable=show_results_var, 
                                command=toggle_results_display,
                                font=("Arial", 12))
show_results_cb.pack(pady=5)

# Thêm bảng để hiển thị kết quả
columns = ("Username", "Status", "Location")
result_tree = ttk.Treeview(root, columns=columns, show="headings", height=6)
result_tree.heading("Username", text="Username")
result_tree.heading("Status", text="Status")
result_tree.heading("Location", text="Location")
result_tree.column("Username", width=150)
result_tree.column("Status", width=150, anchor="center")
result_tree.column("Location", width=150, anchor="center")

# Đảm bảo bảng kết quả được ẩn khi khởi động
result_tree.pack_forget()

# Thêm bảng thống kê location
stats_tree = ttk.Treeview(root, columns=("Location", "Total", "Active", "Suspend"), show="headings", height=5)
stats_tree.heading("Location", text="Location")
stats_tree.heading("Total", text="Total Users")
stats_tree.heading("Active", text="Active")
stats_tree.heading("Suspend", text="Suspend")
stats_tree.pack(pady=10)

stats_tree.column("Location", width=200, anchor="center")  # Cột Location rộng hơn
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
