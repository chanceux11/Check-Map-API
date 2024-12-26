import tkinter as tk
from tkinter import ttk
import requests
import random
import time
import pyperclip  
from datetime import timedelta
import threading  

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

def get_random_user_agent():
    return random.choice(user_agents)

def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

def check_user_status(username):
    url = f"https://feedback.ebay.com/fdbk/feedback_profile/{username}"
    # url = f"https://www.ebay.com/usr/{username}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": "https://pages.ebay.com/services/forum/feedback-login.html",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Forwarded-For": get_random_ip(),  
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        # print("response", response.text)
        if "Please verify yourself to continue" in response.text:
            return "CAPTCHA"
        else:
            if "Sorry, this user was not found" or "Oops. There seems to be a problem loading the page." in response.text:
                return "SUSPEND"
            elif "Click to visit user profile page":
                return "ACTIVE"
            else:
                return "UNKNOWN"
            
    except requests.RequestException:
        return "ERROR"

def check_users():
    start_time = time.time()
    
    usernames = user_input.get("1.0", "end-1c").split("\n")
    checked_users = 0
    captcha_count = 0

     
    result_label.config(text="")
    copy_label.config(text="")
    result_tree.delete(*result_tree.get_children())  
    
     
    def worker(username):
        nonlocal checked_users, captcha_count
        username = username.strip()   
        if '"' in username:
             
            username = username.replace('"', '')
            if not username:   
                return
        
        status = check_user_status(username)
        if status == "CAPTCHA":
            captcha_count += 1
        checked_users += 1
        result_tree.insert("", "end", values=(username, status))   
 
    threads = []
    for username in usernames:
        thread = threading.Thread(target=worker, args=(username,))
        threads.append(thread)
        thread.start()
 
    for thread in threads:
        thread.join()

    end_time = time.time()
    elapsed_time = timedelta(seconds=int(end_time - start_time))
     
    result_label.config(text=f"Checked {checked_users} users, {captcha_count} CAPTCHA.\nTime: {str(elapsed_time)}")
 
def copy_data():
    copied_data = ""
    for item in result_tree.get_children():
        username = result_tree.item(item)['values'][0]
        status = result_tree.item(item)['values'][1]
        copied_data += f"{username}\t{status}\n"   
 
    pyperclip.copy(copied_data)
    copy_label.config(text="Data copied!")
 
root = tk.Tk()
root.title("Check Live Ebay")
root.geometry("600x700")
 
label = tk.Label(root, text="Ebay Usernames:", font=("Arial", 12))
label.pack(pady=10)
 
user_input = tk.Text(root, height=10, width=50, font=("Arial", 12))
user_input.pack(pady=10)
 
check_button = tk.Button(root, text="Check Status", font=("Arial", 12), command=lambda: threading.Thread(target=check_users).start())
check_button.pack(pady=10)
 
columns = ("Username", "Status")
result_tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
result_tree.heading("Username", text="Username")
result_tree.heading("Status", text="Status")
result_tree.pack(pady=10)
 
result_label = tk.Label(root, text="", font=("Arial", 12), fg="green")
result_label.pack(pady=2)
 
copy_button = tk.Button(root, text="Copy Data", font=("Arial", 12), command=copy_data)
copy_button.pack(pady=5)
 
copy_label = tk.Label(root, text="", font=("Arial", 12), fg="blue")
copy_label.pack(pady=2)
 
root.mainloop()
