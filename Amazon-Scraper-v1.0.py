import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import json
import random
import csv
import pyperclip
from concurrent.futures import ThreadPoolExecutor
import time
import re

class AmazonScraper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Amazon Scraper Tool")
        self.root.resizable(False, False)
        
        self.scraped_data = []
        self.product_links = []
        
        self.create_gui()
        
    def create_gui(self):
        self.root.update_idletasks()  
        width = 1000  
        height = 1000  
        self.root.geometry(f"{width}x{height}")
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2 - 30 
        self.root.geometry(f"+{x}+{y}")
        
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Times new roman", 16, "bold"), padding=10)
        style.configure("Header.TLabel", font=("Times new roman", 12, "bold"))
        style.configure("Status.TLabel", font=("Times new roman", 10), foreground="blue")
        style.configure("Action.TButton", font=("Times new roman", 10, "bold"), padding=5)
        
        main_container = ttk.Frame(self.root, padding="20")
        main_container.pack(expand=True, fill="both")
        
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=0)
        title = ttk.Label(title_frame, text="Amazon Book Scraper", style="Title.TLabel")
        title.pack(anchor="center")
        
        category_frame = ttk.LabelFrame(main_container, text="Lấy links sản phẩm", padding="10")
        category_frame.pack(fill="x", padx=10, pady=3)
        
        url_frame = ttk.Frame(category_frame)
        url_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(url_frame, text="URL Category:", style="Header.TLabel").pack(anchor="w")
        self.category_url = ttk.Entry(url_frame, width=80)
        self.category_url.pack(fill="x", pady=5)
        
        button_frame = ttk.Frame(category_frame)
        button_frame.pack(anchor="center", pady=5)
        
        self.get_links_button = ttk.Button(
            button_frame,
            text="Lấy Links",
            command=self.start_get_links,
            style="Action.TButton"
        )
        self.get_links_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="Dừng",
            command=self.stop_get_links,
            state="disabled",
            style="Action.TButton"
        )
        self.stop_button.pack(side="left", padx=5)
        
        self.links_status = ttk.Label(category_frame, text="", style="Status.TLabel")
        self.links_status.pack(anchor="w")
        
        links_frame = ttk.LabelFrame(main_container, text="Links sản phẩm", padding="10")
        links_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        text_frame = ttk.Frame(links_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.links_text = tk.Text(text_frame, height=8, width=80)
        links_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.links_text.yview)
        self.links_text.configure(yscrollcommand=links_scroll.set)
        
        self.links_text.pack(side="left", fill="both", expand=True)
        links_scroll.pack(side="right", fill="y")
        
        scrape_frame = ttk.LabelFrame(main_container, text="Lấy thông tin sản phẩm", padding="10")
        scrape_frame.pack(fill="x", padx=10, pady=5)
        
        self.scrape_button = ttk.Button(
            scrape_frame,
            text="Lấy Thông Tin",
            command=self.start_scraping,
            style="Action.TButton"
        )
        self.scrape_button.pack(anchor="center", pady=5)
        
        self.scrape_status = ttk.Label(scrape_frame, text="", style="Status.TLabel")
        self.scrape_status.pack(anchor="w")
        
        table_frame = ttk.Frame(main_container)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        table_scroll_y = ttk.Scrollbar(table_frame)
        table_scroll_y.pack(side="right", fill="y")
        
        table_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        table_scroll_x.pack(side="bottom", fill="x")
        
        columns = ("URL", "Title", "ISBN", "Author", "Language", "Book_Type", "Publication_Date", "Image")
        self.table = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings", 
            height=8,
            yscrollcommand=table_scroll_y.set,
            xscrollcommand=table_scroll_x.set
        )
        self.table.pack(fill="both", expand=True)
        
        table_scroll_y.config(command=self.table.yview)
        table_scroll_x.config(command=self.table.xview)
        
        column_widths = {
            "URL": 100,
            "Title": 100,
            "ISBN": 100,
            "Author": 100,
            "Language": 80,
            "Book_Type": 100,
            "Publication_Date": 100,
            "Image": 100
        }
        
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=column_widths[col])
        
        # Frame cho thông báo và nút xuất dữ liệu
        export_frame = ttk.Frame(main_container)
        export_frame.pack(fill="x", pady=3)
        
        self.export_status = ttk.Label(
            export_frame, 
            text="",
            style="Status.TLabel"
        )
        self.export_status.pack(anchor="center", pady=5)
        
        button_frame = ttk.Frame(export_frame)
        button_frame.pack(anchor="center")
        
        ttk.Button(
            button_frame, 
            text="Copy dữ liệu", 
            command=self.copy_to_clipboard,
            style="Action.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame, 
            text="Xuất CSV", 
            command=self.export_to_csv,
            style="Action.TButton"
        ).pack(side="left", padx=5)

    def get_amazon_product_links(self, url):
        if not self.is_running:
            return []
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.get(url)
            time.sleep(2)

            found_50 = False
            max_attempts = 5
            attempts = 0

            while not found_50 and attempts < max_attempts and self.is_running:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                last_product = driver.find_elements(By.CSS_SELECTOR, '.zg-bdg-text')
                for element in last_product:
                    if element.text == '#50':
                        found_50 = True
                        break
                
                attempts += 1

            if not self.is_running:
                return []
            if not found_50:
                self.links_status.config(text="Không tìm thấy sản phẩm #50 sau nhiều lần thử")
                return []

            zg_element = driver.find_element(By.ID, "zg")
            elements = zg_element.find_elements(By.CSS_SELECTOR, "a[href*='/dp/'], a[href*='/gp/product/']")
            
            links = []
            for element in elements:
                if not self.is_running:
                    return []
                href = element.get_attribute('href')
                if href:
                    clean_url = re.sub(r'/ref=.*', '', href)
                    if clean_url not in links:
                        links.append(clean_url)

            return links

        finally:
            driver.quit()

    def start_get_links(self):
        url = self.category_url.get().strip()
        if not url:
            self.links_status.config(
                text="⚠️ Vui lòng nhập URL category!", 
                foreground="red",
                font=("Helvetica", 10, "bold")
            )
            self.root.after(3000, lambda: self.links_status.config(text=""))
            return
            
        self.get_links_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.links_status.config(text="Đang lấy links...", foreground="blue")
        
        self.is_running = True
        
        def get_links_thread():
            try:
                self.product_links = self.get_amazon_product_links(url)
                
                # Kiểm tra xem có bị dừng không
                if self.is_running:
                    self.links_text.delete(1.0, tk.END)
                    for link in self.product_links:
                        self.links_text.insert(tk.END, f"{link}\n")
                    
                    self.links_status.config(
                        text=f"✅ Đã tìm thấy {len(self.product_links)} links",
                        foreground="green"
                    )
            except Exception as e:
                self.links_status.config(
                    text=f"⚠️ Lỗi: Link không hợp lệ!", 
                    foreground="red",
                    font=("Helvetica", 10, "bold")
                )
            finally:
                self.get_links_button.config(state="normal")
                self.stop_button.config(state="disabled")
                self.is_running = False
        
        threading.Thread(target=get_links_thread).start()

    def stop_get_links(self):
        self.is_running = False
        self.links_status.config(
            text="⚠️ Đã dừng lấy links", 
            foreground="orange",
            font=("Helvetica", 10, "bold")
        )
        self.get_links_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def scrape_product_info(self, url):
        max_retries = 3 
        retry_delay = 5  
        
        for attempt in range(max_retries):
            try:
                user_agent = random.choice(user_agents)
                referer = random.choice(referers)
                headers = {
                    "User-Agent": user_agent,
                    "Referer": referer,
                    "Accept-Language": "en-US,en;q=0.9",
                    "X-Forwarded-For": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
                }
                
                response = requests.get(url, headers=headers, timeout=15) 
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    if not soup.find("span", id="productTitle"):
                        print(f"Attempt {attempt + 1}: Invalid product page for {url}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            return {
                                "URL": url,
                                "Title": "Trang sản phẩm không hợp lệ",
                                "ISBN": "N/A",
                                "Author": "N/A",
                                "Language": "N/A",
                                "Book_Type": "N/A",
                                "Publication_Date": "N/A",
                                "Image": "N/A"
                            }

                    title = soup.find("span", id="productTitle")
                    title = title.get_text(strip=True) if title else "Không tìm thấy tiêu đề"
                    
                    image = soup.find("img", id="landingImage")
                    if image and 'data-a-dynamic-image' in image.attrs:
                        dynamic_images = json.loads(image['data-a-dynamic-image'])
                        image_url = max(dynamic_images.keys(), key=lambda url: dynamic_images[url][0])
                    else:
                        image_url = "Không tìm thấy ảnh"

                    subtitle = soup.find('span', id='productSubtitle')
                    book_type = 'Không tìm thấy loại sách'
                    pub_date = 'Không tìm thấy ngày xuất bản'
                    if subtitle:
                        subtitle_text = subtitle.get_text().strip()

                        if '–' in subtitle_text:
                            book_type, pub_date = subtitle_text.split('–', 1)
                            book_type = book_type.strip()
                            pub_date = pub_date.strip()

                    details = {}
                    detail_bullets = soup.find('ul', class_='detail-bullet-list')
                    if detail_bullets:
                        for item in detail_bullets.find_all('li'):
                            label = item.find('span', class_='a-text-bold')
                            value = item.find_all('span')[-1] 
                            if label and value:
                                key = label.get_text().strip().replace('‏', '').replace(':', '').replace('‎', '').strip()
                                val = value.get_text().strip()
                                details[key] = val

                    isbn = details.get('ISBN-13', details.get('ISBN', details.get('ASIN', 'Không tìm thấy ISBN')))
                    
                    author_element = soup.find('span', class_='author')
                    author = "Không tìm thấy tác giả"
                    if author_element:
                        author_text = author_element.get_text().strip()

                        if "(Author)" in author_text:
                            author = author_text.replace("(Author)", "").strip()
                        else:
                            author = author_text.strip()

                    language = details.get('Language', 'Không tìm thấy ngôn ngữ')
                    
                    if 'Paperback' in details or 'Hardcover' in details:
                        pages = details.get('Paperback', details.get('Hardcover', '')).replace('pages', '').strip()
                        if pages:
                            book_type = f"{book_type}"
                    
                    publisher_info = details.get('Publisher', '')
                    if publisher_info and '(' in publisher_info and ')' in publisher_info:
                        pub_date = publisher_info[publisher_info.find('(') + 1:publisher_info.find(')')].strip()

                    return {
                        "URL": url,
                        "Title": title,
                        "ISBN": isbn,
                        "Author": author,
                        "Language": language,
                        "Book_Type": book_type,
                        "Publication_Date": pub_date,
                        "Image": image_url
                    }
                else:
                    return {
                        "URL": url,
                        "Title": "Lỗi kết nối",
                        "ISBN": "N/A",
                        "Author": "N/A",
                        "Language": "N/A",
                        "Book_Type": "N/A",
                        "Publication_Date": "N/A",
                        "Image": "N/A"
                    }
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                return {
                    "URL": url,
                    "Title": "Lỗi xử lý",
                    "ISBN": "N/A",
                    "Author": "N/A",
                    "Language": "N/A",
                    "Book_Type": "N/A",
                    "Publication_Date": "N/A",
                    "Image": "N/A"
                }

    def start_scraping(self):
        self.scrape_button.config(state="disabled")
        self.table.delete(*self.table.get_children())
        self.scraped_data.clear()
        
        def scrape_thread():
            urls = [url.strip() for url in self.links_text.get("1.0", "end").splitlines() if url.strip()]
            total_urls = len(urls)
            processed = 0
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {executor.submit(self.scrape_product_info, url): url for url in urls}
                
                for future in future_to_url:
                    try:
                        info = future.result()
                        processed += 1
                        self.scraped_data.append(info)
                        self.root.after(0, lambda i=info: self.table.insert("", "end", values=(
                            i["URL"],
                            i["Title"], 
                            i["ISBN"], 
                            i["Author"], 
                            i["Language"], 
                            i["Book_Type"], 
                            i["Publication_Date"],
                            i["Image"]
                        )))
                        self.scrape_status.config(text=f"Đang xử lý... ({processed}/{total_urls})")
                    except Exception as e:
                        print(f"Error: {str(e)}")
            
            self.scrape_status.config(text=f"Hoàn thành! Đã xử lý {processed} sản phẩm")
            self.scrape_button.config(state="normal")
        
        threading.Thread(target=scrape_thread).start()

    def copy_to_clipboard(self):
        if not self.scraped_data:
            self.export_status.config(
                text="⚠️ Không có dữ liệu để copy!", 
                foreground="red",
                font=("Helvetica", 10, "bold")  
            )
            self.root.after(3000, lambda: self.export_status.config(text=""))
            return
        
        headers = ["URL", "Title", "ISBN", "Author", "Language", "Book_Type", "Publication_Date", "Image"]
        clipboard_text = "\t".join(headers) + "\n"
        
        for item in self.scraped_data:
            row = [str(item[field]) for field in headers]
            clipboard_text += "\t".join(row) + "\n"
        
        pyperclip.copy(clipboard_text)
        self.export_status.config(
            text="✅ Đã copy dữ liệu vào clipboard!", 
            foreground="green",
            font=("Helvetica", 10, "bold")  
        )
        self.root.after(3000, lambda: self.export_status.config(text=""))

    def export_to_csv(self):
        if not self.scraped_data:
            self.export_status.config(
                text="⚠️ Không có dữ liệu để xuất!", 
                foreground="red",
                font=("Helvetica", 10, "bold")  
            )
            self.root.after(3000, lambda: self.export_status.config(text=""))
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["URL", "Title", "ISBN", "Author", "Language", "Book_Type", "Publication_Date", "Image"])
                writer.writeheader()
                writer.writerows(self.scraped_data)
            self.export_status.config(
                text=f"✅ Đã lưu dữ liệu vào {file_path}", 
                foreground="green",
                font=("Helvetica", 10, "bold")  
            )
            self.root.after(3000, lambda: self.export_status.config(text=""))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
    ]
    
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
    ]
    
    app = AmazonScraper()
    app.run()