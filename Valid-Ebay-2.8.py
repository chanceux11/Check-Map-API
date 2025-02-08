import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import time
import random
import re
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import concurrent.futures
import queue
import asyncio
import aiohttp

class EbayEmailChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Ebay Email Checker")
        self.root.geometry("1000x800")
        
        # Configure modern style
        style = ttk.Style()
        style.configure('Modern.TLabel', padding=5, font=('Segoe UI', 10))
        style.configure('Modern.TEntry', padding=5)
        style.configure('Modern.TButton', padding=8, font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        
        # Create main container with padding
        container = ttk.Frame(root, padding="20")
        container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive layout
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        container.columnconfigure(0, weight=2)  # Left panel takes 2 parts
        container.columnconfigure(1, weight=3)  # Right panel takes 3 parts
        container.rowconfigure(1, weight=1)     # Main content area expands
        
        # Header
        header_frame = ttk.Frame(container)
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        header_frame.columnconfigure(1, weight=1)  # Space between title and button expands
        
        ttk.Label(header_frame, text="Ebay Email Checker", 
                 font=('Segoe UI', 16, 'bold')).grid(row=0, column=0, sticky=tk.W)
        
        # Left panel for inputs
        left_panel = ttk.Frame(container)
        left_panel.grid(row=1, column=0, padx=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)  # Email list expands vertically
        
        # Email list section
        ttk.Label(left_panel, text="Email List", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.email_list_text = tk.Text(left_panel)
        self.email_list_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add radio buttons for connection type selection
        connection_frame = ttk.Frame(left_panel)
        connection_frame.grid(row=4, column=0, sticky=tk.W, pady=(15, 5))

        ttk.Label(connection_frame, text="Connection Type:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W)

        self.connection_type = tk.StringVar(value="direct")
        ttk.Radiobutton(connection_frame, text="Direct", variable=self.connection_type, value="direct").grid(row=0, column=1, padx=10)
        ttk.Radiobutton(connection_frame, text="SOCKS", variable=self.connection_type, value="socks").grid(row=0, column=2, padx=10)
        ttk.Radiobutton(connection_frame, text="ScraperAPI", variable=self.connection_type, value="scraper").grid(row=0, column=3, padx=10)

        # Socks5 Proxy List section (moved after connection type selection)
        ttk.Label(left_panel, text="Socks5 Proxy List (IP:PORT or IP:PORT:USER:PASS)", style='Header.TLabel').grid(row=5, column=0, sticky=tk.W, pady=(15, 5))
        self.proxy_list_text = tk.Text(left_panel, height=10)
        self.proxy_list_text.grid(row=6, column=0, sticky=(tk.W, tk.E))
        
        # API Keys section
        ttk.Label(left_panel, text="API Keys (one per line)", style='Header.TLabel').grid(row=7, column=0, sticky=tk.W, pady=(15, 5))
        self.api_keys_text = tk.Text(left_panel, height=10)
        self.api_keys_text.grid(row=8, column=0, sticky=(tk.W, tk.E))
        
        # Right panel for results
        right_panel = ttk.Frame(container)
        right_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)  # Results frame expands
        right_panel.rowconfigure(1, weight=1)  # Log frame expands
        
        # Results section
        results_frame = ttk.LabelFrame(right_panel, text="Results", padding=10)
        results_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        results_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(1, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        # Existing emails
        ttk.Label(results_frame, text="Existing Emails", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.existing_emails = tk.Text(results_frame)
        self.existing_emails.grid(row=1, column=0, padx=(0, 5), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Available emails
        ttk.Label(results_frame, text="Available Emails", style='Header.TLabel').grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        self.available_emails = tk.Text(results_frame)
        self.available_emails.grid(row=1, column=1, padx=(5, 0), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status log
        log_frame = ttk.LabelFrame(right_panel, text="Status Log", padding=10)
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(20, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.result_text = tk.Text(log_frame)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.result_text.config(state='disabled')
        
        # Bottom buttons
        button_frame = ttk.Frame(container)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E))
        button_frame.columnconfigure(2, weight=1)  # Space after buttons expands
        
        self.check_button = ttk.Button(button_frame, text="Check Emails", 
                                     style='Modern.TButton',
                                     command=self.check_email_list_threaded)
        self.check_button.grid(row=0, column=0, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear All", 
                                     style='Modern.TButton',
                                     command=self.clear_fields)
        self.clear_button.grid(row=0, column=1, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Check", 
                                    style='Modern.TButton',
                                    command=self.stop_checking,
                                    state='disabled')  # Initially disabled
        self.stop_button.grid(row=0, column=2, padx=5)
        
        self.check_credits_button = ttk.Button(button_frame, text="Check Credits", 
                                             style='Modern.TButton',
                                             command=self.check_all_credits)
        self.check_credits_button.grid(row=0, column=3, padx=5)
        
        # Initialize hidden attributes for cookie and token
        self.cookie_string = ""
        self.srt_token = ""
        
        # Initialize other attributes
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
        self.max_workers = 1
        self.request_delay = 0.2
        self.batch_size = 5
        self.queue = queue.Queue()
        self.results = {"existing": [], "available": []}
        self.stop_flag = threading.Event()
        self.token_lock = threading.Lock()
        self.refresh_in_progress = threading.Event()
        self.refresh_completed = threading.Event()
        self.driver = None
        self.loop = None
        self.update_id = None
        self.loop_ready = threading.Event()
        self.is_checking = False
        self.stop_requested = False
        self.referers = [
            "https://www.ebay.com/",
            "https://signup.ebay.com/pa/crte",
            "https://www.ebay.com/signin/",
            "https://reg.ebay.com/reg/PartialReg",
            "https://www.google.com/",
            "https://www.bing.com/search?q=ebay+signup",
            "https://duckduckgo.com/"
        ]
        self.current_api_key = None
        self.api_keys = []
        self.api_credits = {}
        
        # Add file handlers for real-time saving
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.existing_file = None
        self.available_file = None

        # Initialize proxy-related attributes
        self.proxy_list = []
        self.current_proxy_index = 0

    def get_token_threaded(self):
        """Run get_token in a separate thread"""
        threading.Thread(target=self.get_token, daemon=True).start()

    def check_email_list_threaded(self):
        """Start email checking in a non-blocking way"""
        try:
            self.check_button.config(state='disabled')
            self.stop_button.config(state='normal')  # Enable stop button
            self.stop_requested = False
            self.is_checking = True
            
            # Start or restart async loop
            if not self.loop or not self.loop.is_running():
                self.stop_async_loop()
                self.start_async_loop()
            
            if self.loop and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.check_email_list(), self.loop)
                
                def done_callback(fut):
                    try:
                        fut.result()
                    except Exception as e:
                        self.queue.put({'type': 'log', 'text': f"Error in async task: {str(e)}"})
                    finally:
                        self.queue.put({'type': 'log', 'text': "Finished checking emails!"})
                        self.is_checking = False
                        self.stop_requested = False
                        self.root.after(0, self.enable_buttons)
                        
                future.add_done_callback(done_callback)
            else:
                self.queue.put({'type': 'log', 'text': "Failed to start async loop"})
                self.enable_buttons()
                return
            
            if not self.update_id:
                self.update_gui()
                
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error starting check: {str(e)}"})
            self.enable_buttons()

    def start_async_loop(self):
        """Start the async event loop in a separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop_ready.set()  # Signal that loop is ready
            self.loop.run_forever()
            
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        
        # Wait for loop to be ready
        self.loop_ready.wait()
        
    def stop_async_loop(self):
        """Stop the async event loop"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None
            self.loop_ready.clear()
            
    def update_gui(self):
        """Update GUI with queued messages"""
        try:
            while True:
                try:
                    msg = self.queue.get_nowait()
                    if isinstance(msg, dict):
                        if msg.get('type') == 'existing':
                            self.existing_emails.insert(tk.END, f"{msg['email']}\n")
                        elif msg.get('type') == 'available':
                            self.available_emails.insert(tk.END, f"{msg['email']}\n")
                        elif msg.get('type') == 'log':
                            self.result_text.config(state='normal')
                            self.result_text.insert(tk.END, f"{msg['text']}\n")
                            self.result_text.see(tk.END)
                            self.result_text.config(state='disabled')
                    else:
                        self.result_text.config(state='normal')
                        self.result_text.insert(tk.END, f"{str(msg)}\n")
                        self.result_text.see(tk.END)
                        self.result_text.config(state='disabled')
                        
                        if msg == "Finished checking all emails!":
                            self.enable_buttons()
                            
                except queue.Empty:
                    break
                    
        finally:
            # Schedule next update
            self.update_id = self.root.after(100, self.update_gui)
            
    def enable_buttons(self):
        """Enable buttons after processing"""
        # self.root.after(0, lambda: self.get_token_button.config(state='normal'))
        self.root.after(0, lambda: self.check_button.config(state='normal'))
        self.root.after(0, lambda: self.stop_button.config(state='disabled'))
        
    def __del__(self):
        """Cleanup when the application closes"""
        try:
            self.stop_async_loop()
            if self.update_id:
                self.root.after_cancel(self.update_id)
        except:
            pass

    def get_token(self):
        """Get cookie and SRT token using Selenium"""
        driver = None
        try:
            self.queue.put({'type': 'log', 'text': "Getting cookie and token..."})
            
            # Configure Chrome Options
            chrome_options = Options()
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            # Add headless mode options
            chrome_options.add_argument("--headless=new")  # New headless mode for newer Chrome versions
            # chrome_options.add_argument("--window-size=1920,1080")  # Set window size
            # chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add extensions
            chrome_options.add_extension("0.2.1_0.crx")
            
            # Enable logging performance logs
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Initialize ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # First open the extension page to activate it
            driver.get("chrome-extension://hlifkpholllijblknnmbfagnkjneagid/popup/popup.html")
            time.sleep(2)  # Wait for extension to load
            
            # Then navigate to eBay signup page
            driver.get("https://signup.ebay.com/pa/crte?ru=https%3A%2F%2Fwww.ebay.com%2Fn%2Ferror")
            
            # Check for verification page
            # self.queue.put({'type': 'log', 'text': "Checking for verification page..."})
            try:
                verify_text = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Please verify yourself to continue')]"))
                )
                # self.queue.put({'type': 'log', 'text': "Verification page detected! Waiting for captcha solution..."})
                
                WebDriverWait(driver, 300).until(
                    lambda d: len(d.find_elements(By.XPATH, "//h1[contains(text(), 'Please verify yourself to continue')]")) == 0 or
                             len(d.find_elements(By.ID, "Email")) > 0
                )
                self.queue.put({'type': 'log', 'text': "Verification completed!"})
                time.sleep(2)
            except:
                # self.queue.put({'type': 'log', 'text': "No verification page detected, continuing..."})
                pass
            
            # Wait for email field
            # self.queue.put({'type': 'log', 'text': "Waiting for email field..."})
            email_field = WebDriverWait(driver, 120).until(
                EC.presence_of_element_located((By.ID, "Email"))
            )
            
            # Enter test email and trigger validation
            email_field.send_keys("pijiye6853@citdaca.com")
            time.sleep(1)
            
            # Click outside using JavaScript
            driver.execute_script("arguments[0].blur();", email_field)
            time.sleep(2)
            
            # Check for captcha
            # self.queue.put({'type': 'log', 'text': "Checking for captcha..."})
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")) > 0
                )
                # self.queue.put({'type': 'log', 'text': "Captcha detected! Please solve it..."})
                
                WebDriverWait(driver, 300).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")) == 0
                )
                # self.queue.put({'type': 'log', 'text': "Captcha solved!"})
                time.sleep(2)
            except:
                time.sleep(0.1)
                # self.queue.put({'type': 'log', 'text': "No captcha detected, continuing..."})
            
            # Look for validatefield request in performance logs
            # self.queue.put({'type': 'log', 'text': "Looking for validatefield request..."})
            time.sleep(2)
            
            # Get performance logs
            logs = driver.get_log('performance')
            
            # Process logs to find validatefield request
            validatefield_request = None
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if (
                        'Network.requestWillBeSent' in log['method'] and
                        'validatefield' in log['params']['request']['url']
                    ):
                        validatefield_request = log['params']['request']
                        break
                except:
                    continue
            
            if validatefield_request:
                try:
                    # Extract SRT token from request payload
                    payload = json.loads(validatefield_request['postData'])
                    srt_token = payload.get('srt', '')
                    
                    if srt_token:
                        # Get cookies
                        cookies = driver.get_cookies()
                        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                        
                        # Update internal attributes
                        self.cookie_string = cookie_string
                        self.srt_token = srt_token
                        
                        #self.queue.put({'type': 'log', 'text': f"Found SRT token: {srt_token}"})
                        self.queue.put({'type': 'log', 'text': "Successfully got cookie and token!"})
                        self.queue.put({'type': 'log', 'text': "Checking..."})
                    else:
                        self.queue.put({'type': 'log', 'text': "No SRT token in validatefield request"})
                except Exception as e:
                    self.queue.put({'type': 'log', 'text': f"Error parsing validatefield request: {str(e)}"})
            else:
                self.queue.put({'type': 'log', 'text': "No validatefield request found in logs"})
            
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error: {str(e)}"})
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
    def parse_cookies(self, cookie_string):
        """Convert cookie string to dictionary"""
        cookies = {}
        try:
            for item in cookie_string.strip().split(';'):
                if item:
                    key, value = item.strip().split('=', 1)
                    cookies[key] = value
            return cookies
        except Exception as e:
            messagebox.showerror("Error", f"Invalid cookie format: {str(e)}")
            return None
            
    def clear_results(self):
        """Clear results area"""
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state='disabled')
        
    def clear_fields(self):
        """Clear all input fields"""
        if not self.is_checking:  # Only allow clearing if not checking
            self.cookie_text.delete(1.0, tk.END)
            self.srt_text.delete(1.0, tk.END)
            self.email_list_text.delete(1.0, tk.END)
            self.existing_emails.delete(1.0, tk.END)
            self.available_emails.delete(1.0, tk.END)
            self.clear_results()
        else:
            self.queue.put({'type': 'log', 'text': "Cannot clear fields while checking is in progress"})
        
    async def get_scraper_api_credits(self, session):
        """Check remaining ScraperAPI credits"""
        account_url = "https://api.scraperapi.com/account"
        params = {
            'api_key': "59a68d593a15ea2e525feea76409f203"
        }
        
        try:
            async with session.get(account_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('requestCount', 0), data.get('failedRequestCount', 0)
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Status {response.status}. Error checking credits: {str(e)}"})
        return None, None

    async def check_email_list(self):
        """Modified check_email_list to handle all connection types"""
        try:
            # Clear previous results
            self.queue.put({'type': 'log', 'text': "Starting new check..."})
            self.root.after(0, lambda: self.existing_emails.delete(1.0, tk.END))
            self.root.after(0, lambda: self.available_emails.delete(1.0, tk.END))
            
            # Initialize files with timestamp
            self.timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.existing_file = open(f"existing_emails_{self.timestamp}.txt", "a", encoding="utf-8")
            self.available_file = open(f"available_emails_{self.timestamp}.txt", "a", encoding="utf-8")
            
            connection_type = self.connection_type.get()
            
            # Handle ScraperAPI initialization if selected
            if connection_type == "scraper":
                async with aiohttp.ClientSession() as session:
                    await self.initialize_api_key(session)
                    if not self.current_api_key:
                        self.queue.put({'type': 'log', 'text': "No valid API keys found. Please add API keys with credits."})
                        return
            # Handle SOCKS initialization if selected
            elif connection_type == "socks":
                self.queue.put({'type': 'log', 'text': "Checking proxies before starting..."})
                self.proxy_list = await self.check_proxies()
                if not self.proxy_list:
                    self.queue.put({'type': 'log', 'text': "Error: No live proxies found! Please check your proxy list."})
                    return

            # Get initial inputs
            cookie_string = self.cookie_string
            srt_token = self.srt_token
            email_list = self.email_list_text.get("1.0", tk.END).strip().split('\n')
            email_list = [email.strip() for email in email_list if email.strip()]

            if not email_list:
                self.queue.put({'type': 'log', 'text': "Please enter email list"})
                return

            # Get initial token if needed
            if not all([cookie_string, srt_token]):
                await self.refresh_token()
                cookie_string = self.cookie_string
                srt_token = self.srt_token

            cookies = self.parse_cookies(cookie_string)
            if not cookies:
                return

            total_emails = len(email_list)
            processed = 0
            self.queue.put({'type': 'log', 'text': f"Starting to check {total_emails} emails..."})

            # Configure client session
            conn = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                current_proxy = self.get_next_proxy() if connection_type == "socks" else None
                proxy_fail_count = 0
                
                while email_list and not self.stop_requested:
                    try:
                        # Check if we've used all proxies and need to refresh
                        if connection_type == "socks" and self.current_proxy_index >= len(self.proxy_list):
                            self.queue.put({'type': 'log', 'text': "All proxies used. Checking for live proxies again..."})
                            self.proxy_list = await self.check_proxies()
                            if not self.proxy_list:
                                self.queue.put({'type': 'log', 'text': "No live proxies available! Please add new proxies."})
                                break
                            self.current_proxy_index = 0
                            current_proxy = self.get_next_proxy()

                        # Check API credits if using ScraperAPI
                        if connection_type == "scraper":
                            if self.api_credits.get(self.current_api_key, 0) <= 5:
                                await self.initialize_api_key(session)
                                if not self.current_api_key:
                                    self.queue.put({'type': 'log', 'text': "All API keys exhausted. Please add new API keys."})
                                    break
                                self.queue.put({'type': 'log', 'text': f"Switched to API key {self.current_api_key[:8]}... with {self.api_credits[self.current_api_key]} credits remaining"})

                        # Process emails in batches
                        batch = email_list[:5]
                        tasks = []
                        
                        for email in batch:
                            if connection_type == "scraper":
                                task = self.check_email_scraper(session, email, cookies, srt_token)
                            elif connection_type == "socks":
                                task = self.check_email_async(session, email, cookies, srt_token, proxy=current_proxy)
                            else:  # direct
                                task = self.check_email_async(session, email, cookies, srt_token)
                            tasks.append(task)
                        
                        # Execute batch concurrently
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Process results and handle errors
                        retry_batch = []
                        batch_failed = False
                        
                        for email, result in zip(batch, results):
                            if isinstance(result, Exception):
                                self.queue.put({'type': 'log', 'text': f"Error checking {email}: {str(result)}"})
                                retry_batch.append(email)
                                batch_failed = True
                            elif result is None:
                                retry_batch.append(email)
                                batch_failed = True
                            else:
                                processed += 1
                                if connection_type == "scraper":
                                    self.api_credits[self.current_api_key] -= 1
                        
                        # Handle proxy failures when using SOCKS
                        if connection_type == "socks" and batch_failed:
                            proxy_fail_count += 1
                            if proxy_fail_count >= 2:
                                self.queue.put({'type': 'log', 'text': "Switching to next proxy..."})
                                current_proxy = self.get_next_proxy()
                                proxy_fail_count = 0
                                
                                if not current_proxy:
                                    self.queue.put({'type': 'log', 'text': "No more working proxies available!"})
                                    break
                        
                        # Remove processed emails from list
                        email_list = email_list[5:]
                        
                        # Handle retries if needed
                        if retry_batch:
                            await self.refresh_token()
                            cookie_string = self.cookie_string
                            srt_token = self.srt_token
                            cookies = self.parse_cookies(cookie_string)
                            email_list = retry_batch + email_list
                        
                        # Update progress
                        if processed % 5 == 0:
                            progress_msg = f"Progress: {processed}/{total_emails} emails checked"
                            if connection_type == "scraper":
                                progress_msg += f". Credits remaining: {self.api_credits.get(self.current_api_key, 0)}"
                            self.queue.put({'type': 'log', 'text': progress_msg})
                        
                        # Delay between batches
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        self.queue.put({'type': 'log', 'text': f"Error processing batch: {str(e)}"})
                        await asyncio.sleep(2)

        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error in check_email_list: {str(e)}"})
        finally:
            # Close files
            if self.existing_file:
                self.existing_file.close()
            if self.available_file:
                self.available_file.close()
            self.is_checking = False
            self.stop_requested = False
            self.root.after(0, self.enable_buttons)
            self.queue.put({'type': 'log', 'text': "Finished checking emails!"})

    async def initialize_api_key(self, session):
        """Initialize API key and check its credits"""
        # Get API keys from text area
        api_keys = self.api_keys_text.get("1.0", tk.END).strip().split('\n')
        api_keys = [key.strip() for key in api_keys if key.strip()]
        
        for api_key in api_keys:
            if api_key not in self.api_credits:
                # Check credits for new key
                credits_info = await self.check_api_credits(session, api_key)
                if credits_info and credits_info['remaining'] > 0:
                    self.api_credits[api_key] = credits_info['remaining']
            
            # Use key if it has credits
            if api_key in self.api_credits and self.api_credits[api_key] > 0:
                self.current_api_key = api_key
                return
        
        # No valid API key found
        self.current_api_key = None
        self.api_credits = {}

    def get_random_ip(self):
        """Generate random IP address"""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

    async def check_email_async(self, session, email, cookies, srt_token, retry_count=0, proxy=None):
        """Modified check_email_async to use proxy"""
        MAX_RETRIES = 2
        url = "https://signup.ebay.com/ajax/validatefield"
            
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": random.choice(self.user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": random.choice(self.referers),
            "Origin": "https://signup.ebay.com",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        payload = {
            "email": email,
            "fieldName": "email",
            "moduleName": "BUYER_REG_PERSONAL_EMAIL_DWEB",
            "returnUrl": "https://www.ebay.com/",
            "srt": srt_token
        }

        try:
            # Add proxy to request if available
            proxy_url = proxy['proxy'] if proxy else None
            
            async with session.post(url,
                                  json=payload, 
                                  headers=headers, 
                                  cookies=cookies,
                                  ssl=False,
                                  proxy=proxy_url,
                                  timeout=30) as response:
                
                if response.status == 200:
                    text = await response.text()
                    data = json.loads(text)
                    
                    if "error" in data:
                        error_msg = data.get("error", "")
                        if "already registered" in error_msg.lower():
                            self.queue.put({'type': 'existing', 'email': email})
                            if self.existing_file:
                                self.existing_file.write(f"{email}\n")
                                self.existing_file.flush()
                            return "success"
                        return None
                    
                    if data.get("valid") is True:
                        self.queue.put({'type': 'available', 'email': email})
                        if self.available_file:
                            self.available_file.write(f"{email}\n")
                            self.available_file.flush()
                        return "success"
                    elif data.get("valid") is False:
                        if data.get("emailTaken"):
                            self.queue.put({'type': 'existing', 'email': email})
                            if self.existing_file:
                                self.existing_file.write(f"{email}\n")
                                self.existing_file.flush()
                        return "success"
                    
                elif response.status in [429, 302, 403] and retry_count < MAX_RETRIES:
                    await asyncio.sleep(2)  # Increased delay for rate limiting
                    return await self.check_email_async(session, email, cookies, srt_token, retry_count + 1, proxy=proxy)
                
                return None
                
        except Exception as e:
            if retry_count < MAX_RETRIES:
                # Get new proxy for retry
                new_proxy = self.get_next_proxy()
                await asyncio.sleep(2)
                return await self.check_email_async(session, email, cookies, srt_token, retry_count + 1, proxy=new_proxy)
            return e

    async def refresh_token(self):
        """Get new token and cookie"""
        try:
            # Run get_token in the background
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.get_token)
            await asyncio.sleep(2)  # Wait for UI updates
            
            return True
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error refreshing token: {str(e)}"})
            return False

    def stop_checking(self):
        """Stop the email checking process"""
        self.stop_requested = True
        self.queue.put({'type': 'log', 'text': "Stopping check process..."})
        self.stop_button.config(state='disabled')
        
        # Close files when stopping
        if self.existing_file:
            self.existing_file.close()
        if self.available_file:
            self.available_file.close()
        
        # Close browser if it's running
        if hasattr(self, 'driver') and self.driver:
            try:
                self.queue.put({'type': 'log', 'text': "Closing browser..."})
                self.driver.quit()
                self.driver = None
                self.queue.put({'type': 'log', 'text': "Browser closed successfully"})
            except Exception as e:
                self.queue.put({'type': 'log', 'text': f"Error closing browser: {str(e)}"})

    async def check_api_credits(self, session, api_key):
        """Check credits for a single API key"""
        account_url = "https://api.scraperapi.com/account"
        params = {'api_key': api_key}
        
        try:
            async with session.get(account_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    request_count = data.get('requestCount', 0)
                    request_limit = data.get('requestLimit', 0)
                    remaining = request_limit - request_count
                    return {
                        'api_key': api_key,
                        'used': request_count,
                        'limit': request_limit,
                        'remaining': remaining
                    }
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error checking API key {api_key[:8]}...: {str(e)}"})
        return None

    def check_all_credits(self):
        """Check credits for all API keys"""
        try:
            self.check_credits_button.config(state='disabled')
            
            # Get API keys from text area
            api_keys = self.api_keys_text.get("1.0", tk.END).strip().split('\n')
            api_keys = [key.strip() for key in api_keys if key.strip()]
            
            if not api_keys:
                self.queue.put({'type': 'log', 'text': "Please enter API keys"})
                self.check_credits_button.config(state='normal')
                return
            
            self.queue.put({'type': 'log', 'text': "Checking API credits..."})
            
            # Start or restart async loop if needed
            if not self.loop or not self.loop.is_running():
                self.stop_async_loop()
                self.start_async_loop()
            
            if self.loop and self.loop.is_running():
                async def check_credits():
                    try:
                        async with aiohttp.ClientSession() as session:
                            tasks = [self.check_api_credits(session, key) for key in api_keys]
                            results = await asyncio.gather(*tasks)
                            
                            self.queue.put({'type': 'log', 'text': "\nAPI Credits Status:"})
                            total_remaining = 0
                            available_apis = []  # List to store APIs with remaining credits
                            
                            for result in results:
                                if result:
                                    if result['remaining'] > 0:
                                        msg = f"API {result['api_key'][:8]}... - Used: {result['used']}, "
                                        msg += f"Limit: {result['limit']}, Remaining: {result['remaining']}"
                                        self.queue.put({'type': 'log', 'text': msg})
                                        total_remaining += result['remaining']
                                        available_apis.append(result['api_key'])
                            
                            self.queue.put({'type': 'log', 'text': f"\nTotal remaining credits: {total_remaining}"})
                            
                            # Update API keys text area with only available APIs
                            if available_apis:
                                self.queue.put({'type': 'log', 'text': "\nAvailable APIs with credits:"})
                                for api in available_apis:
                                    self.queue.put({'type': 'log', 'text': f"{api}"})
                                
                                # Update API keys text area
                                def update_api_text():
                                    self.api_keys_text.delete(1.0, tk.END)
                                    self.api_keys_text.insert(tk.END, '\n'.join(available_apis))
                                self.root.after(0, update_api_text)
                            else:
                                self.queue.put({'type': 'log', 'text': "\nNo APIs with remaining credits available!"})
                                # Clear API keys text area
                                self.root.after(0, lambda: self.api_keys_text.delete(1.0, tk.END))
                            
                    except Exception as e:
                        self.queue.put({'type': 'log', 'text': f"Error in check_credits: {str(e)}"})
                
                # Run the async function
                future = asyncio.run_coroutine_threadsafe(check_credits(), self.loop)
                
                def done_callback(fut):
                    try:
                        fut.result()
                    except Exception as e:
                        self.queue.put({'type': 'log', 'text': f"Error in credits check: {str(e)}"})
                    finally:
                        self.root.after(0, lambda: self.check_credits_button.config(state='normal'))
                
                future.add_done_callback(done_callback)
                
                # Start GUI updates if not already running
                if not self.update_id:
                    self.update_gui()
            else:
                self.queue.put({'type': 'log', 'text': "Failed to start async loop"})
                self.check_credits_button.config(state='normal')
            
        except Exception as e:
            self.queue.put({'type': 'log', 'text': f"Error checking credits: {str(e)}"})
            self.check_credits_button.config(state='normal')

    def parse_proxy(self, proxy_str):
        """Parse proxy string into dictionary format"""
        try:
            parts = proxy_str.strip().split(':')
            if len(parts) == 2:
                return {
                    'proxy': f"socks5://{parts[0]}:{parts[1]}"
                }
            elif len(parts) == 4:
                return {
                    'proxy': f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                }
            return None
        except:
            return None

    def get_next_proxy(self):
        """Get next proxy from the list in round-robin fashion"""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy

    async def check_proxy_alive(self, session, proxy):
        """Check if a proxy is alive using httpbin.org"""
        test_url = "http://httpbin.org/ip"
        try:
            proxy_url = proxy['proxy']
            async with session.get(test_url, 
                                 proxy=proxy_url,
                                 timeout=5,  # Giảm timeout xuống 5s
                                 ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "origin" in data:
                        return True
            return False
        except Exception:
            return False

    async def check_proxies(self):
        """Check all proxies and filter live ones"""
        self.queue.put({'type': 'log', 'text': "Checking proxies..."})
        
        # Parse proxy list
        proxy_list = self.proxy_list_text.get("1.0", tk.END).strip().split('\n')
        all_proxies = [
            self.parse_proxy(proxy) for proxy in proxy_list 
            if proxy.strip() and self.parse_proxy(proxy.strip())
        ]
        
        if not all_proxies:
            self.queue.put({'type': 'log', 'text': "No valid proxy format found!"})
            return []

        # Create session for proxy checking
        conn = aiohttp.TCPConnector(ssl=False, limit=100)
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            batch_size = 100
            live_proxies = []
            total_proxies = len(all_proxies)
            checked = 0

            for i in range(0, len(all_proxies), batch_size):
                batch = all_proxies[i:i + batch_size]
                tasks = [self.check_proxy_alive(session, proxy) for proxy in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter live proxies from this batch
                for proxy, is_alive in zip(batch, results):
                    if isinstance(is_alive, bool) and is_alive:
                        live_proxies.append(proxy)
                
                checked += len(batch)
                self.queue.put({'type': 'log', 'text': f"Checking proxies: {checked}/{total_proxies}"})
                await asyncio.sleep(0.1)
        
        total_live = len(live_proxies)
        self.queue.put({'type': 'log', 'text': f"Found {total_live} live proxies out of {total_proxies}"})
        
        # Update proxy list text area with live proxies
        def update_proxy_text():
            self.proxy_list_text.delete(1.0, tk.END)
            for proxy in live_proxies:
                proxy_str = proxy['proxy'].replace('socks5://', '')
                self.proxy_list_text.insert(tk.END, f"{proxy_str}\n")
        self.root.after(0, update_proxy_text)
        
        # Save live proxies to file
        if live_proxies:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            with open(f"live_proxies_{timestamp}.txt", "w", encoding="utf-8") as f:
                for proxy in live_proxies:
                    f.write(f"{proxy['proxy'].replace('socks5://', '')}\n")
        
        return live_proxies

    async def check_email_scraper(self, session, email, cookies, srt_token, retry_count=0):
        """Check a single email using ScraperAPI"""
        MAX_RETRIES = 0
        url = "https://signup.ebay.com/ajax/validatefield"
        
        scraper_params = {
            'api_key': self.current_api_key,
            'url': url,
            'keep_headers': 'true',
            'session_number': random.randint(1, 1000),
            'country_code': random.choice(['us', 'uk', 'de']),
            'render': 'true'
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": random.choice(self.user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": random.choice(self.referers),
            "Origin": "https://signup.ebay.com",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        payload = {
            "email": email,
            "fieldName": "email",
            "moduleName": "BUYER_REG_PERSONAL_EMAIL_DWEB",
            "returnUrl": "https://www.ebay.com/",
            "srt": srt_token
        }

        try:
            async with session.post("http://api.scraperapi.com", 
                                  params=scraper_params,
                                  json=payload, 
                                  headers=headers, 
                                  cookies=cookies,
                                  allow_redirects=False) as response:
                
                if response.status == 200:
                    text = await response.text()
                    data = json.loads(text)
                    
                    if "error" in data:
                        error_msg = data.get("error", "")
                        if "already registered" in error_msg.lower():
                            self.queue.put({'type': 'existing', 'email': email})
                            if self.existing_file:
                                self.existing_file.write(f"{email}\n")
                                self.existing_file.flush()
                            return "success"
                        return None
                    
                    if data.get("valid") is True:
                        self.queue.put({'type': 'available', 'email': email})
                        if self.available_file:
                            self.available_file.write(f"{email}\n")
                            self.available_file.flush()
                        return "success"
                    elif data.get("valid") is False:
                        if data.get("emailTaken"):
                            self.queue.put({'type': 'existing', 'email': email})
                            if self.existing_file:
                                self.existing_file.write(f"{email}\n")
                                self.existing_file.flush()
                        return "success"
                    
                elif response.status in [429, 302] and retry_count < MAX_RETRIES:
                    await asyncio.sleep(2)
                    return await self.check_email_scraper(session, email, cookies, srt_token, retry_count + 1)
                
                return None
                
        except Exception as e:
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(2)
                return await self.check_email_scraper(session, email, cookies, srt_token, retry_count + 1)
            return e

def extract_csrf_token(html_content):
    """Trích xuất CSRF token từ HTML"""
    csrf_match = re.search(r'name="_csrf"\s+value="([^"]+)"', html_content)
    if csrf_match:
        return csrf_match.group(1)
    return generate_csrf_token()  # Fallback to random token

def generate_csrf_token():
    """Tạo CSRF token ngẫu nhiên"""
    return ''.join(random.choices('0123456789abcdef', k=32))

# Test function
if __name__ == "__main__":
    root = tk.Tk()
    app = EbayEmailChecker(root)
    root.mainloop()
 