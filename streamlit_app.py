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

# 屏蔽审查和多轮对话功能
def is_content_blocked(prompt_feedback_str):
    return "block_reason: SAFETY" in prompt_feedback_str

def generate_content_with_context(initial_prompt, model_choice, max_attempts=3):
    genai.configure(api_key=st.secrets["api_key"])
    model = genai.GenerativeModel(model_choice)  # 使用用户选择的模型
    attempts = 0
    messages = [{'role': 'user', 'parts': [initial_prompt]}]

    while attempts < max_attempts:
        response = model.generate_content(messages, safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        })
        
        prompt_feedback_str = str(response.prompt_feedback)
        if is_content_blocked(prompt_feedback_str):
            st.write(f"被屏蔽次数{attempts + 1}: 正常尝试重新输出")
            # 尝试多次
            messages.append({'role': 'user', 'parts': ["继续生成"]})
            attempts += 1
        else:
            return response.text, False  
    return "被屏蔽太多次，完蛋了", True

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
st.write("当前版本 v0.1.1 更新日期：2024日4月6日")

url = st.text_input("请输入4Chan\Stage1st\NGA\5ch类帖子链接:", key="url_input")

# 设置触发按钮
if st.button("开始分析"):
    st.session_state['url'] = st.session_state['url_input']

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
# 使用session_state来跟踪对话历史
if 'history' not in st.session_state:
    st.session_state['history'] = []

if url:
    extracted_content, site_prompt = handle_url(url)
    if extracted_content and model_choice:
        if 'initial_prompt' not in st.session_state:
            st.session_state['initial_prompt'] = f"{site_prompt}+{extracted_content}"
        
        # 首次生成内容
        if not st.session_state['history']:
            response_text, blocked = generate_content_with_context(st.session_state['initial_prompt'], model_choice)
            if not blocked:
                st.markdown(response_text)
            else:
                st.write(response_text)
        
        # 为后续输入和按钮预留位置
        input_placeholder = st.empty()
        button_placeholder = st.empty()

        # 如果已有生成内容，则显示继续对话的输入框
        if st.session_state['history'] or not blocked:
            user_input = input_placeholder.text_input("继续对话：", key="new_user_input")
            if button_placeholder.button("提交", key="new_submit"):
                # 更新历史记录
                st.session_state['history'].append(user_input)
                input_placeholder.empty()  # 清除输入框
                button_placeholder.empty()  # 清除按钮

                # 生成新的prompt
                new_prompt = st.session_state['initial_prompt'] + "\n\n".join(st.session_state['history'])
                response_text, blocked = generate_content_with_context(new_prompt, model_choice)
                
                if not blocked:
                    st.markdown(response_text)
                else:
                    st.write(response_text)

        if st.session_state['history']:
            # 显示之前所有的对话和最后的生成内容
            for i, text in enumerate(st.session_state['history'][:-1]):  # 不显示最后一条，因为它已在markdown中显示
                st.text_area(f"Round {i+1}:", value=text, height=75, key=f"round_{i}")