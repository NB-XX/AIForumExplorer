import requests
import streamlit as st

# api_key = st.secrets["ocr_api_key"]
api_key ='helloworld'

def ocr_space_file(filename, overlay=False, api_key=api_key,language='chs'):
    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    if r.get('IsErroredOnProcessing'):
        return "OCR识别失败。"
    else:
        return r['ParsedResults'][0]['ParsedText']

def ocr_space_url(url, overlay=False, api_key=api_key, language='chs'):

    payload = {'url': url,
               'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    r = requests.post('https://api.ocr.space/parse/image',
                      data=payload,
                      ).json()
    if r.get('IsErroredOnProcessing'):
        return "OCR识别失败。"
    else:
        return r['ParsedResults'][0]['ParsedText']


# Use examples:
# print(ocr_space_url(url='https://img.saraba1st.com/forum/202404/03/181048lglk2tikv1pqvpg2.png'))