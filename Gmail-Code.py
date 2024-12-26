import tkinter as tk
from tkinter import scrolledtext
import imaplib
import email
from email.header import decode_header
import re
import threading
import datetime
import os

class GmailCodeReader:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Gmail Code Reader")
        self.window.geometry("600x400")
        
        # Tạo frame chính
        main_frame = tk.Frame(self.window)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Tạo các controls
        self.create_controls(main_frame)
        
        # Biến để kiểm soát thread
        self.running = False
        self.thread = None
        
        # Tạo thư mục logs nếu chưa tồn tại
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Tạo file log nếu chưa tồn tại
        self.log_file = os.path.join('logs', 'codeGmail.txt')
        # Thêm biến để lưu ID mail cuối cùng
        self.last_email_id = None

    def create_controls(self, frame):
        # Email input
        tk.Label(frame, text="Email:").pack(anchor='w')
        self.email_entry = tk.Entry(frame, width=40)
        self.email_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Password input
        tk.Label(frame, text="App Password:").pack(anchor='w')
        self.password_entry = tk.Entry(frame, width=40, show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons frame
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="Start", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Log area
        self.log_area = scrolledtext.ScrolledText(frame, height=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
        
        # Ghi đè vào file (mode 'w' thay vì 'a')
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"{message}")

    def extract_code(self, text):
        patterns = [
            r'\b\d{6}\b',  # Mã 6 số
            r'\b\d{4}\b',  # Mã 4 số
            r'\b\d{5}\b',  # Mã 5 số
            r'\b\d{8}\b',  # Mã 8 số
        ]
        
        for pattern in patterns:
            codes = re.findall(pattern, text)
            if codes:
                return codes[0]
        return None

    def check_new_emails(self, imap):
        try:
            imap.select("INBOX")
            # Tìm tất cả email, sắp xếp theo thứ tự mới nhất
            _, messages = imap.search(None, "ALL")
            
            if not messages[0]:
                return
                
            # Lấy ID email mới nhất
            latest_email_id = messages[0].split()[-1]
            
            # Nếu đây là lần đầu chạy hoặc có email mới
            if self.last_email_id is None:
                self.last_email_id = latest_email_id
                return
            
            if latest_email_id != self.last_email_id:
                # Chỉ xử lý email mới nhất
                _, msg_data = imap.fetch(latest_email_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                charset = part.get_content_charset() or 'utf-8'
                                body = part.get_payload(decode=True)
                                
                                try:
                                    body = body.decode(charset)
                                except UnicodeDecodeError:
                                    for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                                        try:
                                            body = body.decode(encoding)
                                            break
                                        except UnicodeDecodeError:
                                            continue
                                
                                code = self.extract_code(body)
                                if code:
                                    self.log_message(f"{code}")
                                break
                            except Exception as e:
                                self.log_message(f"Error reading content: {str(e)}")
                else:
                    try:
                        charset = email_message.get_content_charset() or 'utf-8'
                        body = email_message.get_payload(decode=True)
                        
                        try:
                            body = body.decode(charset)
                        except UnicodeDecodeError:
                            for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                                try:
                                    body = body.decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                        
                        code = self.extract_code(body)
                        if code:
                            self.log_message(f"{code}")
                    except Exception as e:
                        self.log_message(f"Error reading content: {str(e)}")
                
                # Cập nhật ID email cuối cùng
                self.last_email_id = latest_email_id
                    
        except Exception as e:
            self.log_message(f"Error checking emails: {str(e)}")

    def monitor_emails(self):
        try:
            imap_server = "imap.gmail.com"
            imap = imaplib.IMAP4_SSL(imap_server)
            imap.login(self.email_entry.get(), self.password_entry.get())
            self.log_message("Connected to Gmail successfully!")
            
            while self.running:
                self.check_new_emails(imap)
                self.window.after(1000)  # Đợi 1 giây
            
            imap.logout()
            self.log_message("Disconnected from Gmail")
            
        except Exception as e:
            self.log_message(f"Connection error: {str(e)}")
            self.stop_monitoring()

    def start_monitoring(self):
        if not self.email_entry.get() or not self.password_entry.get():
            self.log_message("Please enter email and password!")
            return
            
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.email_entry.config(state=tk.DISABLED)
        self.password_entry.config(state=tk.DISABLED)
        
        self.thread = threading.Thread(target=self.monitor_emails)
        self.thread.start()

    def stop_monitoring(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.email_entry.config(state=tk.NORMAL)
        self.password_entry.config(state=tk.NORMAL)

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = GmailCodeReader()
    app.run()