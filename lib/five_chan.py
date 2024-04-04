import requests
import html
import re

def download_dat(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"请求错误: {e}")
        return None
    
def format_post(raw_text):
    floors = re.split(r'名無しさん', raw_text)[1:] 
    extracted_content = []
    for index, floor in enumerate(floors):
        author_match = re.search(r'ID:([^\s<>]+)', floor)
        author = author_match.group(1) if author_match else ''
        
        resto_match = re.search(r'&gt;&gt;(\d+)<br>', floor)
        resto = resto_match.group(1) if resto_match else ''

        content_start = floor.find(f"ID:{author}<>") + len(f"ID:{author}<>")
        content_end = floor.rfind("<>")
        content = floor[content_start:content_end]
        
        content = re.sub(r'&gt;&gt;\d+<br>', '', content)
        content = content.replace('<br>', '\n')
        com = html.unescape(content.strip())

        extracted_content.append(f"No:{index+1},Author:{author},Reply:{resto},Msg:{com}")
    
    return '\n'.join(extracted_content)  # 返回所有楼层内容的长字符串

def five_chan_scraper(sever,board,thread_id):
    if 'jpnkn' in sever:
        url = f"https://{sever}/{board}/dat/{thread_id}.dat"
    elif '5ch' in sever:
        url = f"https://{sever}/{board}/oyster/{thread_id[0:4]}/{thread_id}.dat"
    else:
        print("未知的服务器。")
        return
    print(f"正在下载{url}")
    post = download_dat(url)
    extracted_content = format_post(post)
    return extracted_content

# 使用案例
# print(fivechan_scraper('egg.5ch.net','streaming', '1669397246'))