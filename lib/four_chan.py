import requests
import re
import html
from ocr_file import ocr_space_url  # 确保从正确的文件导入ocr_space_url函数

def download_and_extract_json(url,board):
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
        if 'tim' in post and 'fsize' in post and post['fsize'] < 1024 * 1024:
            image_url = f"https://i.4cdn.org/{board}/{post['tim']}{post['ext']}"
            # 调用OCR函数处理图片
            ocr_text = ocr_space_url(url=image_url,language='eng')
            extracted_post['img_ocr'] = ocr_text
        
        extracted_posts.append(extracted_post)
    return extracted_posts

def four_chan_scrape(thread_id, board):
    url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
    extracted_data = download_and_extract_json(url,board)
    
    extracted_content = ""
    for post in extracted_data:
        post_content = f"No:{post['no']},"
        if post['resto']:
            post_content += f"Reply: {','.join(post['resto'])},"
        # 添加OCR结果到评论前
        if post['img_ocr']:
            post_content += f"Msg:[img:{post['img_ocr']}] {post['com']}\n"
        else:
            post_content += f"Msg:{post['com']}\n"
        extracted_content += post_content
    
    return extracted_content

# 示例使用
# print(four_chan_scrape(12345678, 'b'))
