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
from PIL import Image, ImageTk
import os
from datetime import datetime, timedelta
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AmazonScraper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Amazon v1.0")
        self.root.resizable(True, True)
        
        # Maximize window on startup
        self.root.state('zoomed')  # For Windows
        # Fallback for Linux/Mac if 'zoomed' doesn't work
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        
        # Đảm bảo cửa sổ được tạo và có kích thước trước khi cập nhật layout
        self.root.update_idletasks()
        
        # Load background images using resource_path
        self.bg_image_left = Image.open(resource_path("anh1.png"))
        self.bg_image_right = Image.open(resource_path("anh2.png"))
        
        # Tạo frame chứa toàn bộ nội dung
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        
        # Bind sự kiện resize
        self.root.bind("<Configure>", self.on_resize)
        
        self.update_layout()
        
        self.scraped_data = []
        self.product_links = []
        
        self.create_gui()

    def update_layout(self):
        # Lấy kích thước hiện tại của cửa sổ
        self.width = max(self.root.winfo_width(), 100)  # Minimum width 100px
        self.height = max(self.root.winfo_height(), 100)  # Minimum height 100px
        
        # Tính toán kích thước cho mỗi phần
        bg_width = max(self.width // 4, 400)  # Minimum width 50px
        
        try:
            # Resize background images
            bg_left = self.bg_image_left.resize((bg_width, self.height))
            bg_right = self.bg_image_right.resize((bg_width, self.height))
            
            # Cập nhật PhotoImage
            self.bg_photo_left = ImageTk.PhotoImage(bg_left)
            self.bg_photo_right = ImageTk.PhotoImage(bg_right)
            
            # Cập nhật hoặc tạo mới labels nếu chưa tồn tại
            if not hasattr(self, 'bg_label_left'):
                self.bg_label_left = tk.Label(self.root)
                self.bg_label_right = tk.Label(self.root)
                self.main_frame = ttk.Frame(self.root)
            
            # Cập nhật background images
            self.bg_label_left.configure(image=self.bg_photo_left)
            self.bg_label_right.configure(image=self.bg_photo_right)
            
            # Cập nhật vị trí các thành phần
            self.bg_label_left.place(x=0, y=0)
            self.bg_label_right.place(x=self.width - bg_width, y=0)
            
            # Điều chỉnh kích thước phần chính giữa
            center_width = max(self.width - (2 * bg_width), 100)  # Minimum center width
            self.main_frame.place(
                x=bg_width,
                y=0,
                width=center_width,
                height=self.height
            )
        except Exception as e:
            print(f"Error in update_layout: {e}")

    def on_resize(self, event):
        # Chỉ xử lý sự kiện resize từ cửa sổ chính
        if event.widget == self.root:
            # Thêm độ trễ để tránh cập nhật quá nhiều
            self.root.after_cancel(self.resize_job) if hasattr(self, 'resize_job') else None
            self.resize_job = self.root.after(100, self.update_layout)

    def extract_date(self, text):
        # Remove publisher name and extra info before the date
        if ';' in text:
            text = text.split(';')[-1].strip()
        
        # Extract date from within parentheses if exists
        if '(' in text and ')' in text:
            date_part = text[text.find('(') + 1:text.find(')')].strip()
            
            # Remove edition information if present
            edition_keywords = ['Edition', 'édition', 'Édition', 'Auflage', 'Éditeur']
            for keyword in edition_keywords:
                if keyword in date_part:
                    date_part = date_part.split(keyword)[-1].strip()
                    
            # Clean up any leading/trailing punctuation
            date_part = date_part.strip(' ,()')
            
            # Check if the extracted part contains numbers (likely a date)
            if any(char.isdigit() for char in date_part):
                return date_part
        
        # Try to find date in the text without parentheses
        # Common French date formats
        date_patterns = [
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}',  # French
            r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',  # English
            r'\d{1,2}\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}',   # German
            r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{4}'  # Just year
        ]
        
        import re
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        
        return text.strip()
        
    def create_gui(self):
        style = ttk.Style()
        style.configure("Transparent.TFrame", background="white")
        style.configure("Title.TLabel", font=("Times new roman", 16, "bold"), padding=10)
        style.configure("Header.TLabel", font=("Times new roman", 12, "bold"))
        style.configure("Status.TLabel", font=("Times new roman", 10), foreground="blue")
        style.configure("Action.TButton", font=("Times new roman", 10, "bold"), padding=5)

        # Create main container with white background
        main_container = ttk.Frame(self.main_frame, style="Transparent.TFrame", padding="20")
        main_container.pack(expand=True, fill="both")

        # Create notebook
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tab 1: Original scraper
        scraper_tab = ttk.Frame(notebook)
        notebook.add(scraper_tab, text="Amazon Scraper")
        
        # Tab 2: Link comparison
        compare_tab = ttk.Frame(notebook)
        notebook.add(compare_tab, text="So sánh Links")
        
        # Tab 3: eBay Search (New)
        ebay_tab = ttk.Frame(notebook)
        notebook.add(ebay_tab, text="eBay Search")
        
        # Add content to tabs
        self.create_compare_tab(compare_tab)
        self.create_scraper_tab(scraper_tab)
        self.create_ebay_tab(ebay_tab)

    def create_scraper_tab(self, parent):
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=0)
        title = ttk.Label(title_frame, text="Amazon Book Scraper", style="Title.TLabel")
        title.pack(anchor="center")
        
        category_frame = ttk.LabelFrame(parent, text="Lấy links sản phẩm", padding="10")
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
        
        links_frame = ttk.LabelFrame(parent, text="Links sản phẩm", padding="10")  # Changed from main_container to parent
        links_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        text_frame = ttk.Frame(links_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.links_text = tk.Text(text_frame, height=8, width=80)
        links_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.links_text.yview)
        self.links_text.configure(yscrollcommand=links_scroll.set)
        
        self.links_text.pack(side="left", fill="both", expand=True)
        links_scroll.pack(side="right", fill="y")
        
        scrape_frame = ttk.LabelFrame(parent, text="Lấy thông tin sản phẩm", padding="10")  # Changed from main_container to parent
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
        
        table_frame = ttk.Frame(parent)  # Changed from main_container to parent
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        table_scroll_y = ttk.Scrollbar(table_frame)
        table_scroll_y.pack(side="right", fill="y")
        
        table_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        table_scroll_x.pack(side="bottom", fill="x")
        
        columns = ("URL", "Title", "ISBN-10", "ISBN-13", "Author", "Language", "Book_Type", "Publication_Date", "Image", "Price", "Reviews")
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
            "URL": 80,
            "Title": 80,
            "ISBN-10": 80,
            "ISBN-13": 80,
            "Author": 80,
            "Language": 80,
            "Book_Type": 80,
            "Publication_Date": 80,
            "Image": 80,
            "Price": 80,
            "Reviews": 80
        }
        
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=column_widths[col])
        
        # Frame cho thông báo và nút xuất dữ liệu
        export_frame = ttk.Frame(parent)
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

    def create_compare_tab(self, parent):
        # Frame for list 1
        list1_frame = ttk.LabelFrame(parent, text="Danh sách links 1", padding="10")
        list1_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Text area for list 1
        self.list1_text = tk.Text(list1_frame, height=8, width=80)
        list1_scroll = ttk.Scrollbar(list1_frame, orient="vertical", command=self.list1_text.yview)
        self.list1_text.configure(yscrollcommand=list1_scroll.set)
        self.list1_text.pack(side="left", fill="both", expand=True)
        list1_scroll.pack(side="right", fill="y")
        
        # Frame for list 2
        list2_frame = ttk.LabelFrame(parent, text="Danh sách links 2", padding="10")
        list2_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Text area for list 2
        self.list2_text = tk.Text(list2_frame, height=8, width=80)
        list2_scroll = ttk.Scrollbar(list2_frame, orient="vertical", command=self.list2_text.yview)
        self.list2_text.configure(yscrollcommand=list2_scroll.set)
        self.list2_text.pack(side="left", fill="both", expand=True)
        list2_scroll.pack(side="right", fill="y")
        
        # Compare button
        compare_button = ttk.Button(
            parent,
            text="So sánh vị trí",
            command=self.compare_links,
            style="Action.TButton"
        )
        compare_button.pack(pady=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(parent, text="Kết quả so sánh", padding="10")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Results text area
        self.results_text = tk.Text(results_frame, height=8, width=80)
        results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        self.results_text.pack(side="left", fill="both", expand=True)
        results_scroll.pack(side="right", fill="y")

    def create_ebay_tab(self, parent):
        # Main container using vertical layout
        main_container = ttk.Frame(parent, padding="5")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top section - Search inputs
        search_frame = ttk.LabelFrame(main_container, text="Search Terms", padding="5")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        input_frame = ttk.Frame(search_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Left side of search frame
        left_input = ttk.Frame(input_frame)
        left_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(left_input, text="Enter search terms (one per line):").pack(anchor='w')
        self.ebay_search_text = tk.Text(left_input, width=50, height=5)
        self.ebay_search_text.pack(fill=tk.X, pady=5)
        
        # Right side of search frame
        right_input = ttk.Frame(input_frame)
        right_input.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Label(right_input, text="Items per page:").pack()
        self.ebay_items_per_page = ttk.Combobox(right_input, values=['60', '120', '240'], width=5)
        self.ebay_items_per_page.set('60')
        self.ebay_items_per_page.pack(pady=5)
        
        # Button frame with status label
        button_frame = ttk.Frame(search_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Left side - Buttons
        button_container = ttk.Frame(button_frame)
        button_container.pack(side=tk.LEFT)
        
        # Tạo và lưu trữ tham chiếu đến các nút
        self.search_button = ttk.Button(button_container, text="Search", 
                                      command=self.start_ebay_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        self.copy_summary_button = ttk.Button(button_container, text="Copy Summary", 
                                            command=self.copy_ebay_summary)
        self.copy_summary_button.pack(side=tk.LEFT, padx=5)
        
        self.copy_details_button = ttk.Button(button_container, text="Copy Details", 
                                            command=self.copy_ebay_details)
        self.copy_details_button.pack(side=tk.LEFT, padx=5)
        
        # Right side - Status label
        self.ebay_status_label = ttk.Label(button_frame, text="", foreground="blue")
        self.ebay_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Middle section - Summary Results
        summary_frame = ttk.LabelFrame(main_container, text="Summary Results", padding="5")
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary Treeview
        self.ebay_summary_tree = ttk.Treeview(summary_frame, columns=(
            'Search Term', 'Total Results', 'Last 7 Days',
            'Date1', 'Date2', 'Date3', 'Date4', 'Date5', 'Date6', 'Date7'
        ), show='headings', height=5)
        
        # Define summary columns
        columns = {
            'Search Term': 100,
            'Total Results': 80,
            'Last 7 Days': 80,
            'Date1': 80, 'Date2': 80, 'Date3': 80, 'Date4': 80,
            'Date5': 80, 'Date6': 80, 'Date7': 80
        }
        
        for col, width in columns.items():
            self.ebay_summary_tree.heading(col, text=col)
            self.ebay_summary_tree.column(col, width=width, anchor='center')
        
        # Add scrollbars to summary tree
        summary_scroll_y = ttk.Scrollbar(summary_frame, orient="vertical", command=self.ebay_summary_tree.yview)
        summary_scroll_x = ttk.Scrollbar(summary_frame, orient="horizontal", command=self.ebay_summary_tree.xview)
        self.ebay_summary_tree.configure(yscrollcommand=summary_scroll_y.set, xscrollcommand=summary_scroll_x.set)
        
        summary_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.ebay_summary_tree.pack(fill=tk.BOTH, expand=True)
        summary_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bottom section - Item Details
        details_frame = ttk.LabelFrame(main_container, text="Item Details", padding="5")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Details header
        details_header = ttk.Frame(details_frame)
        details_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(details_header, text="Selected Term: ").pack(side=tk.LEFT)
        self.ebay_selected_term_var = tk.StringVar(value="All Terms")
        ttk.Label(details_header, textvariable=self.ebay_selected_term_var).pack(side=tk.LEFT)
        ttk.Button(details_header, text="Show All Items", 
                  command=self.show_all_ebay_terms).pack(side=tk.RIGHT)
        
        # Details Treeview
        self.ebay_details_tree = ttk.Treeview(details_frame, columns=(
            'Search Term', 'Title', 'Price', 'Sold Date'
        ), show='headings', height=10)
        
        detail_columns = {
            'Search Term': 150,
            'Title': 400,
            'Price': 100,
            'Sold Date': 150
        }
        
        for col, width in detail_columns.items():
            self.ebay_details_tree.heading(col, text=col)
            self.ebay_details_tree.column(col, width=width, anchor='w')
        
        # Add scrollbars to details tree
        details_scroll_y = ttk.Scrollbar(details_frame, orient="vertical", command=self.ebay_details_tree.yview)
        details_scroll_x = ttk.Scrollbar(details_frame, orient="horizontal", command=self.ebay_details_tree.xview)
        self.ebay_details_tree.configure(yscrollcommand=details_scroll_y.set, xscrollcommand=details_scroll_x.set)
        
        details_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.ebay_details_tree.pack(fill=tk.BOTH, expand=True)
        details_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Store results
        self.ebay_all_details_results = []
        
        # Add event bindings
        self.ebay_summary_tree.bind('<<TreeviewSelect>>', self.on_ebay_summary_select)
        self.ebay_summary_tree.bind('<Double-1>', self.on_ebay_summary_select)
        self.ebay_summary_tree.bind('<Button-1>', self.on_ebay_single_click)

    def compare_links(self):
        # Get links from both text areas
        links1 = [link.strip() for link in self.list1_text.get("1.0", "end").splitlines() if link.strip()]
        links2 = [link.strip() for link in self.list2_text.get("1.0", "end").splitlines() if link.strip()]
        
        # Clear previous results
        self.results_text.delete("1.0", "end")
        
        # Find position changes
        changes = []
        for link in links1:
            if link in links2:
                pos1 = links1.index(link) + 1
                pos2 = links2.index(link) + 1
                if pos1 != pos2:
                    changes.append(f"Link: {link}\nVị trí cũ: {pos1}\nVị trí mới: {pos2}\n")
        
        # Find missing links
        missing_in_2 = [link for link in links1 if link not in links2]
        missing_in_1 = [link for link in links2 if link not in links1]
        
        # Display results
        if changes:
            self.results_text.insert("end", "=== Links thay đổi vị trí ===\n\n")
            for change in changes:
                self.results_text.insert("end", f"{change}\n")
        
        if missing_in_2:
            self.results_text.insert("end", "=== Links bị xóa (có trong DS1, không có trong DS2) ===\n\n")
            for link in missing_in_2:
                pos = links1.index(link) + 1
                self.results_text.insert("end", f"Link: {link}\nVị trí cũ: {pos}\n\n")
        
        if missing_in_1:
            self.results_text.insert("end", "=== Links mới thêm (có trong DS2, không có trong DS1) ===\n\n")
            for link in missing_in_1:
                pos = links2.index(link) + 1
                self.results_text.insert("end", f"Link: {link}\nVị trí mới: {pos}\n\n")
        
        if not changes and not missing_in_1 and not missing_in_2:
            self.results_text.insert("end", "Không có thay đổi nào giữa hai danh sách!")

    def get_amazon_product_links(self, url):
        if not self.is_running:
            return []
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--start-maximized')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        all_links = []
        
        def smooth_scroll(driver, start, end, steps=10, delay=0.2):
            height = end - start
            step_size = height / steps
            for i in range(steps):
                current = start + (step_size * (i + 1))
                driver.execute_script(f"window.scrollTo(0, {current});")
                time.sleep(delay)

        try:
            # Process page 1
            driver.set_window_position(0, 0)
            driver.set_window_size(1920, 1080)
            driver.get(url)
            time.sleep(2)

            # Handle CAPTCHA for page 1
            max_captcha_retries = 3
            captcha_retry_count = 0

            while captcha_retry_count < max_captcha_retries:
                if "captcha" in driver.page_source.lower():
                    captcha_retry_count += 1
                    self.links_status.config(
                        text=f"⚠️ Phát hiện CAPTCHA! Đang thử lại lần {captcha_retry_count}...", 
                        foreground="orange",
                        font=("Helvetica", 10, "bold")
                    )
                    time.sleep(3)
                    driver.refresh()
                    continue
                break

            if captcha_retry_count >= max_captcha_retries:
                self.links_status.config(
                    text="⚠️ Không thể vượt qua CAPTCHA sau nhiều lần thử!", 
                    foreground="red",
                    font=("Helvetica", 10, "bold")
                )
                time.sleep(300)
                return []

            # Process both pages
            for page in range(1, 3):
                self.links_status.config(
                    text=f"Đang lấy links từ trang {page}...",
                    foreground="blue"
                )

                found_rhf = False
                max_attempts = 5
                attempts = 0

                while not found_rhf and attempts < max_attempts and self.is_running:
                    total_height = driver.execute_script("return document.body.scrollHeight;")
                    sections = [
                        (0, total_height * 0.3),
                        (total_height * 0.3, total_height * 0.6),
                        (total_height * 0.6, total_height)
                    ]
                    
                    for start, end in sections:
                        smooth_scroll(driver, start, end)
                        time.sleep(1)
                    
                    driver.execute_script(f"window.scrollTo(0, {total_height * 0.9});")
                    time.sleep(0.5)
                    driver.execute_script(f"window.scrollTo(0, {total_height});")
                    time.sleep(1)

                    try:
                        rhf_element = driver.find_element(By.ID, "navFooter")
                        if rhf_element:
                            found_rhf = True
                            time.sleep(3)
                    except:
                        pass
                    
                    attempts += 1

                if not self.is_running:
                    return []
                if not found_rhf:
                    self.links_status.config(text=f"Không tìm thấy sản phẩm trên trang {page}")
                    continue

                # Extract links from current page
                try:
                    zg_element = driver.find_element(By.ID, "zg")
                    elements = zg_element.find_elements(By.CSS_SELECTOR, "a[href*='/dp/'], a[href*='/gp/product/']")
                    
                    for element in elements:
                        if not self.is_running:
                            return []
                        href = element.get_attribute('href')
                        if href:
                            clean_url = re.sub(r'/ref=.*', '', href)
                            if clean_url not in all_links:
                                all_links.append(clean_url)
                except Exception as e:
                    print(f"Error extracting links: {e}")

                # If this is page 1, try to navigate to page 2
                if page == 1:
                    try:
                        # Try different selectors for the "Next" button
                        next_button = None
                        selectors = [
                            "li.a-last a",  # Common selector
                            "a.s-pagination-next",  # Alternative selector
                            "a[href*='page=2']",  # Direct page 2 link
                            "span.s-pagination-strip a:last-child",  # Last pagination link
                            "a[aria-label='Next page']"  # Aria-label selector
                        ]
                        
                        for selector in selectors:
                            try:
                                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                                if next_button:
                                    break
                            except:
                                continue
                        
                        if next_button:
                            # Scroll to the button and click it
                            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(1)
                            next_button.click()
                            time.sleep(3)  # Wait for page 2 to load
                        else:
                            # If no next button found, try to modify URL directly
                            current_url = driver.current_url
                            if "?" in current_url:
                                page2_url = f"{current_url}&page=2"
                            else:
                                page2_url = f"{current_url}?page=2"
                            driver.get(page2_url)
                            time.sleep(3)
                            
                    except Exception as e:
                        print(f"Error navigating to page 2: {e}")
                        self.links_status.config(
                            text="⚠️ Không thể chuyển sang trang 2",
                            foreground="orange"
                        )
                        break

            return all_links

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
                print(e)
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
                    
                    reviews_count = "N/A"
                    try:
                        # Try to find the review count from the customer review link
                        review_element = soup.find('span', id='acrCustomerReviewText')
                        if review_element:
                            # Extract just the number from text like "2 évaluations" or "2 ratings"
                            review_text = review_element.get_text(strip=True)
                            # Extract first number from the text
                            number = ''.join(filter(str.isdigit, review_text))
                            if number:
                                reviews_count = number
                    except Exception as e:
                        print(f"Error extracting reviews: {str(e)}")
                        reviews_count = "N/A"

                    if not soup.find("span", id="productTitle"):
                        print(f"Attempt {attempt + 1}: Invalid product page for {url}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            return {
                                "URL": url,
                                "Title": "Trang sản phẩm không hợp lệ",
                                "ISBN-10": "N/A",
                                "ISBN-13": "N/A",
                                "Author": "N/A",
                                "Language": "N/A",
                                "Book_Type": "N/A",
                                "Publication_Date": "N/A",
                                "Image": "N/A",
                                "Price": "N/A",
                                "Reviews": "N/A"
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

                    isbn10 = details.get('ISBN-10', 'N/A')
                    isbn13 = details.get('ISBN-13', 'N/A')
                    
                    author_element = soup.find('span', class_='author')
                    author = "Không tìm thấy tác giả"
                    if author_element:
                        author = ' '.join(author_element.get_text().split())
                        patterns_to_remove = [
                            "(Author)",
                            "(Author),",
                            "(Author, Illustrator)",
                            "(Auteur)",
                            "(Autor)",
                            "(Herausgeber, Autor)",
                            "(Illustrations)",
                            "(Auteur Illustrations)",
                            "(Auteur Dessins Rédacteur)",
                            "(Avec la contribution de)",
                            "(Avec la contribution de Dessins)",
                            "(Auteur Dessins)",
                        ]

                        for pattern in patterns_to_remove:
                            author = author.replace(pattern, "")
                        
                        # Xóa dấu phẩy và khoảng trắng thừa
                        author = author.replace(",", "").strip()

                    language = 'N/A'
                    language_keys = ['Language', 'Langue', 'Sprache', 'Idioma', 'Lingua']
                    for key in language_keys:
                        if key in details:
                            language = details[key]
                            break
                            
                    # Try alternative location if language is still not found
                    if language == 'N/A':
                        language_elem = soup.find('div', {'id': 'language'})
                        if language_elem:
                            language = language_elem.get_text().strip()
                            
                    # Try another alternative location
                    if language == 'N/A':
                        language_elem = soup.find('td', {'class': 'a-size-base', 'data-attribute': 'language'})
                        if language_elem:
                            language = language_elem.get_text().strip()
                    
                    
                    if 'Paperback' in details or 'Hardcover' in details:
                        pages = details.get('Paperback', details.get('Hardcover', '')).replace('pages', '').strip()
                        if pages:
                            book_type = f"{book_type}"
                    
                    pub_date = 'N/A'
                    publisher_info = details.get('Éditeur', details.get('Publisher', ''))
                    if publisher_info:
                        if '(' in publisher_info and ')' in publisher_info:
                            date_part = publisher_info[publisher_info.find('(') + 1:publisher_info.find(')')].strip()
                            if any(char.isdigit() for char in date_part):
                                pub_date = date_part

                    if pub_date == 'N/A':
                        detail_text = ' '.join([span.get_text() for span in soup.find_all('span')])
                        pub_date = self.extract_date(detail_text)

                    if pub_date == 'N/A':
                        detail_bullets = soup.find('ul', class_='detail-bullet-list')
                        if detail_bullets:
                            for item in detail_bullets.find_all('li'):
                                label = item.find('span', class_='a-text-bold')
                                if label and ('Publisher' in label.get_text() or 'Éditeur' in label.get_text()):
                                    value_span = item.find_all('span')[-1]
                                    if value_span:
                                        pub_date = self.extract_date(value_span.get_text().strip())
                                        if pub_date != 'N/A' and any(char.isdigit() for char in pub_date):
                                            break
                   

                    price = "N/A"
                    try:
                        formats_div = soup.find('div', id='formats')
                        if formats_div:
                            # Try to find Hardcover price first
                            hardcover = formats_div.find('div', id='tmm-grid-swatch-HARDCOVER')
                            if hardcover:
                                price_text = hardcover.find('span', class_='slot-price').get_text().strip()
                                if any(x in price_text.lower() for x in ['from', 'ab', 'à partir de']):
                                    # Extract price after currency symbol ($ or € or EUR)
                                    price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')
                                else:
                                    price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')
                            
                            # If no Hardcover price, try Kindle price
                            if price == "N/A":
                                kindle = formats_div.find('div', id='tmm-grid-swatch-KINDLE')
                                if kindle:
                                    price_elem = kindle.find('span', class_='ebook-price-value')
                                    if price_elem:
                                        price = ''.join(c for c in price_elem.get_text().strip() if c.isdigit() or c == ',' or c == '.')

                            # If no Kindle price, try Paperback price
                            if price == "N/A":
                                paperback = formats_div.find('div', id='tmm-grid-swatch-PAPERBACK')
                                if paperback:
                                    price_text = paperback.find('span', class_='slot-price').get_text().strip()
                                    if price_text and price_text != "—":
                                        if any(x in price_text.lower() for x in ['from', 'ab', 'à partir de']):
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')
                                        else:
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')

                            # If no Paperback price, try Mass Market Paperback (Poche) price
                            if price == "N/A":
                                mass_market = formats_div.find('div', id='tmm-grid-swatch-MASS_MARKET_PAPERBACK')
                                if mass_market:
                                    price_text = mass_market.find('span', class_='slot-price').get_text().strip()
                                    if price_text and price_text != "—":
                                        if any(x in price_text.lower() for x in ['from', 'ab', 'à partir de']):
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')
                                        else:
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')

                            # If no Paperback price, try Magazine price
                            if price == "N/A":
                                magazine = formats_div.find('div', id='tmm-grid-swatch-OTHER')
                                if magazine:
                                    price_text = magazine.find('span', class_='slot-price').get_text().strip()
                                    if price_text and price_text != "—":
                                        if any(x in price_text.lower() for x in ['from', 'ab', 'à partir de']):
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')
                                        else:
                                            price = ''.join(c for c in price_text if c.isdigit() or c == ',' or c == '.')

                        # Validate and format price
                        if price != "N/A":
                            # Convert European format (comma decimal) to US format (dot decimal)
                            price = price.replace(',', '.')
                            
                            # If multiple dots exist, keep only the last one
                            if price.count('.') > 1:
                                parts = price.split('.')
                                price = ''.join(parts[:-1]) + '.' + parts[-1]
                            
                            try:
                                price_float = float(price)
                                if price_float <= 0:
                                    price = "N/A"
                                else:
                                    # Check URL to determine currency symbol
                                    if ".fr" in url or ".de" in url:
                                        price = f"€{price_float:.2f}"
                                    else:
                                        price = f"${price_float:.2f}"
                            except ValueError:
                                price = "N/A"

                    except Exception as e:
                        print(f"Error extracting price: {str(e)}")
                        price = "N/A"
                    
                    
                    return {
                        "URL": url,
                        "Title": title,
                        "ISBN-10": isbn10,
                        "ISBN-13": isbn13,
                        "Author": author,
                        "Language": language,
                        "Book_Type": book_type,
                        "Publication_Date": pub_date,
                        "Image": image_url,
                        "Price": price,
                        "Reviews": reviews_count
                    }
                else:
                    return {
                        "URL": url,
                        "Title": "Lỗi kết nối",
                        "ISBN-10": "N/A",
                        "ISBN-13": "N/A",
                        "Author": "N/A",
                        "Language": "N/A",
                        "Book_Type": "N/A",
                        "Publication_Date": "N/A",
                        "Image": "N/A",
                        "Price": "N/A",
                        "Reviews": "N/A"
                    }
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                return {
                    "URL": url,
                    "Title": "Lỗi xử lý",
                    "ISBN-10": "N/A",
                    "ISBN-13": "N/A",
                    "Author": "N/A",
                    "Language": "N/A",
                    "Book_Type": "N/A",
                    "Publication_Date": "N/A",
                    "Image": "N/A",
                    "Price": "N/A",
                    "Reviews": "N/A"
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
                            i["ISBN-10"],
                            i["ISBN-13"], 
                            i["Author"], 
                            i["Language"], 
                            i["Book_Type"], 
                            i["Publication_Date"],
                            i["Image"],
                            i["Price"],
                            i["Reviews"]
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
        
        headers = ["URL", "Title", "ISBN-10", "ISBN-13", "Author", "Language", "Book_Type", "Publication_Date", "Image", "Price", "Reviews"]
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
                writer = csv.DictWriter(file, fieldnames=["URL", "Title", "ISBN-10", "ISBN-13", "Author", "Language", "Book_Type", "Publication_Date", "Image", "Price", "Reviews"])
                writer.writeheader()
                writer.writerows(self.scraped_data)
            self.export_status.config(
                text=f"✅ Đã lưu dữ liệu vào {file_path}", 
                foreground="green",
                font=("Helvetica", 10, "bold")  
            )
            self.root.after(3000, lambda: self.export_status.config(text=""))

    def start_ebay_search(self):
        # Clear previous results
        for tree in [self.ebay_summary_tree, self.ebay_details_tree]:
            for item in tree.get_children():
                tree.delete(item)
        
        search_terms = self.ebay_search_text.get("1.0", tk.END).strip().split('\n')
        search_terms = [term.strip() for term in search_terms if term.strip()]
        
        if not search_terms:
            self.ebay_status_label.config(
                text="⚠️ Please enter at least one search term",
                foreground="red"
            )
            self.root.after(3000, lambda: self.ebay_status_label.config(text=""))
            return
        
        self.search_button.config(state="disabled")
        self.ebay_status_label.config(text="🔍 Searching...", foreground="blue")
        threading.Thread(target=self.perform_multiple_searches, args=(search_terms,), daemon=True).start()

    def perform_multiple_searches(self, search_terms):
        items_per_page = self.ebay_items_per_page.get()
        summary_results = []
        details_results = []
        date_set = set()
        
        for term in search_terms:
            url = create_ebay_url(term, items_per_page)
            book_data = get_ebay_book_titles(url)
            
            # Collect all sold dates
            latest_date = None
            for item in book_data:
                if 'sold_date' in item:
                    try:
                        sold_date = self.parse_sold_date(item['sold_date'])
                        if sold_date:
                            date_set.add(sold_date)
                            # Update latest_date if this date is more recent
                            if latest_date is None or sold_date > latest_date:
                                latest_date = sold_date
                    except:
                        continue
            
            if latest_date:
                # Generate 7 consecutive dates starting from the latest date
                dates_to_track = []
                for i in range(7):
                    current_date = latest_date - timedelta(days=i)
                    dates_to_track.append(current_date)
                
                # Sort dates in reverse chronological order (newest first)
                dates_to_track.sort(reverse=True)
                
                # Update column headers with the dates
                for i, date in enumerate(dates_to_track, 1):
                    self.ebay_summary_tree.heading(f'Date{i}', text=date.strftime('%m/%d'))
                
                # Calculate daily counts
                daily_counts = {date: 0 for date in dates_to_track}
                for item in book_data:
                    if 'sold_date' in item:
                        try:
                            sold_date = self.parse_sold_date(item['sold_date'])
                            if sold_date in daily_counts:
                                daily_counts[sold_date] += 1
                        except:
                            continue
                
                # Prepare summary results
                total_results = len(book_data)
                last_7_days = sum(daily_counts.values())
                daily_breakdown = [str(daily_counts.get(date, 0)) for date in dates_to_track]
                
                summary_results.append([term, total_results, last_7_days] + daily_breakdown)
                
                # Add details for each item
                for item in book_data:
                    details_results.append([
                        term,
                        item.get('title', 'N/A'),
                        item.get('price', 'N/A'),
                        item.get('sold_date', 'N/A')
                    ])
        
        self.root.after(0, self.display_ebay_results, summary_results, details_results)

    def parse_sold_date(self, sold_text):
        try:
            sold_text = sold_text.lower()
            if 'sold' in sold_text:
                sold_text = sold_text.replace('sold', '').strip()
            
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            month = None
            for month_name, month_num in month_map.items():
                if month_name in sold_text:
                    month = month_num
                    break
            
            if month is None:
                return None
            
            match = re.search(r'(\d+),?\s*(\d{4})?', sold_text)
            if match:
                day = int(match.group(1))
                year = int(match.group(2)) if match.group(2) else datetime.now().year
                return datetime(year, month, day).date()
            
            return None
            
        except (ValueError, AttributeError):
            return None

    def display_ebay_results(self, summary_results, details_results):
        # Clear previous results
        for tree in [self.ebay_summary_tree, self.ebay_details_tree]:
            for item in tree.get_children():
                tree.delete(item)
        
        # Store all details results
        self.ebay_all_details_results = details_results
        
        # Display summary results
        for result in summary_results:
            self.ebay_summary_tree.insert('', 'end', values=result)
        
        # Display all details initially
        for result in details_results:
            self.ebay_details_tree.insert('', 'end', values=result)
        
        self.ebay_selected_term_var.set("All Terms")
        
        # Update status label
        total_items = len(details_results)
        self.ebay_status_label.config(
            text=f"✅ Found {total_items} items across {len(summary_results)} search terms",
            foreground="green"
        )
        self.search_button.config(state="normal")
        # self.root.after(5000, lambda: self.ebay_status_label.config(text=""))

    def copy_ebay_summary(self):
        self._copy_ebay_tree_data(self.ebay_summary_tree)
        self.ebay_status_label.config(text="✅ Summary copied to clipboard!", foreground="green")
        # self.root.after(3000, lambda: self.ebay_status_label.config(text=""))

    def copy_ebay_details(self):
        self._copy_ebay_tree_data(self.ebay_details_tree)
        self.ebay_status_label.config(text="✅ Details copied to clipboard!", foreground="green")
        # self.root.after(3000, lambda: self.ebay_status_label.config(text=""))

    def _copy_ebay_tree_data(self, tree):
        lines = []
        # Add header
        headers = [tree.heading(col)['text'] for col in tree.cget('columns')]
        lines.append('\t'.join(headers))
        
        # Add data
        for item_id in tree.get_children():
            values = tree.item(item_id)['values']
            lines.append('\t'.join(map(str, values)))
        
        # Copy to clipboard
        result_text = '\n'.join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(result_text)

    def on_ebay_single_click(self, event):
        self.last_click_time = event.time

    def on_ebay_summary_select(self, event):
        if hasattr(self, 'last_click_time') and event.time - self.last_click_time > 300:
            return
            
        selection = self.ebay_summary_tree.selection()
        if selection:
            item = self.ebay_summary_tree.item(selection[0])
            selected_term = item['values'][0]
            
            self.ebay_selected_term_var.set(selected_term)
            
            for item in self.ebay_details_tree.get_children():
                self.ebay_details_tree.delete(item)
            
            filtered_details = [
                result for result in self.ebay_all_details_results 
                if result[0] == selected_term
            ]
            
            for result in filtered_details:
                self.ebay_details_tree.insert('', 'end', values=result)

    def show_all_ebay_terms(self):
        for item in self.ebay_details_tree.get_children():
            self.ebay_details_tree.delete(item)
        
        for result in self.ebay_all_details_results:
            self.ebay_details_tree.insert('', 'end', values=result)
        
        self.ebay_summary_tree.selection_remove(self.ebay_summary_tree.selection())
        self.ebay_selected_term_var.set("All Terms")

    def run(self):
        self.root.mainloop()

def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

def get_ebay_book_titles(url):
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
        'Referer': random.choice(referers),
        'X-Forwarded-For': get_random_ip()
    }
    
    try:
        time.sleep(random.uniform(2, 5))
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        item_count = 0
        
        item_containers = soup.find_all('div', class_='s-item__info')
        
        for container in item_containers:
            item_data = {}
            
            title_element = container.find(['div', 'span', 'h3'], 
                                      class_=['s-item__title', 's-item__title--has-tags'])
            if title_element and 'Shop on eBay' not in title_element.text:
                item_data['title'] = title_element.text.strip()
            
            positive_element = container.find('span', class_='s-item__caption--signal')
            if positive_element:
                sold_date = positive_element.find('span')
                if sold_date:
                    item_data['sold_date'] = sold_date.text.strip()
            
            if item_count < 5:
                price_element = container.find('span', class_='s-item__price')
                if price_element:
                    price_span = price_element.find('span', class_='POSITIVE')
                    if price_span:
                        item_data['price'] = price_span.text.strip()
            
            if item_data.get('title'):
                items.append(item_data)
                item_count += 1
        
        return items
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def create_ebay_url(search_term, items_per_page='60'):
    search_term = search_term.replace(' ', '+')
    base_url = "https://www.ebay.com/sch/i.html"
    params = {
        '_from': 'R40',
        '_nkw': search_term,
        '_sacat': '0',
        'rt': 'nc',
        'LH_Complete': '1',
        'LH_Sold': '1',
        '_fcid': '1',
        '_ipg': items_per_page
    }
    
    url_parts = []
    for key, value in params.items():
        url_parts.append(f"{key}={value}")
    
    return f"{base_url}?{'&'.join(url_parts)}"

class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Login")
        self.root.resizable(False, False)
        
        # Căn giữa cửa sổ
        window_width = 300
        window_height = 168
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Container chính
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Label tiêu đề
        ttk.Label(
            main_frame, 
            text="Enter Password", 
            font=("Times New Roman", 14, "bold")
        ).pack(pady=(0, 5))
        
        # Frame cho password
        pwd_frame = ttk.Frame(main_frame)
        pwd_frame.pack(fill="x", pady=5)
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            pwd_frame, 
            textvariable=self.password_var, 
            show="*",
            width=30
        )
        self.password_entry.pack(side="left", padx=(0, 5))
        
        # Nút show/hide password
        self.show_pwd = tk.BooleanVar()
        self.show_button = ttk.Checkbutton(
            pwd_frame,
            text="Show",
            variable=self.show_pwd,
            command=self.toggle_password_visibility
        )
        self.show_button.pack(side="left")
        
        # Label thông báo
        self.message_label = ttk.Label(
            main_frame, 
            text="", 
            foreground="red",
            font=("Times New Roman", 10)
        )
        self.message_label.pack(pady=5)
        
        # Nút Login
        ttk.Button(
            main_frame, 
            text="Login",
            command=self.verify_password
        ).pack(pady=5)
        
        # Bind Enter key
        self.password_entry.bind('<Return>', lambda e: self.verify_password())
        
        # Focus vào ô password
        self.password_entry.focus()
        
        self.correct_password = "12356"  # Thay đổi mật khẩu tại đây
        self.login_successful = False

    def toggle_password_visibility(self):
        if self.show_pwd.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def verify_password(self):
        if self.password_var.get() == self.correct_password:
            self.login_successful = True
            self.root.destroy()
        else:
            self.message_label.config(text="Incorrect password!")
            self.password_var.set("")
            self.password_entry.focus()

    def run(self):
        self.root.mainloop()
        return self.login_successful

# Sửa lại hàm main để thêm xác thực đăng nhập
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
    
    # Hiển thị cửa sổ đăng nhập
    login_window = LoginWindow()
    if login_window.run():
        # Nếu đăng nhập thành công, khởi chạy ứng dụng chính
        app = AmazonScraper()
        app.run()