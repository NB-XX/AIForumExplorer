import requests
import streamlit as st

# 尝试从 Streamlit secrets 获取 api_key，如果失败则使用默认值
try:
    api_key = st.secrets["ocr_api_key"]
except KeyError as e:
    api_key = 'helloworld'
    print(f"无法从secrets获取api_key: {e}")

def ocr_space_file(filename, overlay=False, language='chs', api_key=api_key):
    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    try:
        response = r.json()
        if response.get('IsErroredOnProcessing'):
            return "OCR识别失败。"
        else:
            return response['ParsedResults'][0]['ParsedText']
    except Exception as e:
        return f"处理响应时出错: {str(e)}"

def ocr_space_url(url, overlay=False, language='chs', api_key=api_key):
    payload = {'url': url,
               'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    r = requests.post('https://api.ocr.space/parse/image',
                      data=payload,
                      )
    try:
        response = r.json()
        if response.get('IsErroredOnProcessing'):
            return "OCR识别失败。"
        else:
            return response['ParsedResults'][0]['ParsedText']
    except Exception as e:
        return f"处理响应时出错: {str(e)}"

# 使用示例:
# print(ocr_space_url(url='https://img.saraba1st.com/forum/202404/03/181048lglk2tikv1pqvpg2.png'))
