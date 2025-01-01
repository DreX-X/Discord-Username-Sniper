import json
import os
import asyncio
import time
from typing import Dict, Optional, List
import tls_client
from datetime import datetime
import aiohttp
import subprocess
import sys
import platform
import requests
from colorama import Fore, Back, Style, init

def redirect_to_discord():
    try:
        response = requests.get("https://discord.gg/leafhub")
        if response.status_code == 200:
            print(f"Successfully redirected to discord.gg/leafhub")
        else:
            print(f"Failed to redirect, status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error while trying to redirect: {e}")

redirect_to_discord()

class RazorCapSolver:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.razorcap.xyz"

    def create_task(self, sitekey: str, siteurl: str, proxy: str, rqdata: Optional[str] = None) -> Optional[int]:
        data = {
            'key': self.api_key,
            'type': 'hcaptcha_enterprise',
            'data': {
                'sitekey': sitekey,
                'siteurl': siteurl.replace('https://', '').split('/')[0],
                'proxy': f'http://{proxy}' if not proxy.startswith(('http://', 'https://')) else proxy
            }
        }
        
        if rqdata:
            data['data']['rqdata'] = rqdata

        try:
            response = requests.post(f"{self.base_url}/create_task", json=data)
            if response.status_code == 200:
                return response.json().get('task_id')
            return None
        except:
            return None

    def get_result(self, task_id: int, max_attempts: int = 60) -> Optional[str]:
        for _ in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/get_result/{task_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 'solved' and 'response_key' in result:
                        return result['response_key']
                    elif result['status'] == 'error':
                        return None
                time.sleep(1)
            except:
                pass
        return None

    def solve(self, sitekey: str, siteurl: str, proxy: str, rqdata: Optional[str] = None) -> Optional[str]:
        task_id = self.create_task(sitekey, siteurl, proxy, rqdata)
        if task_id is None:
            return None
            
        return self.get_result(task_id)

class Utils:
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def load_tokens(filename: str) -> List[Dict[str, str]]:
        try:
            with open(filename, 'r') as f:
                tokens = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            token, password = line.split(':')
                            tokens.append({
                                'token': token.strip(),
                                'password': password.strip()
                            })
                        except ValueError:
                            print(f"{Fore.RED}[-] Invalid format in {filename}. Skipping line: {line}{Style.RESET_ALL}")
                return tokens
        except FileNotFoundError:
            print(f"[-] {filename} not found")
            exit(1)
        except Exception as e:
            print(f"[-] Error reading {filename}: {e}")
            exit(1)

    @staticmethod
    def load_usernames(filename: str) -> List[str]:
        try:
            with open(filename, 'r') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            print(f"[-] {filename} not found")
            exit(1)
        except Exception as e:
            print(f"[-] Error reading {filename}: {e}")
            exit(1)

utils = Utils()

def load_config() -> dict:
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            required_keys = ['webhook_url', 'razorcap_key', 'proxy']
            
            if not all(key in config for key in required_keys):
                raise KeyError("Missing required configuration keys")
                
            return config
            
    except FileNotFoundError:
        print("[-] config.json not found")
        exit(1)
    except json.JSONDecodeError:
        print("[-] Invalid JSON in config.json")
        exit(1)
    except KeyError as e:
        print(f"[-] Configuration error: {e}")
        exit(1)

class UsernameSniper:
    def __init__(self, token_data: Dict[str, str], config: dict, target_username: str):
        self.token = token_data['token']
        self.password = token_data['password']
        self.target_username = target_username
        self.webhook_url = config['webhook_url']
        self.razorcap_key = config['razorcap_key']
        self.proxy = config['proxy']
        self.running = True
        self.start_time = time.time()
        
        self.solver = RazorCapSolver(self.razorcap_key)
        
        self.session = tls_client.Session(
            client_identifier="chrome_117",
            random_tls_extension_order=True
        )
        
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Chromium";v="117", "Google Chrome";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-US',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNy4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE3LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjIyMzg1MSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
        }


    async def send_webhook(self, title: str, description: str, color: int = 0x00ff00):
        try:
            async with aiohttp.ClientSession() as session:
                webhook_data = {
                    "embeds": [{
                        "title": title,
                        "description": description,
                        "color": color,
                        "timestamp": datetime.now().isoformat()
                    }]
                }
                async with session.post(self.webhook_url, json=webhook_data) as response:
                    if response.status != 204:
                        print(f"Failed to send webhook: {response.status}")
        except Exception as e:
            print(f"Webhook error: {e}")

    def get_elapsed_time(self) -> str:
        elapsed = time.time() - self.start_time
        return f"{elapsed:.2f}s"

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        token_preview = f"{self.token[:6]}...{self.token[-6:]}"
        print(f"[{timestamp}] [{level}] [{token_preview}] {message}")

    async def validate_token(self) -> bool:
        try:
            response = self.session.get(
                "https://discord.com/api/v9/users/@me",
                headers=self.headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.log(f"Logged in as: {user_data.get('username')}#{user_data.get('discriminator')}")
                return True
            else:
                self.log(f"Invalid token. Status code: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Token validation error: {e}", "ERROR")
            return False

    async def check_username_available(self) -> bool:
        try:
            response = self.session.get(
                f"https://discord.com/api/v9/users/username/{self.target_username}",
                headers=self.headers
            )
            
            if response.status_code == 404:
                return True
            elif response.status_code == 429:
                retry_after = response.json().get('retry_after', 1)
                self.log(f"Rate limited. Waiting {retry_after} seconds...", "WARN")
                await asyncio.sleep(retry_after)
            
            return False
                
        except Exception as e:
            self.log(f"Error checking username availability: {e}", "ERROR")
            await asyncio.sleep(1)
            return False

    async def claim_username(self):
        url = "https://discord.com/api/v9/users/@me"
        
        try:
            payload = {
                'username': self.target_username,
                'password': self.password
            }
            
            response = self.session.patch(
                url,
                json=payload,
                headers=self.headers
            )
            
            if response.status_code == 200:
                self.log(f"Successfully claimed username: {self.target_username}", "SUCCESS")
                await self.send_webhook(
                    "Username Claimed Successfully!",
                    f"Successfully Claimed Username\n(`{self.target_username}`)\n\nElapsed Time\n(`{self.get_elapsed_time()}`)"
                )
                return True
                
            response_data = response.json()
            
            if 'captcha_key' in response_data:
                self.log("Captcha detected, solving...", "INFO")
                captcha_sitekey = response_data['captcha_sitekey']
                captcha_rqdata = response_data.get('captcha_rqdata')
                captcha_rqtoken = response_data.get('captcha_rqtoken')
                
                captcha_key = self.solver.solve(
                    sitekey=captcha_sitekey,
                    siteurl="discord.com",
                    proxy=self.proxy,
                    rqdata=captcha_rqdata
                )
                
                if captcha_key:
                    self.log("Captcha solved successfully, retrying claim...", "SUCCESS")
                    payload.update({
                        'captcha_key': captcha_key,
                        'captcha_rqtoken': captcha_rqtoken 
                    })
                    
                    response = self.session.patch(
                        url,
                        json=payload,
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        self.log(f"Successfully claimed username: {self.target_username}", "SUCCESS")
                        await self.send_webhook(
                            "Username Claimed Successfully!",
                            f"Successfully Claimed Username\n(`{self.target_username}`)\n\nElapsed Time\n(`{self.get_elapsed_time()}`)"
                        )
                        return True
                else:
                    self.log("Failed to solve captcha", "ERROR")
                    
            self.log(f"Failed to claim username. Response: {response.text}", "ERROR")
            return False
            
        except Exception as e:
            self.log(f"Error claiming username: {e}", "ERROR")
            return False

    async def monitor_username(self):
        self.log("Starting username sniper...", "ALERT")
        await self.send_webhook(
            "Username Sniper Started",
            f"🚀 Monitoring for username availability: {self.target_username}"
        )
        
        if not await self.validate_token():
            self.log("Token validation failed. Exiting...", "ERROR")
            return

        self.log("Initial validation successful, starting monitoring loop...", "SUCCESS")
        
        while self.running:
            try:
                is_available = await self.check_username_available()
                
                if is_available:
                    self.log(f"Target username {self.target_username} is available! Attempting to claim...", "ALERT")
                    if await self.claim_username():
                        self.running = False
                        return
                    else:
                        await asyncio.sleep(2)
                else:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                self.log(f"Error monitoring username: {e}", "ERROR")
                await asyncio.sleep(1)

async def main():
    init(autoreset=True)
    utils.clear()
    
    print(f"""
{Fore.CYAN}   __             __              _      
  / /  ___  __ _ / _| /\  /\_   _| |__   
 / /  / _ \/ _` | |_ / /_/ / | | | '_ \  
/ /__|  __/ (_| |  _/ __  /| |_| | |_) | 
\____/\___|\__,_|_| \/ /_/  \__,_|_.__/  
                                         
{Fore.YELLOW}         Username Sniper
{Fore.LIGHTBLACK_EX}         Created by Leaf{Style.RESET_ALL}
    """)

    try:
        print(f"{Fore.YELLOW}[*] Loading configuration...{Style.RESET_ALL}")
        config = load_config()
        
        tokens = Utils.load_tokens('tokens.txt')
        usernames = Utils.load_usernames('usernames.txt')
        
        print(f"{Fore.GREEN}[+] Configuration loaded successfully{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[+] Loaded {len(tokens)} token:password pairs and {len(usernames)} usernames{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}[Configuration Summary]{Style.RESET_ALL}")
        print(f"{Fore.WHITE}├─ Target Usernames: {Fore.CYAN}{len(usernames)} loaded{Style.RESET_ALL}")
        print(f"{Fore.WHITE}├─ Tokens: {Fore.CYAN}{len(tokens)} loaded{Style.RESET_ALL}")
        print(f"{Fore.WHITE}└─ Webhook Configured: {Fore.GREEN}Yes{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}[*] Initializing snipers...{Style.RESET_ALL}")
        
        tasks = []
        for token_data in tokens:
            for username in usernames:
                sniper = UsernameSniper(token_data, config, username)
                tasks.append(sniper.monitor_username())
        
        print(f"\n{Fore.GREEN}[+] Starting username monitoring with {len(tasks)} tasks{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] Press CTRL+C to stop{Style.RESET_ALL}\n")
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[!] Shutdown requested by user{Style.RESET_ALL}")
        print(f"{Fore.WHITE}[*] Cleaning up...{Style.RESET_ALL}")
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"\n{Fore.RED}[!] Fatal error occurred: {e}{Style.RESET_ALL}")
        
    finally:
        if not asyncio.get_event_loop().is_closed():
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            
            loop = asyncio.get_event_loop()
            loop.close()
            print(f"\n{Fore.GREEN}[+] Cleanup completed. Goodbye!{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Process terminated by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}[!] Unhandled exception: {e}{Style.RESET_ALL}")
    finally:
        print(f"\n{Fore.YELLOW}[*] Exiting...{Style.RESET_ALL}")
