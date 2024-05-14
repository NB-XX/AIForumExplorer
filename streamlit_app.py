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

def generate_content_with_context(initial_prompt, model_choice, max_attempts=3):
    genai.configure(api_key=st.secrets["api_key"])
    model = genai.GenerativeModel(model_choice)
    attempts = 0
    messages = [{'role': 'user', 'parts': [initial_prompt]}]
    st.write(f"已传入{len(initial_prompt) }字")
    while attempts < max_attempts:
        response = model.generate_content(messages, safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        },generation_config=genai.types.GenerationConfig(temperature=1.0))

        if 'block_reason' in str(response.prompt_feedback):
            st.write(f"被屏蔽{attempts + 1}次: 正常尝试重新输出。{response.prompt_feedback}")
            messages.append({'role':'model','parts':["请指示我"]})
            messages.append({'role': 'user', 'parts': ["继续生成"]})
            attempts += 1
        else:
            try:
                if response.text:  # 直接检查响应文本是否存在
                    return response.text, False
                else:
                    return "没有生成内容。", True
            except AttributeError as e:
                return f"响应解析失败：{e}", True

    return "被屏蔽太多次，完蛋了", True


def s1_link_replacement(match):
    numbers = match.group(1).split(',')
    links = [f'[[{num}]](https://bbs.saraba1st.com/2b/forum.php?mod=redirect&ptid={thread_id}&authorid=0&postno={num})' for num in numbers]
    return ', '.join(links)

# def nga_link_replacement(match):
#     numbers = match.group(1).split(',')
#     links = [f'[[{num}]](https://bbs.nga.cn/read.php?pid={thread_id}&opt={num})' for num in numbers]
#     return ', '.join(links)

# def five_chan_link_replacement(match):
#     numbers = match.group(1).split(',')
#     links = [f'[[{num}]](https://{sever}/test/read.cgi/{board}/{thread_id}/{num})' for num in numbers]
#     return ', '.join(links)

def handle_url(url,date_filter):

    # 4chan的URL匹配
    match_4chan = re.match(r'https?://boards\.4chan\.org/(\w+)/thread/(\d+)', url)
    if match_4chan:
        board  = match_4chan.group(1)
        thread_id = match_4chan.group(2)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到4chan{board}板块帖子，串ID: {thread_id}")  # 显示临时消息
        params = {"thread_id":thread_id, "board":board}
        return four_chan_scrape(thread_id,board), prompts["4chan"], '4chan', params

    # Stage1st的URL匹配
    match_s1 = re.match(r'https?://(?:www\.)?(?:saraba1st|stage1st)\.com/2b/thread-(\d+)-\d+-\d+\.html', url)
    if match_s1:
        thread_id = match_s1.group(1)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到Stage1st帖子，帖子ID: {thread_id}")  # 显示临时消息
        params = {"thread_id":thread_id}
        return S1_scraper(thread_id), prompts["Stage1st"], 's1', params
    
    # NGA的URL匹配
    match_nga = re.match(r'https?://(?:bbs\.nga\.cn|nga\.178\.com|ngabbs\.com)/read\.php\?tid=(\d+)', url)
    if match_nga:
        thread_id = match_nga.group(1)  # 提取帖子ID
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到NGA帖子，帖子ID: {thread_id}")  # 显示临时消息
        params = {"thread_id":thread_id}
        return nga_scraper(thread_id,date_filter), prompts["NGA"],'nga', params

    # 5ch的URL匹配
    match = re.match(r'https?://([^/]+)/test/read\.cgi/([^/]+)/(\d+)/?', url)
    if match:
        sever = match.group(1)
        board = match.group(2)
        thread_id = match.group(3)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到5ch类网址，来源{sever}的{board}板块，串ID：{thread_id}")  # 打印识别结果
        params = {"sever":sever, "board":board, "thread_id":thread_id}
        # 调用fivechan_scraper函数
        return five_chan_scraper(sever, board, thread_id), prompts["5ch"], '5ch', params

    st.write("未匹配到正确帖子链接.")

st.title("TL;DR——你的生命很宝贵")
st.write("当前版本 v0.1.4 更新日期：2024日5月14日")

url = st.text_input(r"请输入4Chan\Stage1st\NGA\5ch类帖子链接:", key="url_input")

# 列布局
col1, col2 = st.columns(2)

with col1:
    # 下拉选择时间筛选选项
    date_filter_options = {
        "none": "不过滤",
        "day": "过去一天",
        "week": "过去一周",
        "month": "过去一月"
    }
    date_filter = st.selectbox(
        "选择时间筛选选项：",
        options=list(date_filter_options.keys()),
        format_func=lambda x: date_filter_options[x]
    )

with col2:
    # 分析按钮
    if st.button("开始分析"):
        st.session_state['url'] = st.session_state['url_input']
        st.session_state['date_filter'] = date_filter


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
    extracted_content, site_prompt, parser_name, params = handle_url(url,date_filter)
    if extracted_content and model_choice:
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text("帖子已拉取完毕，正在等待模型生成...")
        prompt = f"{site_prompt}+{extracted_content}"
        response_text, blocked = generate_content_with_context(prompt, model_choice)
        placeholder.empty()  # 清除临时消息
        if "获取内容失败" in response_text:
            st.error(response_text)
        else:
            if not blocked: # 这里写的实在是太丑陋了 但是我不知道怎么优雅的处理
                if parser_name == "s1":
                    thread_id = params["thread_id"]
                    pattern = r'\[(\d+(?:,\d+)*)\]'
                    formatted_text = re.sub(pattern, s1_link_replacement, response_text)
                    st.markdown(formatted_text)  
                # if parser_name == "nga":
                #     thread_id = params["thread_id"]
                #     board = params["board"]
                #     pattern = r'\[(\d+(?:,\d+)*)\]'
                #     formatted_text = re.sub(pattern, nga_link_replacement, response_text)
                #     st.markdown(formatted_text)
                # if parser_name == "5ch":
                #     sever = params["sever"]
                #     thread_id = params["thread_id"]
                #     pattern = r'\[(\d+(?:,\d+)*)\]'
                #     formatted_text = re.sub(pattern, five_chan_link_replacement, response_text)
                #     st.markdown(formatted_text)
                else:
                    st.write(response_text)
            else:
                st.write(response_text)