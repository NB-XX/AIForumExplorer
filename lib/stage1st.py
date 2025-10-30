import requests
import html
import re
from datetime import datetime, timedelta
import streamlit as st
import pytz

def convert_html_to_text(html_content):
    """将HTML内容转换为纯文本，移除或转换一些特定格式。"""
    text = html.unescape(html_content)
    text = re.sub(r'本帖最后由 .*? 于 \d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2} 编辑', '', text)
    text = re.sub('—— 来自 .*$', '', text, flags=re.MULTILINE)
    text = re.sub('----发送自 .*$', '', text, flags=re.MULTILINE)
    text = re.sub('<[^<]+?>', '', text)
    text = text.replace("<br>", "\n").replace("<br />", "\n")
    text = re.sub(r'\n\s*\n', '\n', text)
    return text

def extract_post_data(post, pid_to_position):
    """从单个帖子的数据中提取和处理信息。"""
    post_no = post["position"]
    author = post["author"]
    message = post.get("message", "")
    dateline = datetime.fromtimestamp(int(post['dateline'])).strftime('%Y-%m-%d %H:%M:%S')
    
    # 提取所有引用的pid并转换为帖子位置
    pids = re.findall(r'goto=findpost&amp;pid=(\d+)&amp;', message)
    resto = [str(pid_to_position[int(pid)]) for pid in pids if int(pid) in pid_to_position]
    
    # 移除包含引用pid的<blockquote>
    message = re.sub(r'<div class="quote"><blockquote>.*?goto=findpost&pid=(\d+)&.*?</blockquote></div>', '', message, flags=re.DOTALL)
    
    com = convert_html_to_text(message)
    return {"no": post_no, "author": author, "resto": resto, "com": com, "dateline": dateline}

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

    filtered_posts = [post for post in posts if datetime.strptime(post['dateline'], '%Y-%m-%d %H:%M:%S') >= time_threshold]
    return filtered_posts

def download_json(url, params):
    """下载并返回JSON数据。"""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=params)
    response.raise_for_status()
    return response.json()

def fetch_thread_info(thread_id, sid):
    """获取指定帖子的基本信息。"""
    url = "https://app.stage1st.com/2b/api/app/thread"
    params = {'sid': sid, 'tid': thread_id}
    return download_json(url, params)

def extract_and_format_posts(thread_data):
    """提取帖子数据并格式化输出。"""
    extracted_posts = []
    pid_to_position = {post["pid"]: post["position"] for post in thread_data["data"]["list"]}
    
    for post in thread_data["data"]["list"]:
        extracted_posts.append(extract_post_data(post, pid_to_position))
    
    formatted_posts = []
    for post in extracted_posts:
        resto_str = ",".join(post['resto'])
        post_content = f"No:{post['no']}, Author:{post['author']}, Reply:{resto_str}, Msg:{post['com']}"
        formatted_posts.append(post_content)
    
    return "\n".join(formatted_posts)


def S1_scraper(thread_id, date_filter='none'):
    """主函数，执行S1论坛的抓取任务。"""
    sid = st.secrets["s1sid"]
    thread_info = fetch_thread_info(thread_id, sid)
    
    if not thread_info or not thread_info.get("success"):
        return "Failed to fetch thread info."
    
    replies = int(thread_info["data"]["replies"])
    pageSize = min(1000, replies + 1)  # 最大拉取1000 防止S1暴死
    total_pages = (replies + pageSize - 1) // pageSize 
    url = "https://app.stage1st.com:443/2b/api/app/thread/page"
    
    posts = []
    for page in range(1, total_pages + 1):
        params = {'sid': sid, 'tid': thread_id, 'pageNo': page, 'pageSize': pageSize}
        page_data = download_json(url, params)
        if page_data and page_data.get("success"):
            posts.extend(extract_and_format_posts(page_data))
    
    posts = filter_posts_by_date(posts, date_filter)  # 应用时间过滤
    
    extracted_content = f"Subject: {thread_info['data']['subject']}, Date: {datetime.fromtimestamp(int(thread_info['data']['dateline'])).strftime('%Y-%m-%d %H:%M:%S')}, " \
                        f"Forum: {thread_info['data']['fname']}, Replies: {replies}, Author: {thread_info['data']['author']}\n" + "\n".join(posts)

    return extracted_content


# 示例使用（需要替换为有效的thread_id）
# print(S1_scraper(2178880))
