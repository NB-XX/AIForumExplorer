import requests
import re
import html

def extract_json(data):
    extracted_posts = []
    
    # 创建一个pid到number的映射 用于处理引用
    pid_to_number = {post["pid"]: post["number"] for post in data["Variables"]["postlist"]}
    
    for post in data["Variables"]["postlist"]:
        post_no = post["number"]
        author = post["author"]
        resto = []
        pattern = re.compile(r'pid=(\d+)')
        message = post.get("message", "")
        pids = pattern.findall(message)
        for pid in pids:
            if pid in pid_to_number:
                resto.append(pid_to_number[pid])
        com = re.sub('<blockquote>.*?</blockquote>', '', message, flags=re.DOTALL)
        com = re.sub('本帖最后由 .*? 于 \d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2} 编辑', '', com)
        com = re.sub('—— 来自 .*$', '', com, flags=re.MULTILINE)
        com = re.sub('----发送自 .*$', '', com, flags=re.MULTILINE)
        com = html.unescape(com)
        com = re.sub('<[^<]+?>', '', com)
        com = com.replace("<br>", "\n").replace("<br />", "\n")
        com = re.sub('\n\s*\n', '\n', com)
        extracted_posts.append({"no": post_no, "author": author, "resto": resto, "com": com})
    
    return extracted_posts



def download_json(url):
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
    return data


def S1_scraper(thread_id):
    ppp = 40  # 网页端可以获取超过40的回帖不用遍历 不知道为什么API只能获取40条
    url = f"https://bbs.saraba1st.com/2b/api/mobile/index.php?module=viewthread&ppp={ppp}&tid={thread_id}"
    initial_data = download_json(url)
    total_replies = int(initial_data["Variables"]["thread"]["replies"]) + 1
    total_pages = (total_replies + ppp - 1) // ppp  # 向上取整计算总页数
    
    extracted_content = ""
    
    # 遍历每一页
    for page in range(1, total_pages + 1):
        page_url = f"{url}&page={page}"
        page_data = download_json(page_url)
        extracted_data = extract_json(page_data)
        
        for post in extracted_data:
            post_content = f"No:{post['no']}, Author:{post['author']},"
            if post['resto']:
                post_content += f" Reply:{','.join(post['resto'])},"
            post_content += f" Msg:{post['com']}\n"
            extracted_content += post_content
    
    return extracted_content
# 示例使用
# print(S1_scraper(123456))
