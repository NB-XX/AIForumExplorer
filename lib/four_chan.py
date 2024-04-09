import requests
import re
import html

def download_and_extract_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  
        return response.json()
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return None
    except ValueError as e:
        print(f"解析JSON出错: {e}")
        return None

def extract_posts(data):
    if data is None:
        return []

    extracted_posts = []
    for post in data.get('posts', []):
        com = post.get('com', '')
        links = re.findall(r'<a href=\"#p(\d+)\" class=\"quotelink\">&gt;&gt;\d+</a>', com)
        resto = links
        com = re.sub(r'<a href=\"#p\d+\" class=\"quotelink\">(&gt;&gt;\d+)</a>', '', com)
        com = re.sub(r'<span class=\"quote\">&gt;([^<]+)</span>', r'> \1', com)
        com = com.replace('<br>', '\n')
        com = re.sub(r'<[^>]+>', '', com)  
        com = html.unescape(com)

        # 剔除非空回复
        if com.strip():
            extracted_posts.append({
                'no': post.get('no'),
                'com': com,
                'resto': resto
            })
    return extracted_posts


def four_chan_scrape(thread_id, board):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    data = download_and_extract_json(url)
    extracted_posts = extract_posts(data)
    
    extracted_content = ""
    for post in extracted_posts:
        post_content = f"No:{post['no']},"
        if post['resto']:
            post_content += f"Reply: {','.join(post['resto'])},"
        post_content += f"Msg:{post['com']}\n"
        extracted_content += post_content
    
    return extracted_content


# 示例使用
# print(four_chan_scrape('73295476','vt'))
