import os
import requests
import time
from datetime import datetime, timedelta
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["DATABASE_ID"]

def check_site(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=15, allow_redirects=True)
        end_time = time.time()
        open_time_sec = round(end_time - start_time, 2)
        if response.status_code in (200, 403):
            return f"状态：✅正常（{open_time_sec}s）", open_time_sec
        else:
            return f"状态：❓HTTP错误: {response.status_code}", None
    except requests.exceptions.Timeout:
        return "状态：❌超时", None
    except requests.exceptions.ConnectionError:
        return "状态：❌DNS错误", None
    except Exception as e:
        return f"状态：❌异常: {e}", None

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
            page_id = page["id"]
            url_property = page["properties"]["URL-TEXT"]["url"]

            # 新增：主页链接与头像链接
            homepage_cover = page["properties"].get("主页链接", {}).get("url")
            avatar_icon = page["properties"].get("头像链接", {}).get("url")

            update_payload = {
                "properties": {}
            }

            # 检查目标站点状态和打开时间
            new_status, open_time_sec = check_site(url_property)

            # 生成北京时间 (UTC+8)
            utc_now = datetime.utcnow()
            beijing_time = utc_now + timedelta(hours=8)
            formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M")
            last_check_text = f"于 {formatted_time} 自动检测~"

            update_payload["properties"]["Status"] = {"select": {"name": new_status}}
            update_payload["properties"]["LAST-CHECK"] = {"rich_text": [{"text": {"content": last_check_text}}]}
            if open_time_sec is not None:
                update_payload["properties"]["OPEN-TIME"] = {"number": open_time_sec}

            # 设置封面
            if homepage_cover:
                update_payload["cover"] = {
                    "type": "external",
                    "external": {"url": homepage_cover}
                }
                print(f"设置封面: {homepage_cover}")
            # 设置图标
            if avatar_icon:
                update_payload["icon"] = {
                    "type": "external",
                    "external": {"url": avatar_icon}
                }
                print(f"设置图标: {avatar_icon}")

            notion.pages.update(page_id, **update_payload)
            print(f"更新: {url_property} → {new_status} | {last_check_text}")
            time.sleep(0.5)
        if not query.get("has_more"):
            break
        cursor = query.get("next_cursor")

if __name__ == "__main__":
    update_status()
