import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from lib.four_chan import four_chan_scrape
from lib.four_chan import find_previous_threads
from lib.stage1st import S1_scraper
from lib.nga import nga_scraper
from lib.five_chan import five_chan_scraper
import re
import json

if "url_inputs" not in st.session_state:
    st.session_state.url_inputs = [""]
if "urls_to_process" not in st.session_state:
    st.session_state.urls_to_process = []
if "model_choice" not in st.session_state:
    st.session_state.model_choice = "gemini-2.5-pro"

# 加载prompts.json文件
with open("prompts.json", "r") as file:
    prompts = json.load(file)

def generate_content_with_context(initial_prompt, model_choice, max_attempts=3):
    try:
        genai.configure(api_key=st.secrets["api_key"])
        model = genai.GenerativeModel(model_choice)
        attempts = 0
        messages = [{'role': 'user', 'parts': [initial_prompt]}]
        st.write(f"已传入{len(initial_prompt) }字")
        while attempts < max_attempts:
            try:
                response = model.generate_content(
                    messages,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    },
                    generation_config=genai.types.GenerationConfig(temperature=1.0)
                )
            except Exception as api_err:
                # 将API异常报错直接反馈到前台
                return f"模型生成失败：{api_err}", True

            if 'block_reason' in str(response.prompt_feedback):
                st.write(f"被屏蔽{attempts + 1}次: 正常尝试重新输出。{response.prompt_feedback}")
                messages.append({'role':'model','parts':["请指示我"]})
                messages.append({'role': 'user', 'parts': ["继续生成"]})
                attempts += 1
            else:
                try:
                    if response.text:
                        return response.text, False
                    else:
                        return "没有生成内容。", True
                except AttributeError as e:
                    return f"响应解析失败：{e}", True
        return "被屏蔽太多次，完蛋了", True
    except Exception as e:
        # 顶层保护，防止未捕获异常导致页面崩溃
        return f"模型调用发生未预期异常：{e}", True


def build_s1_link_replacement(thread_id):
    def _replace(match):
        numbers = match.group(1).split(',')
        links = [
            f'[[{num}]](https://bbs.saraba1st.com/2b/forum.php?mod=redirect&ptid={thread_id}&authorid=0&postno={num})'
            for num in numbers
        ]
        return ', '.join(links)
    return _replace

def build_4chan_no_link_replacement(board):
    def _replace(match):
        num = match.group(1)
        return f"No:[{num}](https://archive.palanq.win/{board}/post/{num}/)"
    return _replace

# 如需支持 >>123456 的引链，也可启用此替换
def build_4chan_quote_link_replacement(board):
    def _replace(match):
        num = match.group(1)
        return f">>[{num}](https://archive.palanq.win/{board}/post/{num}/)"
    return _replace

# def nga_link_replacement(match):
#     numbers = match.group(1).split(',')
#     links = [f'[[{num}]](https://bbs.nga.cn/read.php?pid={thread_id}&opt={num})' for num in numbers]
#     return ', '.join(links)

# def five_chan_link_replacement(match):
#     numbers = match.group(1).split(',')
#     links = [f'[[{num}]](https://{sever}/test/read.cgi/{board}/{thread_id}/{num})' for num in numbers]
#     return ', '.join(links)

def handle_url(url, use_asagi_fallback=False):

    # 4chan的URL匹配
    match_4chan = re.match(r'https?://boards\.4chan\.org/(\w+)/thread/(\d+)', url)
    if match_4chan:
        board  = match_4chan.group(1)
        thread_id = match_4chan.group(2)
        placeholder = st.empty()  # 创建一个空的占位符
        placeholder.text(f"已识别到4chan{board}板块帖子，串ID: {thread_id}")  # 显示临时消息
        params = {"thread_id":thread_id, "board":board}
        return four_chan_scrape(thread_id, board, use_asagi_fallback), prompts["4chan"], '4chan', params

    # Stage1st的URL匹配
    match_s1 = re.match(r'https?://(?:www\.|bbs\.)?(?:saraba1st\.com|stage1st\.com)/2b/thread-(\d+)-\d+-\d+\.html', url)
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
        return nga_scraper(thread_id), prompts["NGA"],'nga', params

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
st.write("当前版本 v0.1.9 更新日期：2025年9月25日")

st.subheader("输入需要总结的帖子链接")
st.write("支持的站点：4chan、Stage1st、NGA、5ch、jpnkn")

st.markdown(
    """
    <style>
    /* 调整按钮高度以接近输入框 */
    div.stButton > button {
        height: 38px;
        padding: 0 0.6rem;
        margin-top: 0px;
        line-height: 38px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

url_count = len(st.session_state.url_inputs)
for idx in range(url_count):
    cols = st.columns([10, 1])
    input_key = f"url_input_{idx}"
    if input_key not in st.session_state:
        st.session_state[input_key] = st.session_state.url_inputs[idx]
    st.session_state.url_inputs[idx] = cols[0].text_input(
        "帖子链接",
        key=input_key,
        placeholder=f"帖子链接 {idx + 1}",
        label_visibility="collapsed",
    )
    if idx == url_count - 1:
        if cols[1].button("➕", key=f"add_url_input_{idx}", use_container_width=True, help="新增一个帖子链接输入框"):
            st.session_state.url_inputs.append("")
    # 4chan专用：为4chan线程链接提供“往前追踪几个帖子”隐藏选项
    match_4chan = re.match(r'https?://boards\.4chan\.org/(\w+)/thread/(\d+)', st.session_state.url_inputs[idx])
    if match_4chan:
        board_candidate = match_4chan.group(1)
        with st.expander("4chan 选项", expanded=False):
            track_key = f"follow_prev_count_{idx}"
            default_val = int(st.session_state.get(track_key, 0))
            st.number_input(
                "往前追踪几个帖子",
                min_value=0,
                max_value=10,
                value=default_val,
                step=1,
                key=track_key,
                help="沿OP中的 Previous 链接向前查找旧串"
            )

colA, colB = st.columns([1, 1])
with colA:
    use_asagi_fallback = st.checkbox("4chan失败时使用Asagi存档", value=True, help="当原始4chan接口返回404或失败时，自动切换到存档站")
with colB:
    pass

if st.button("开始分析"):
    nonempty = [u.strip() for u in st.session_state.url_inputs if u.strip()]
    if not nonempty:
        st.warning("请至少输入一个有效链接。")
        st.session_state.urls_to_process = []
    else:
        # 扩展：对4chan链接根据选项追溯前序串（索引与原输入框一致，避免错配）
        expanded = []
        for idx, raw_u in enumerate(st.session_state.url_inputs):
            u = raw_u.strip()
            if not u:
                continue
            expanded.append(u)
            m = re.match(r'https?://boards\.4chan\.org/(\w+)/thread/(\d+)', u)
            if m:
                board = m.group(1)
                tid = m.group(2)
                follow_count = int(st.session_state.get(f"follow_prev_count_{idx}", 0))
                if follow_count > 0:
                    prev_list = find_previous_threads(board, tid, max_steps=follow_count, use_asagi_fallback=use_asagi_fallback)
                    # 规范化为标准URL，新在前旧在后
                    for ptid in prev_list:
                        expanded.append(f"https://boards.4chan.org/{board}/thread/{ptid}")
        # 去重并保持顺序
        seen = set()
        ordered = []
        for u in expanded:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        st.session_state.urls_to_process = ordered

model_options = {
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash"
}
model_choice = st.session_state.model_choice
st.caption(f"当前使用模型：{model_options.get(model_choice, model_choice)}")

aggregated_segments = []
failed_urls = []
for idx, url in enumerate(st.session_state.urls_to_process, start=1):
    result = handle_url(url, use_asagi_fallback=use_asagi_fallback)
    if not result:
        failed_urls.append((url, "未匹配到正确帖子链接"))
        continue
    extracted_content, site_prompt, parser_name, params = result
    if not extracted_content:
        failed_urls.append((url, "获取内容失败"))
        continue
    aggregated_segments.append({
        "url": url,
        "prompt": site_prompt,
        "content": extracted_content,
        "parser": parser_name,
        "params": params
    })

if failed_urls:
    st.warning("以下链接处理失败：" + "；".join(f"{u}（{reason}）" for u, reason in failed_urls))

if aggregated_segments and model_choice:
    placeholder = st.empty()
    placeholder.text("所有帖子已拉取完毕，正在等待模型生成...")
    combined_prompt_parts = []
    for segment in aggregated_segments:
        combined_prompt_parts.append(
            f"来源：{segment['url']}\n指引：{segment['prompt']}\n内容：{segment['content']}"
        )
    prompt = "\n---\n".join(combined_prompt_parts)
    response_text, blocked = generate_content_with_context(prompt, model_choice)
    placeholder.empty()
    # 仅当 blocked=True（模型调用失败/被屏蔽/解析异常）时展示错误
    if blocked:
        st.error(response_text)
    else:
        # 正常成功路径
        # 1) S1链接替换（仅当唯一S1来源）
        s1_segments = [seg for seg in aggregated_segments if seg["parser"] == "s1"]
        formatted_text = response_text
        if len(s1_segments) == 1:
            s1_tid = s1_segments[0]["params"]["thread_id"]
            pattern_s1 = r'\[(\d+(?:,\d+)*)\]'
            formatted_text = re.sub(pattern_s1, build_s1_link_replacement(s1_tid), formatted_text)

        # 2) 4chan编号与引用替换：按“第一个输入串”的板块判定
        board = None
        if st.session_state.get("urls_to_process"):
            first_url = st.session_state.urls_to_process[0]
            m_board = re.match(r'https?://boards\.4chan\.org/(\w+)/', first_url) or \
                      re.match(r'https?://[^/]+/(\w+)/', first_url)
            if m_board:
                board = m_board.group(1)
        if board:
            # No:123456 或 No: 123456 → 加链接
            pattern_no = r'No:\s*(\d+)'
            formatted_text = re.sub(pattern_no, build_4chan_no_link_replacement(board), formatted_text)
            # >>123456 → 加链接
            pattern_quote = r'>>([0-9]{3,})'
            formatted_text = re.sub(pattern_quote, build_4chan_quote_link_replacement(board), formatted_text)

        st.markdown(formatted_text)
