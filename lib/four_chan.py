import requests
import re
import html
from lib.ocr_api import ocr_space_url  # 确保从正确的文件导入ocr_space_url函数

def download_and_extract_json(url, board):
    try:
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return []
    except ValueError as e:
        print(f"解析JSON出错: {e}")
        return []

    extracted_posts = []
    for post in data.get('posts', []):
        extracted_post = {
            'no': post.get('no'),
            'com': '',
            'resto': [],
            'img_ocr': ''
        }
        if 'com' in post:
            com = post['com']
            links = re.findall(r'<a href=\"#p(\d+)\" class=\"quotelink\">&gt;&gt;\d+</a>', com)
            extracted_post['resto'] = links
            com = re.sub(r'<a href=\"#p\d+\" class=\"quotelink\">(&gt;&gt;\d+)</a>', '', com)
            com = re.sub(r'<span class=\"quote\">&gt;([^<]+)</span>', r'> \1', com)
            com = com.replace('<br>', '\n')
            com = re.sub(r'<[^>]+>', '', com)  
            com = html.unescape(com)  
            extracted_post['com'] = com
        
        # 检查是否有图片且文件大小小于1MB
        # if 'tim' in post and 'fsize' in post and post['fsize'] < 1024 * 1024:
        #     image_url = f"https://i.4cdn.org/{board}/{post['tim']}{post['ext']}"
        #     # 调用OCR函数处理图片
        #     ocr_text = ocr_space_url(url=image_url,language='eng')
        #     print(ocr_text)
        #     extracted_post['img_ocr'] = ocr_text
        
        extracted_posts.append(extracted_post)
    return extracted_posts


def _clean_asagi_comment_to_text(comment_html: str) -> (str, list):
    """将 Asagi/FoolFuuka 风格的评论 HTML 清洗为纯文本，并提取引用楼层。
    返回 (纯文本, 引用pid列表字符串)"""
    if not comment_html:
        return "", []
    links = []
    # 提取锚点形式引用
    for m in re.findall(r'<a[^>]+href=\"#p(\d+)\"[^>]*>[^<]*</a>', comment_html):
        links.append(m)
    # 备用：提取 >>123456 形式
    for m in re.findall(r'&gt;&gt;(\d+)', comment_html):
        links.append(m)
    # 绿字转义
    text = re.sub(r'<span class=\"quote\">&gt;([^<]+)</span>', r'> \1', comment_html)
    # 换行处理
    text = text.replace('<br>', '\n')
    # 去标签
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip(), links


def download_and_extract_json_asagi(board: str, thread_id: str):
    """从 Asagi 存档 API 获取并解析帖子列表到通用结构。"""
    url = f"https://archive.palanq.win/_/api/chan/thread/?board={board}&num={thread_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Asagi 请求出错: {e}")
        return []
    except ValueError as e:
        print(f"Asagi 解析JSON出错: {e}")
        return []

    posts = []
    raw_posts = []
    if isinstance(data, dict):
        if 'posts' in data and isinstance(data['posts'], list):
            raw_posts = data['posts']
        elif 'threads' in data and isinstance(data['threads'], list) and data['threads']:
            # 有些实现可能在 threads[0].posts 下
            t0 = data['threads'][0]
            raw_posts = t0.get('posts', []) if isinstance(t0, dict) else []

    for post in raw_posts:
        post_id = post.get('no') or post.get('num') or post.get('id')
        comment_html = post.get('comment') or post.get('com') or ''
        text, links = _clean_asagi_comment_to_text(comment_html)
        posts.append({
            'no': post_id,
            'com': text,
            'resto': links,
            'img_ocr': ''
        })

    return posts

def four_chan_scrape(thread_id, board, use_asagi_fallback: bool = False):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    extracted_data = download_and_extract_json(url, board)

    if not extracted_data and use_asagi_fallback:
        extracted_data = download_and_extract_json_asagi(board, thread_id)

    extracted_content = ""
    for post in extracted_data:
        post_no = post.get('no', '')
        post_content = f"No:{post_no},"
        if post.get('resto'):
            post_content += f"Reply: {','.join(post['resto'])},"
        # 添加OCR结果到评论前
        if post.get('img_ocr'):
            post_content += f"Msg:[img:{post['img_ocr']}] {post.get('com','')}\n"
        else:
            post_content += f"Msg:{post.get('com','')}\n"
        extracted_content += post_content

    return extracted_content


def fetch_op_comment_4chan(board: str, thread_id: str):
    """获取4chan原生接口的OP评论HTML。如果失败返回None。"""
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    posts = data.get('posts', []) if isinstance(data, dict) else []
    if not posts:
        return None
    # 优先按no匹配OP，否则回退第一个
    op_post = next((p for p in posts if str(p.get('no')) == str(thread_id)), posts[0])
    return op_post.get('com')


def fetch_op_comment_asagi(board: str, thread_id: str):
    """获取Asagi存档接口的OP评论HTML（优先comment_processed）。失败返回None。"""
    url = f"https://archive.palanq.win/_/api/chan/thread/?board={board}&num={thread_id}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    # 结构为 { "thread_id": { "op": {...}, "posts": {...} } }
    tkey = str(thread_id)
    tnode = data.get(tkey)
    if not isinstance(tnode, dict):
        # 有些实现可能直接是包含threads/posts数组的形式（兼容性弱处理）
        # 退化为None
        return None
    op = tnode.get('op', {}) if isinstance(tnode.get('op'), dict) else {}
    return op.get('comment_processed') or op.get('comment') or op.get('comment_sanitized')


def fetch_op_comment(board: str, thread_id: str, use_asagi_fallback: bool = False):
    """获取OP评论HTML，优先原生4chan，失败可按开关回退Asagi。"""
    html = fetch_op_comment_4chan(board, thread_id)
    if html is None and use_asagi_fallback:
        html = fetch_op_comment_asagi(board, thread_id)
    return html


def extract_previous_thread_id_from_op(board: str, op_comment_html: str):
    """从OP评论HTML中抽取前序串的thread_id。优先识别 /{board}/thread/NUM，次选 'Previous: >>NUM'。"""
    if not op_comment_html:
        return None
    # 1) 直接thread链接
    m = re.search(r'href=\"/[a-z0-9]+/thread/(\d+)(?:#p\d+)?\"', op_comment_html, re.IGNORECASE)
    if m:
        return m.group(1)
    # 2) Previous: >>NUM（支持HTML转义&gt;）
    m = re.search(r'(?:Previous|Prev)[^<]*?(?:&gt;|>)&gt;&gt;(\d+)', op_comment_html, re.IGNORECASE)
    if m:
        return m.group(1)
    # 3) 宽松回退：出现 >>NUM 时取第一个（风险：可能指向楼层而非OP）
    m = re.search(r'(?:&gt;|>)&gt;&gt;(\d+)', op_comment_html)
    if m:
        return m.group(1)
    return None


def find_previous_threads(board: str, thread_id: str, max_steps: int = 0, use_asagi_fallback: bool = False):
    """沿着OP中的Previous链接向前追溯至多max_steps个串，返回线程ID列表（新->旧）。"""
    results = []
    if max_steps <= 0:
        return results
    visited = set([str(thread_id)])
    current = str(thread_id)
    for _ in range(max_steps):
        op_html = fetch_op_comment(board, current, use_asagi_fallback=use_asagi_fallback)
        if not op_html:
            break
        prev_tid = extract_previous_thread_id_from_op(board, op_html)
        if not prev_tid:
            break
        if prev_tid in visited:
            break
        results.append(prev_tid)
        visited.add(prev_tid)
        current = prev_tid
    return results

# 示例使用
# print(four_chan_scrape(12345678, 'b'))
