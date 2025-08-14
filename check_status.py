import os
import requests
import time
import random
from datetime import datetime, timedelta
from notion_client import Client
from notion_client import APIErrorCode, APIResponseError

notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["DATABASE_ID"]

# 获取代理列表的函数（免费公共代理）
def get_free_proxies():
    try:
        response = requests.get("https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all")
        proxies = response.text.splitlines()
        return proxies
    except:
        return []

# 使用代理访问网站
def check_site_with_proxy(url, proxy_list):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # 尝试最多3个不同的代理
    for _ in range(3):
        if not proxy_list:
            proxy_list = get_free_proxies()
        
        proxy = random.choice(proxy_list) if proxy_list else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=15,
                allow_redirects=True,
                proxies=proxies
            )
            if response.status_code == 200:
                return {"name": "✅正常", "color": "green"}
            else:
                return {"name": f"❓HTTP错误: {response.status_code}", "color": "red"}
        except requests.exceptions.Timeout:
            return {"name": "❌超时", "color": "orange"}
        except requests.exceptions.ConnectionError:
            # 代理可能失效，从列表中移除
            if proxy in proxy_list:
                proxy_list.remove(proxy)
            continue
        except Exception as e:
            return {"name": f"异常: {str(e)}", "color": "red"}
    
    return {"name": "代理失败", "color": "red"}

def update_status():
    cursor = None
    proxy_list = get_free_proxies()  # 初始化代理列表
    
    while True:
        try:
            query = notion.databases.query(
                database_id,
                start_cursor=cursor,
                page_size=50,
                filter={"property": "URL-TEXT", "url": {"is_not_empty": True}}
            )
            pages = query.get("results")
            for page in pages:
                url_property = page["properties"]["URL-TEXT"]["url"]
                if url_property:
                    # 使用代理检测网站
                    status_data = check_site_with_proxy(url_property, proxy_list)
                    
                    # 生成北京时间 (UTC+8)
                    utc_now = datetime.utcnow()
                    beijing_time = utc_now + timedelta(hours=8)
                    formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M")
                    last_check_text = f"于 {formatted_time} 检测状态啦~"
                    
                    # 更新Notion属性
                    properties_update = {
                        "Status": {
                            "status": {
                                "name": status_data["name"],
                                "color": status_data["color"]
                            }
                        },
                        "LAST-CHECK": {"rich_text": [{"text": {"content": last_check_text}}]}
                    }
                    
                    notion.pages.update(
                        page["id"],
                        properties=properties_update
                    )
                    print(f"更新: {url_property} → {status_data['name']} | {last_check_text}")
                    time.sleep(0.5)  # 控制Notion API请求频率
            if not query.get("has_more"):
                break
            cursor = query.get("next_cursor")
        except APIResponseError as e:
            if e.code == APIErrorCode.RateLimited:
                print("遇到速率限制，等待10秒后重试...")
                time.sleep(10)
            else:
                raise

if __name__ == "__main__":
    update_status()
