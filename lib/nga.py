import requests
import html
import re
import streamlit as st

# 函数的拆分设计有待优化 应该按照下载和提取分开
def convert_cookies(cookies_str):
    cookies_dict = {}
    for cookie in cookies_str.split('; '):
        key, value = cookie.split('=', 1)
        cookies_dict[key] = value
    return cookies_dict

def fetch_post_info(tid,cookies): 
    base_url = "https://ngabbs.com/app_api.php?__lib=post&__act=list"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookies
    }
    data = {
        'page': 1, 
        'tid': tid,
    }
    response = requests.post(base_url, headers=headers, data=data)
    if response.status_code == 200:
        json_data = response.json()
        total_pages = json_data['totalPage']
        title = json_data['tsubject']
        return total_pages, title
    return 1, "Unknown Title"

def fetch_posts(tid, total_pages,cookies):
    base_url = "https://ngabbs.com/app_api.php?__lib=post&__act=list"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookies
    }
    posts = []

    for page in range(1, total_pages + 1):
        data = {
            'page': page,
            'tid': tid,
        }
        response = requests.post(base_url, headers=headers, data=data)
        if response.status_code == 200:
            posts.extend(response.json()['result'])

    return posts

def process_posts(posts):
    pid_to_no = {}  # PID到楼层编号的映射
    extracted_content = ""
    for post in posts:
        pid = post['pid']
        lou = post['lou']
        no = lou + 1 
        author = post['author']['username']
        pid_to_no[int(pid)] = no

    for post in posts:
        pid = post['pid']
        lou = post['lou']
        no = lou + 1  
        author = post['author']['username']
        content = post['content']

        # 移除HTML标签、表情符号和图片链接
        content = html.unescape(content)
        content = re.sub(r'\[s:[^\]]+\]', '', content)
        content = re.sub(r'\[img\].*?\[\/img\]', '', content)

        quotes = re.findall(r'\[quote\]\[pid=(\d+),\d+,\d+\]Reply\[\/pid\]', content)
        resto = ', '.join(str(pid_to_no[int(q)]) for q in quotes if int(q) in pid_to_no)
        content = re.sub(r'\[quote\].*?\[\/quote\]', '', content)
        com = ' '.join(content.split())

        extracted_content += f"No:{no}, Author:{author}, Reply:{resto}, Msg:{com}\n"
    
    return extracted_content


def nga_scraper(tid):
    cookies_str = st.secrets["ngacookies"]
    cookies = convert_cookies(cookies_str)
    total_pages, title = fetch_post_info(tid,cookies) 
    extracted_content = ""
    if total_pages > 0:
        posts = fetch_posts(tid, total_pages,cookies)
        extracted_content = f"Title：{title}\n"+process_posts(posts)

    return extracted_content

# 使用案例
# print(nga_scraper(39730744))