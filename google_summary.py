import requests
import json
# from llama_cpp import Llama
# from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

from concurrent.futures import ThreadPoolExecutor, as_completed

def search_duckduckgo(query):
    # 設定 Chrome 的選項
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # 啟用無頭模式（背景執行，不顯示瀏覽器）

    # 使用 ChromeDriver 來啟動瀏覽器
    service = Service(executable_path='C://Users//pondahai//Downloads//chromedriver-win64//chromedriver.exe')  # 請確保替換為你的 chromedriver 路徑
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 打開 DuckDuckGo
    driver.get("https://duckduckgo.com/html")
    
    # 找到搜尋框並輸入查詢內容
    search_box = driver.find_element(By.NAME, 'q')
    search_box.send_keys(query)
    search_box.submit()

    time.sleep(2)  # 等待頁面加載

    # 抓取搜尋結果
    results = []
    search_results = driver.find_elements(By.CLASS_NAME, 'result__snippet')
    #print(search_results)
    for result in search_results:
        #print(result)
        text = result.text
        link = result.get_attribute('href')
        results.append({'text': text, 'link': link})

    # 關閉瀏覽器
    driver.quit()
    
    return results

def format_prompt(instruction, chat, question):
    message = [
        {"role": "system", "content": instruction},
        *[
            {"role": "user", "content": entry['human']} if 'human' in entry else {"role": "assistant", "content": entry['assistant']}
            for entry in chat
        ],
        {"role": "user", "content": question}
    ]
    return message


def stream_chat_completions(api_url, api_key, prompt, max_retries=3):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    data = {
        'model': 'your-model-name',
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': True,
        'max_tokens': 8192
    }

    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(api_url, headers=headers, json=data, stream=True)
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data:'):
                            json_data = json.loads(decoded_line[5:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                content = json_data['choices'][0]['delta'].get('content')
                                if content:
                                    yield content
                return  # 成功完成，退出循環
            else:
                print(f"Error: {response.status_code}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")

        retries += 1
        print(f"Retrying ({retries}/{max_retries})...")
        time.sleep(2)  # 等待一段時間再重試

    print("Max retries reached. Giving up.")

def check_urls(urls, max_workers=10):
    """
    多线程检查多个网址的响应，返回第一个响应成功的网址。

    Args:
        urls (list): 要检查的网址列表。
        max_workers (int, optional): 线程池中的最大工作线程数。默认为10。

    Returns:
        str: 第一个响应成功的网址，如果全部失败则返回 None。
        dict: 包含每个网址的响应状态和响应时间的字典。
    """

    results = {}

    def check_url(url):
        start_time = time.time()
        try:
            response = requests.get(url)
            response.raise_for_status()
            end_time = time.time()
            return url, True, end_time - start_time
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            return url, False, end_time - start_time

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check_url, url) for url in urls]
        for future in as_completed(futures):
            url, success, duration = future.result()
            results[url] = {'success': success, 'duration': duration}
            if success:
                return url, results

    return None, results

if __name__ == "__main__":
    query = input("請輸入搜尋關鍵字：")
    result = search_duckduckgo(query)
    total = ''
    urls = ["","",""]
    urls[0] = "http://raspberrypi.local:1234"
    urls[1] = "http://ubuntu:1234"
    urls[2] = "http://localhost:1234"
    first_response_url, all_results = check_urls(urls)
    
    if result:
        # 假設 result 是列表形式，需要迭代處理
        for item in result:  # 你可能需要解析 result 得到真正的項目列表
            print('--------------------')
            print(item['text'])
            print('====================')
            api_url = first_response_url + "/v1/chat/completions"
#             api_url = 'http://raspberrypi.local:1234/v1/chat/completions'
            api_key = 'your-api-key'
            prompt = item['text'] + '\n我用少數幾句zh_TW總結這一段文字並且強調文中提到的數字'

            for content in stream_chat_completions(api_url, api_key, prompt):
                total += content
                print(content, end='', flush=True)
            
            print()
            print()
        
        print('++++++++++++++++++++')
        print(total)
        print('++++++++++++++++++++')
        prompt = total + '\n我先用zh_TW回答分析這篇文字特別強調提到的數字\n然後給出基於這篇文字事實的zh_TW版結論'
        for content in stream_chat_completions(api_url, api_key, prompt):
            print(content, end='', flush=True)
            
