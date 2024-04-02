import re
import requests

def format_post(post):

  floors = []
  floor_no = 1
  for line in post.splitlines():
    # Extract username
    match = re.search(r"ID:([^<>]+)", line)
    author = match.group(1) if match else None

    # Extract replied floor number
    match = re.search(r">>(?P<resto>\d+)", line)
    resto = match.group("resto") if match else None

    # Extract message content
    msg = re.sub(r"(>>\d+)?<br>.*", "", line).strip()

    floors.append({
        "no": floor_no,
        "author": author,
        "resto": resto,
        "msg": msg,
    })
    floor_no += 1

  return floors

def download_dat(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return ""
  
def holoneet_scraper(thread_id):
    url =f"https://edge.jpnkn.com/hololiveneet/dat/{thread_id}.dat"
    post = download_dat(url)
    formatted_floors = format_post(post)
    for floor in formatted_floors:
        print(f"Floor {floor['no']}")
        print(f"Author: {floor['author']}")
        print(f"Reply to: {floor['resto']}")
        print(f"Message: {floor['msg']}")
        print("-" * 20)

thread_id = input("请输入hololive neet帖子ID: ")
holoneet_scraper(thread_id)