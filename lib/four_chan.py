import requests
import re
import html

def download_and_extract_json(url):
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
            'resto': []
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
        
        extracted_posts.append(extracted_post)
    return extracted_posts

def four_chan_scrape(thread_id,board):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    extracted_data = download_and_extract_json(url)
    
    extracted_content = ""
    for post in extracted_data:
        post_content = f"No:{post['no']},"
        if post['resto']:
            post_content += f"Reply: {','.join(post['resto'])},"
        post_content += f"Msg:{post['com']}\n"
        extracted_content += post_content
    
    return(extracted_content)

# 示例使用
# four_chan_scrape(12345678)
