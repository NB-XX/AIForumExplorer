import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from lib.four_chan import four_chan_scrape
from lib.stage1st import S1_scraper
from lib.nga import nga_scraper
from lib.five_chan import five_chan_scraper
import re
import json

# 加载prompts.json文件
with open("prompts.json", "r") as file:
    prompts = json.load(file)

def handle_url(url):
    # 4chan的URL匹配
    match_4chan = re.match(r'https?://boards\.4chan\.org/(\w+)/thread/(\d+)', url)
    if match_4chan:
        board  = match_4chan.group(1)
        thread_id = match_4chan.group(2)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到4chan{board}板块帖子，串ID: {thread_id}")  # 显示临时消息
        # 调用four_chan_scrape函数
        return four_chan_scrape(thread_id,board), prompts["4chan"]

    # Stage1st的URL匹配
    match_s1 = re.match(r'https?://bbs\.saraba1st\.com/2b/thread-(\d+)-\d+-\d+\.html', url)
    if match_s1:
        thread_id = match_s1.group(1)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到Stage1st帖子，帖子ID: {thread_id}")  # 显示临时消息
        # 调用S1_scraper函数
        return S1_scraper(thread_id), prompts["Stage1st"]
    
    # NGA的URL匹配
    match_nga = re.match(r'https?://(?:bbs\.nga\.cn|nga\.178\.com)/read\.php\?tid=(\d+)', url)
    if match_nga:
        thread_id = match_nga.group(1)  # 提取帖子ID
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到NGA帖子，帖子ID: {thread_id}")  # 显示临时消息
        return nga_scraper(thread_id), prompts["NGA"]

    # 匹配指定格式的URL
    match = re.match(r'https?://([^/]+)/test/read\.cgi/([^/]+)/(\d+)/?', url)
    if match:
        sever = match.group(1)
        board = match.group(2)
        thread_id = match.group(3)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到5ch类网址，来源{sever}的{board}板块，串ID：{thread_id}")  # 打印识别结果
        # 调用fivechan_scraper函数
        return five_chan_scraper(sever, board, thread_id), prompts["5ch"]

    st.write("未匹配到正确帖子链接.")

st.title("TL;DR——你的生命很宝贵")
st.write("当前版本 v0.1.0 更新日期：2024日4月6日")
url = st.text_input(r"请输入4Chan\Stage1st\NGA\5ch类帖子链接:")
# 模型选择
model_options = {
    "gemini-1.5-pro-latest": "Gemini 1.5 Pro (每分钟2次查询，每天1000次查询)",
    "gemini-1.0-pro-latest": "Gemini 1.0 Pro (每分钟1次查询，无每天查询限制)"
}
model_choice = st.selectbox(
    "请选择模型：",
    options=list(model_options.keys()),
    format_func=lambda x: f"{x} ({model_options[x]})"  # 显示选项和描述
)

if st.button("切换模型"):
    st.success(f"切换模型成功: {model_choice}")

if url:
    extracted_content,site_prompt = handle_url(url)
    if extracted_content and model_choice:
        # 在模型生成结果之前显示临时消息
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text("帖子已拉取完毕，正在等待模型生成...")  # 显示临时消息
        genai.configure(api_key=st.secrets["api_key"])
        model = genai.GenerativeModel(model_choice)  # 使用用户选择的模型
        prompt = f"{site_prompt}+{extracted_content}"
        response = model.generate_content(prompt,safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        })
        placeholder.empty()  # 清除临时消息
        st.markdown(response.text)  # 显示模型生成的内容
