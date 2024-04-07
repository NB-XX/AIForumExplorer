import requests
import html
import re
from datetime import datetime
import streamlit as st

def extract_json(data):
    extracted_posts = []
    
    # 创建一个pid到position的映射用于处理引用
    pid_to_position = {post["pid"]: post["position"] for post in data["data"]["list"]}
    
    for post in data["data"]["list"]:
        post_no = post["position"]
        author = post["author"]
        message = post.get("message", "")
        
        # 提取所有引用的pid
        pids = re.findall(r'goto=findpost&amp;pid=(\d+)&amp;', message)
        resto = [str(pid_to_position[int(pid)]) for pid in pids if int(pid) in pid_to_position]
        
        # 对包含引用pid的<blockquote>进行移除
        for pid in pids:
            if int(pid) in pid_to_position:
                message = re.sub(f'<div class="quote"><blockquote>.*?goto=findpost&pid={pid}&.*?</blockquote></div>', '', message, flags=re.DOTALL)
        
        # 清理和转换消息内容
        com = html.unescape(message)
        com = re.sub('本帖最后由 .*? 于 \d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2} 编辑', '', com)
        com = re.sub('—— 来自 .*$', '', com, flags=re.MULTILINE)
        com = re.sub('----发送自 .*$', '', com, flags=re.MULTILINE)
        com = re.sub('<[^<]+?>', '', com)
        com = com.replace("<br>", "\n").replace("<br />", "\n")
        com = re.sub('\n\s*\n', '\n', com)
        extracted_posts.append({"no": post_no, "author": author, "resto": resto, "com": com})
    
    return extracted_posts



def download_json(url, params):
    try:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return None
    return data

def timestamp_to_date(timestamp):
    # 将时间戳转换为可读的日期格式
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_thread_info(thread_id, sid="RwyOj3"):
    url = "https://app.saraba1st.com:443/2b/api/app/thread"
    params = {'sid': sid, 'tid': thread_id}
    data = download_json(url, params)
    if data and data["success"]:
        return data["data"]
    else:
        return None

def S1_scraper(thread_id, sid="RwyOj3"):
    thread_info = get_thread_info(thread_id, sid)
    if not thread_info:
        return "Failed to fetch thread info."
    
    replies = int(thread_info["replies"])
    pageSize = min(1000, replies + 1)  # +1考虑到楼主帖子本身，设置pageSize不超过1000
    
    total_pages = (replies + pageSize - 1) // pageSize  # 向上取整计算总页数
    url = "https://app.saraba1st.com:443/2b/api/app/thread/page"
    extracted_content = f"Subject: {thread_info['subject']}, Date: {timestamp_to_date(int(thread_info['dateline']))}, " \
                        f"Forum: {thread_info['fname']}, Replies: {replies}, Author: {thread_info['author']}\n"
    
    for page in range(1, total_pages + 1):
        page_params = {'sid': sid, 'tid': thread_id, 'pageNo': page, 'pageSize': pageSize}
        page_data = download_json(url, page_params)
        if page_data and page_data["success"]:
            extracted_data = extract_json(page_data)
            
            for post in extracted_data:
                if post['resto']:
                    resto_str = ",".join(post['resto'])  # 将resto数组转换为逗号分隔的字符串
                    post_content = f"No:{post['no']}, Author:{post['author']}, Reply:{resto_str}, Msg:{post['com']}\n"
                else:
                    post_content = f"No:{post['no']}, Author:{post['author']}, Msg:{post['com']}\n"
                extracted_content += post_content

    return extracted_content


# 示例使用（需要替换为有效的thread_id）
print(S1_scraper(2178880))
