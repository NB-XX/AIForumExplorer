import requests
import html
import re
import streamlit as st
from datetime import datetime, timedelta
import pytz

def convert_cookies(cookies_str):
    """将cookie字符串转换为字典格式。"""
    return dict(cookie.split('=', 1) for cookie in cookies_str.split('; '))

def fetch_json_data(url, tid, page, cookies):
    """通用请求函数，获取JSON数据。"""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'page': page, 'tid': tid}
    response = requests.post(url, headers=headers, data=data, cookies=cookies)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def fetch_post_info(tid, cookies): 
    """获取帖子基本信息，包括总页数和标题。"""
    base_url = "https://ngabbs.com/app_api.php?__lib=post&__act=list"
    json_data = fetch_json_data(base_url, tid, 1, cookies)
    total_pages = json_data.get('totalPage', 1)
    title = json_data.get('tsubject', "Unknown Title")
    return total_pages, title

def fetch_posts(tid, total_pages, cookies):
    """获取所有帖子的内容。"""
    base_url = "https://ngabbs.com/app_api.php?__lib=post&__act=list"
    posts = []
    for page in range(1, total_pages + 1):
        json_data = fetch_json_data(base_url, tid, page, cookies)
        posts.extend(json_data.get('result', []))
    return posts

def process_posts(posts):
    """处理和格式化帖子内容。"""
    pid_to_no = {post['pid']: post['lou'] + 1 for post in posts}
    extracted_content = []
    beijing = pytz.timezone('Asia/Shanghai')

    for post in posts:
        pid, lou, author = post['pid'], post['lou'], post['author']['username']
        no = lou + 1  
        content = html.unescape(post['content'])
        content = re.sub(r'\[s:[^\]]+\]', '', content)
        content = re.sub(r'\[img\].*?\[\/img\]', '', content)
        quotes = re.findall(r'\[quote\]\[pid=(\d+),\d+,\d+\]Reply\[\/pid\]', content)
        resto = ', '.join(str(pid_to_no.get(int(q), '')) for q in quotes)
        content = re.sub(r'\[quote\].*?\[\/quote\]', '', content).strip()
        postdate = datetime.fromtimestamp(post['postdate'], beijing).strftime('%Y-%m-%d %H:%M')
        extracted_content.append(f"Pid:{pid}, No:{no}, Author:{author}, Reply:{resto}, Msg:{content}, PostDate:{postdate}")

    return "\n".join(extracted_content)

def filter_posts_by_date(posts, date_filter):
    """根据时间过滤帖子。"""
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    if date_filter == 'day':
        time_threshold = now - timedelta(days=1)
    elif date_filter == 'week':
        time_threshold = now - timedelta(weeks=1)
    elif date_filter == 'month':
        time_threshold = now - timedelta(days=30)
    else:
        return posts  # 不进行过滤

    filtered_posts = [post for post in posts if datetime.fromtimestamp(post['postdate'], pytz.timezone('Asia/Shanghai')) >= time_threshold]
    return filtered_posts

def nga_scraper(tid, date_filter='none'):
    """主函数，执行Nga论坛的抓取任务。"""
    cookies_str = st.secrets["ngacookies"]
    cookies = convert_cookies(cookies_str)
    total_pages, title = fetch_post_info(tid, cookies)
    posts = fetch_posts(tid, total_pages, cookies) if total_pages > 0 else []
    if posts:
        posts = filter_posts_by_date(posts, date_filter)
    extracted_content = f"Title: {title}\n{process_posts(posts)}" if posts else "No posts found."
    return extracted_content


# 使用案例
# print(nga_scraper(39730744))