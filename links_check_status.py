import os
import requests
import time
from datetime import datetime, timedelta
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["DATABASE_ID"]

def check_site(url):
    try:
        response = requests.get(url, timeout=15, allow_redirects=True)
        return "状态：✅正常" if response.status_code in (200, 403) else f"状态：❓HTTP错误: {response.status_code}"
    except requests.exceptions.Timeout:
        return "状态：❌超时"
    except requests.exceptions.ConnectionError:
        return "状态：❌DNS错误"
    except Exception:
        return "状态：❌异常"

def update_status():
    cursor = None
    while True:
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
                new_status = check_site(url_property)
                
                # 生成北京时间 (UTC+8)
                utc_now = datetime.utcnow()
                beijing_time = utc_now + timedelta(hours=8)
                formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M")
                last_check_text = f"本状态于 {formatted_time} 自动检测~"
                
                # 更新Notion属性
                notion.pages.update(
                    page["id"],
                    properties={
                        "Status": {"select": {"name": new_status}},
                        "LAST-CHECK": {"rich_text": [{"text": {"content": last_check_text}}]}
                    }
                )
                print(f"更新: {url_property} → {new_status} | {last_check_text}")
                time.sleep(0.5)  # 控制请求频率
        if not query.get("has_more"):
            break
        cursor = query.get("next_cursor")

if __name__ == "__main__":
    update_status()
