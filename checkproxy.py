import requests
import time
import os
import sys
import concurrent.futures
from datetime import datetime
from colorama import Fore, Style, init
from urllib.parse import urlparse

# Initialize colorama
init()

# Test endpoints
ENDPOINTS = {
    "api": "https://api.pharosnetwork.xyz/health",
    "rpc": "https://testnet.dplabs-internal.com",
    "google": "https://www.google.com"
}

# Maximum timeout for requests
TIMEOUT = 15

def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.BLUE}[{timestamp}] [INFO]{Style.RESET_ALL} ℹ️  {message}")

def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] [SUCCESS]{Style.RESET_ALL} ✅ {message}")

def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.RED}[{timestamp}] [ERROR]{Style.RESET_ALL} ❌ {message}")

def log_warning(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.YELLOW}[{timestamp}] [WARNING]{Style.RESET_ALL} ⚠️  {message}")

def format_proxy_for_display(proxy):
    """Format proxy string for display (hide password)"""
    if '@' in proxy:
        # For authenticated proxies, mask the password
        parts = proxy.split('@')
        auth_part = parts[0]
        server_part = parts[1]
        
        if ':' in auth_part and '://' in auth_part:
            proto_user, password = auth_part.rsplit(':', 1)
            masked_proxy = f"{proto_user}:****@{server_part}"
        else:
            masked_proxy = f"****@{server_part}"
        
        return masked_proxy
    return proxy

def format_proxy_for_requests(proxy_str):
    """Format proxy string for requests library"""
    if not proxy_str:
        return None
    
    # Handle tunneling proxy format with proxy+ prefix
    if proxy_str.startswith("proxy+"):
        proxy_url = proxy_str.replace("proxy+", "")
        return {
            'http': proxy_url,
            'https': proxy_url  # Same URL for HTTPS tunneling
        }
        
    # Add default protocol if missing
    if not ('://' in proxy_str):
        proxy_str = f"http://{proxy_str}"
        
    return {
        'http': proxy_str,
        'https': proxy_str
    }

def test_proxy_endpoint(proxy_str, endpoint_name, endpoint_url):
    """Test proxy with a specific endpoint"""
    proxies = format_proxy_for_requests(proxy_str)
    start_time = time.time()
    
    try:
        response = requests.get(
            endpoint_url, 
            proxies=proxies, 
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code < 400:
            return {
                "success": True,
                "endpoint": endpoint_name,
                "status_code": response.status_code,
                "response_time": elapsed_time
            }
        else:
            return {
                "success": False,
                "endpoint": endpoint_name,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}"
            }
    except requests.exceptions.ConnectTimeout:
        return {
            "success": False,
            "endpoint": endpoint_name,
            "error": "Connection Timeout"
        }
    except requests.exceptions.ReadTimeout:
        return {
            "success": False,
            "endpoint": endpoint_name,
            "error": "Read Timeout"
        }
    except requests.exceptions.ProxyError as e:
        return {
            "success": False,
            "endpoint": endpoint_name,
            "error": f"Proxy Error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "endpoint": endpoint_name,
            "error": str(e)
        }

def test_proxy(proxy_str):
    """Test a proxy with multiple endpoints"""
    display_proxy = format_proxy_for_display(proxy_str)
    log_info(f"Testing proxy: {display_proxy}")
    
    results = {}
    total_success = 0
    
    for endpoint_name, endpoint_url in ENDPOINTS.items():
        result = test_proxy_endpoint(proxy_str, endpoint_name, endpoint_url)
        results[endpoint_name] = result
        
        if result["success"]:
            total_success += 1
            log_success(f"  {endpoint_name.upper()}: OK ({result['response_time']:.2f}s)")
        else:
            log_error(f"  {endpoint_name.upper()}: Failed - {result['error']}")
    
    proxy_score = total_success / len(ENDPOINTS)
    
    # Determine overall status
    if proxy_score >= 0.75:
        status = "EXCELLENT"
        color = Fore.GREEN
    elif proxy_score >= 0.5:
        status = "GOOD"
        color = Fore.YELLOW
    elif proxy_score > 0:
        status = "POOR"
        color = Fore.RED
    else:
        status = "FAILED"
        color = Fore.RED
    
    log_info(f"Proxy status: {color}{status}{Style.RESET_ALL} (Score: {proxy_score:.2f})")
    print()
    
    return {
        "proxy": proxy_str,
        "display_proxy": display_proxy,
        "score": proxy_score,
        "status": status,
        "results": results
    }

def load_proxies(filename="proxy.txt"):
    """Load proxies from file"""
    if not os.path.exists(filename):
        log_error(f"Proxy file {filename} not found")
        return []
    
    with open(filename, "r") as file:
        proxies = [line.strip() for line in file if line.strip()]
    
    if not proxies:
        log_error(f"No proxies found in {filename}")
    else:
        log_info(f"Loaded {len(proxies)} proxies from {filename}")
    
    return proxies

def save_working_proxies(results, filename="goodproxy.txt", min_score=0.5):
    """Save working proxies to a file"""
    working_proxies = [r["proxy"] for r in results if r["score"] >= min_score]
    
    if not working_proxies:
        log_error(f"No proxies met the minimum score of {min_score}")
        return False
    
    try:
        with open(filename, "w") as file:
            for proxy in working_proxies:
                file.write(f"{proxy}\n")
        log_success(f"Saved {len(working_proxies)} good proxies to {filename}")
        return True
    except Exception as e:
        log_error(f"Failed to save good proxies: {str(e)}")
        return False

def print_summary(results):
    """Print summary of proxy test results"""
    excellent = len([r for r in results if r["status"] == "EXCELLENT"])
    good = len([r for r in results if r["status"] == "GOOD"])
    poor = len([r for r in results if r["status"] == "POOR"])
    failed = len([r for r in results if r["status"] == "FAILED"])
    total = len(results)
    
    print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {Fore.YELLOW}PROXY CHECK SUMMARY{' ' * 40}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Total proxies checked:   {total}{' ' * (60 - 26 - len(str(total)))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Excellent proxies:       {Fore.GREEN}{excellent}{Style.RESET_ALL}{' ' * (60 - 26 - len(str(excellent)))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Good proxies:            {Fore.YELLOW}{good}{Style.RESET_ALL}{' ' * (60 - 26 - len(str(good)))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Poor proxies:            {Fore.RED}{poor}{Style.RESET_ALL}{' ' * (60 - 26 - len(str(poor)))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Failed proxies:          {Fore.RED}{failed}{Style.RESET_ALL}{' ' * (60 - 26 - len(str(failed)))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    
    if excellent + good > 0:
        print(f"\n{Fore.GREEN}Recommendation: Use the {excellent + good} proxies with 'EXCELLENT' or 'GOOD' status{Style.RESET_ALL}")
        
    return {
        "total": total,
        "excellent": excellent,
        "good": good,
        "poor": poor,
        "failed": failed
    }

def print_banner():
    """Print program banner"""
    banner = f"""
{Fore.MAGENTA}{'═' * 60}
║{' ' * 58}║
║{Fore.YELLOW}  🔍 PHAROS NETWORK PROXY CHECKER 🔍  {Fore.MAGENTA}{' ' * 17}║
║{Fore.CYAN}        Verify and test your proxies        {Fore.MAGENTA}{' ' * 17}║
║{' ' * 58}║
{'═' * 60}{Style.RESET_ALL}
"""
    print(banner)

def main():
    print_banner()
    
    # Determine which proxy files to check
    print(f"{Fore.YELLOW}Select proxy file to check:{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[1] Main proxy.txt{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[2] Faucet proxy.txt{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[3] Custom file{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[4] Test all files{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[5] Test single proxy (input manually){Style.RESET_ALL}")
    
    choice = -1
    while choice < 1 or choice > 5:
        try:
            choice = int(input(f"{Fore.GREEN}Enter choice [1-5]: {Style.RESET_ALL}"))
        except ValueError:
            log_error("Please enter a valid number")
    
    proxy_list = []
    
    if choice == 1:
        proxy_list = load_proxies("proxy.txt")
    elif choice == 2:
        proxy_list = load_proxies("faucet/proxy.txt")
    elif choice == 3:
        custom_file = input(f"{Fore.GREEN}Enter proxy file path: {Style.RESET_ALL}")
        proxy_list = load_proxies(custom_file)
    elif choice == 4:
        # Check all proxy files
        main_proxies = load_proxies("proxy.txt") if os.path.exists("proxy.txt") else []
        faucet_proxies = load_proxies("faucet/proxy.txt") if os.path.exists("faucet/proxy.txt") else []
        proxy_list = list(set(main_proxies + faucet_proxies))  # Remove duplicates
        log_info(f"Testing {len(proxy_list)} unique proxies from all files")
    elif choice == 5:
        # Test single proxy
        proxy = input(f"{Fore.GREEN}Enter proxy (format: [proxy+]http://user:pass@host:port): {Style.RESET_ALL}")
        if proxy:
            proxy_list = [proxy]
        else:
            log_error("No proxy entered")
            return
    
    if not proxy_list:
        log_error("No proxies to test")
        return
    
    # Ask if user wants to run tests in parallel
    use_parallel = input(f"{Fore.GREEN}Run tests in parallel for faster results? (y/n) [y]: {Style.RESET_ALL}").lower() != 'n'
    
    log_info(f"Starting proxy check for {len(proxy_list)} proxies")
    start_time = time.time()
    
    results = []
    
    if use_parallel and len(proxy_list) > 1:
        # Parallel testing with ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(proxy_list))) as executor:
            future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxy_list}
            for future in concurrent.futures.as_completed(future_to_proxy):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    proxy = future_to_proxy[future]
                    log_error(f"Error testing proxy {format_proxy_for_display(proxy)}: {str(e)}")
    else:
        # Sequential testing
        for proxy in proxy_list:
            try:
                result = test_proxy(proxy)
                results.append(result)
            except Exception as e:
                log_error(f"Error testing proxy {format_proxy_for_display(proxy)}: {str(e)}")
    
    elapsed_time = time.time() - start_time
    log_info(f"Proxy check completed in {elapsed_time:.2f} seconds")
    
    # Print summary
    summary = print_summary(results)
    
    # Automatically save good proxies (score >= 0.5) to goodproxy.txt
    if summary["excellent"] + summary["good"] > 0:
        log_info(f"Automatically saving proxies with EXCELLENT/GOOD status to goodproxy.txt")
        save_working_proxies(results, "goodproxy.txt", 0.5)
    else:
        log_warning("No good proxies found to save")

if __name__ == "__main__":
    main()