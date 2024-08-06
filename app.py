import streamlit as st
from openai import OpenAI
import time
import re
import base64
from datetime import datetime 
import os

api_key = os.getenv('OPENAI_API_KEY')
assistant_id = os.getenv('ASSISTANT_ID')
# OpenAI 클라이언트 설정
client_openai = OpenAI(api_key=api_key)

# OpenAI Assistant 생성
assistant = client_openai.beta.assistants.retrieve(
    assistant_id=assistant_id
)
thread = client_openai.beta.threads.create()

# 감정 분석 함수
def get_emotion_from_response(response):
    emotion_prompt = [
        {'role': 'system', 'content': 'You are an emotion detection AI. Your task is to determine the emotion conveyed in the given text. Only provide the emotion in lowercase without any punctuation.'},
        {'role': 'user', 'content': f'Emotion of this text: "{response}"? Respond with one of the following: happy, angry, normal, sad, curious'}
    ]
    emotion_response = client_openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=emotion_prompt,
        temperature=0.5,
        max_tokens=10
    )
    emotion = emotion_response.choices[0].message.content.strip().lower()
    emotion = re.sub(r'[^\w\s]', '', emotion)

    allowed_emotions = {'happy', 'angry', 'normal', 'sad', 'curious'}
    
    if emotion not in allowed_emotions:
        emotion = 'happy'

    return emotion

def remove_references(text):
    return re.sub(r"【\d+:\d+†source】", "", text)

def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client_openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

# 이미지를 base64로 인코딩하는 함수
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# CSS를 사용하여 채팅 인터페이스 스타일 지정
def local_css(file_name):
    with open(file_name, "r", encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Streamlit 요소를 숨기는 CSS
def hide_streamlit_elements():
    hide_st_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """
    st.markdown(hide_st_style, unsafe_allow_html=True)

# Streamlit 애플리케이션
def main():
    st.set_page_config(
        page_title="예구구봇",
        page_icon=":speech_balloon:",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    local_css("style.css")
    hide_streamlit_elements()

    st.title("YEGUGU")

    # 프로필 이미지를 base64로 인코딩
    profile_base64 = get_image_base64("logo.png")

    # 세션 상태 초기화
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'input_key' not in st.session_state:
        st.session_state.input_key = 0

    # 채팅 섹션
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-bubble user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="chat-bubble assistant-bubble">
                    <img src="data:image/png;base64,{profile_base64}" class="profile-image">
                    <div class="assistant-content">
                        <div class="assistant-header">
                            <span class="assistant-name">구구</span>
                            <span class="message-time">{message["time"]}</span>
                        </div>
                        <div class="message-content">{message["content"]}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

    # 입력 섹션
    with st.container():
        prompt = st.text_input("메시지를 입력하세요...", key=f"user_input_{st.session_state.input_key}")

    if prompt:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        time_info = f"[현재 시간: {current_time}] "
        prompt_with_time = time_info + prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # AI 응답 생성
        with chat_container:
            st.markdown(f'<div class="chat-bubble user-bubble">{prompt}</div>', unsafe_allow_html=True)
            
            with st.spinner('구구님이 입력하고 있어요...'):
                message_openai = client_openai.beta.threads.messages.create(
                    thread_id=thread.id,
                    role='user',
                    content=prompt_with_time
                )

                run = client_openai.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant.id,
                )

                run = wait_on_run(run, thread)

                messages = client_openai.beta.threads.messages.list(
                    thread_id=thread.id, order="asc", after=message_openai.id
                )

                full_response = ""
                for message_openai in messages:
                    for c in message_openai.content:
                        full_response += c.text.value

                full_response = remove_references(full_response)
                response_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.markdown(f'''
                <div class="chat-bubble assistant-bubble">
                    <img src="data:image/png;base64,{profile_base64}" class="profile-image">
                    <div class="assistant-content">
                        <div class="assistant-header">
                            <span class="assistant-name">구구</span>
                            <span class="message-time">{response_time}</span>
                        </div>
                        <div class="message-content">{full_response}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": full_response, "time": response_time})
        st.session_state.input_key += 1  # 입력 키 증가
        st.experimental_rerun()  # 페이지 리런

if __name__ == "__main__":
    main()
