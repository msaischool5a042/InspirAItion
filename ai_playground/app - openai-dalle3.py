from flask import Flask, render_template, jsonify, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
import threading
from flask_socketio import SocketIO, emit
from datetime import datetime
from boardUpload import add_dream_to_db, Dream, db, User  # boardUpload.py에서 가져오기
from werkzeug.security import generate_password_hash, check_password_hash
from openai import AzureOpenAI
import json
import re
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv(dotenv_path="stt.env")


# Azure Speech 서비스 설정
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

app = Flask(__name__)

app.secret_key = os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dreams.db'  # 데이터베이스 연결
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # SQLAlchemy와 Flask 앱 연결

socketio = SocketIO(app)  # WebSocket 연결 설정

recognized_texts = []  # 인식된 텍스트 저장 리스트
speech_recognizer = None  # 전역 음성 인식 객체
stop_event = threading.Event()  # 음성 인식 종료 이벤트
recognition_thread = None  # 음성 인식 스레드

# Flask 애플리케이션 컨텍스트 내에서 데이터베이스 테이블 생성
with app.app_context():
    db.create_all()

# 음성 인식을 지속적으로 수행하는 함수
def speech_to_text_continuous():
    global recognized_texts, speech_recognizer, stop_event
    recognized_texts = []  # 음성 인식이 시작되면 텍스트 초기화

    try:
        # Azure Speech 설정
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_config.speech_recognition_language = "ko-KR"  # 한글로 음성 인식
        audio_config = speechsdk.AudioConfig(use_default_microphone=True)

        # 음성 인식 객체 생성
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        # 실시간 인식된 텍스트 출력
        def recognized_handler(evt):
            print("실시간 인식된 텍스트:", evt.result.text)
            recognized_texts.append(evt.result.text)  # 인식된 텍스트를 저장
            socketio.emit('recognized_text', {'text': ' '.join(recognized_texts)})  # 클라이언트에 텍스트 전송

        speech_recognizer.recognized.connect(recognized_handler)
        speech_recognizer.start_continuous_recognition()

        print("음성 인식 시작됨")
        stop_event.wait()  # 종료 대기
        speech_recognizer.stop_continuous_recognition()  # 음성 인식 종료
        print("음성 인식 종료됨")

    except Exception as e:
        print(f"음성 인식 중 오류 발생: {e}")
        return
#-------------------------------------------------------------
#STT 변환된 TEXT를 통해 꿈 해몽을 생성하는 함수-----------------
#---------------------------------------------------------------
# Azure OpenAI 설정
# .env 파일 로드
load_dotenv("story_env.env")  # 정확한 경로 확인

# 환경 변수 가져오기
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    raise ValueError("환경 변수가 제대로 설정되지 않았습니다. .env 파일을 확인하세요.")

# AzureOpenAI 클라이언트 초기화
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)
def gpt_response(user_input): 
    try:
        logger.info("Generating GPT response")
        assistant = client.beta.assistants.create(            
            model="team2-gpt-mini",  
            instructions="""
            ## Role
            You are an expert in dream interpretation who provides symbolic meanings and concise interpretations of dreams based on the user's input. 
            Respond in the following JSON format.
            ## JSON Format
            {
            "interpretation": ""
            ---
            ## Instructions
            1. The **interpretation** must always be written in **Korean**.
            2. Use polite and formal language (**존댓말**) for the interpretation.
            3. The interpretation should be concise and limited to approximately **2 sentences**.
            4. Use RAG (retrieval-augmented generation) to find symbolic meanings of dreams and incorporate them into the interpretation naturally.
            5. If no relevant data is found via RAG, create an original interpretation based on the user's dream input while strictly adhering to all restrictions.
            ---
            ## Restrictions
            1. Avoid mentioning "dream" as a theme or referring to waking up from a dream.
            ---
            ## Anonymity Guidelines
            1. Do not mention real-world locations (cities, countries, specific place names) or famous people (real individuals or well-known characters).
            2. Replace user-provided names or locations with fictional names or abstract descriptions.
            ---
            ### Important
            Adhere strictly to all instructions and restrictions outlined above.""",
            tools=[{"type":"file_search","file_search":{"ranking_options":{"ranker":"default_2024_08_21","score_threshold":0}}}],
            tool_resources={"file_search":{"vector_store_ids":["vs_pbD6MOjCO9mhML4X474CoAHQ"]}},
            temperature=1,
            top_p=1
          
        )
        thread = client.beta.threads.create()
    
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
      
        if run.status == 'completed':
            logger.info("GPT response generated successfully")
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            
            for message in reversed(messages.data):
                if message.role == 'assistant':
                    response = message.content[0].text.value
                    
                    ## 뒤에 참고자료가 나와서 정규표현식 사용
                    cleaned_response = re.sub(r'【.*?†source】', '', response)
                    response_json = json.loads(cleaned_response)
                    return response_json
                  
        else:
            logger.error(f"GPT response generation failed with status {run.status}")
            return f"Error: Run failed with status {run.status}"
    except Exception as e:
        logger.error(f"Error during GPT response generation: {e}")
        return f"Error: {str(e)}"


#------------------------------달리------------------------------
load_dotenv("dalle_env.env")

# client = AzureOpenAI(
#     azure_endpoint=os.environ["AZURE_DALLE_ENDPOINT"],
#     api_key=os.environ["AZURE_DALLE_API_KEY"],
#     api_version=os.environ["AZURE_DALLE_API_VERSION"]
# )
        
# 이미지 생성 엔드포인트
@app.route('/generate-image', methods=['POST'])
def generate_image():
    
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_DALLE_ENDPOINT"],
        api_key=os.environ["AZURE_DALLE_API_KEY"],
        api_version=os.environ["AZURE_DALLE_API_VERSION"]
    )
    
    data = request.get_json()
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "프롬프트를 입력하세요"}), 400

    max_retries = 5  # 최대 재시도 횟수, 너무 반복하면 관련없는 내용이 나옴
    attempt = 0

    while attempt < max_retries:
        try:
            # Azure OpenAI DALL·E API 호출
            result = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1
            )
            image_url = result.data[0].url  # 생성된 이미지 URL
            return jsonify({"image_url": image_url})

        except Exception as e:
            # API에서 반환하는 에러 메시지 처리
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = json.loads(e.response.text)
                    error_code = error_response.get('error', {}).get('code', 'unknown')
                except json.JSONDecodeError:
                    return jsonify({"error": "알 수 없는 오류가 발생했습니다."}), 500

                # 429 에러 처리: 재시도 대기 후 반복
                if error_code == '429':
                    time.sleep(1)
                    attempt += 1
                    continue

            # API 응답이 없는 경우
            else:
                return jsonify({"error": "API 응답이 없습니다."}), 500

    # 재시도 초과 시
    return jsonify({"error": "여러 번 시도했지만 이미지를 생성할 수 없습니다."}), 500

#------------------------------------------------------------------------


# 에러 정보를 JSON 파일로 저장하는 함수
def save_error_json(error_code, error_response):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_filename = f"error_{error_code}_{timestamp}.json"
    with open(error_filename, 'w', encoding='utf-8') as f:
        json.dump(error_response, f, ensure_ascii=False, indent=2)


# 3차프로젝트에서 봐야할 것들은 79번 줄 부터 여기까지

# 음성 텍스트 변환 처리
@app.route('/stt', methods=['POST'])
def speech_to_text():
    global recognized_texts, speech_recognizer, stop_event, recognition_thread
    recognized_texts = []  # 이전에 저장된 텍스트 초기화
    stop_event.clear()  # 종료 이벤트 초기화

    # 음성 인식을 백그라운드에서 수행
    recognition_thread = threading.Thread(target=speech_to_text_continuous)
    recognition_thread.start()

    return jsonify({"status": "음성 인식 시작됨"})

# 음성 인식 종료 처리
@app.route('/stop-stt', methods=['POST'])
def stop_speech_to_text():
    global stop_event, speech_recognizer, recognition_thread
    try:
        stop_event.set()  # 종료 이벤트 발생

        # 음성 인식 종료
        if speech_recognizer:
            speech_recognizer.stop_continuous_recognition()

        # 스레드 종료 대기
        if recognition_thread:
            recognition_thread.join()
        
        # 모든 텍스트를 하나로 합침
        combined_text = ' '.join(recognized_texts)

        # 인식된 텍스트를 반환 (저장은 /save-dream에서 처리)
        return jsonify({"status": "음성 인식 종료됨", "recognized_text": combined_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# /get-recognition-result 엔드포인트 추가
@app.route('/get-recognition-result', methods=['GET'])
def get_recognition_result():
    return jsonify({'recognized_text': ' '.join(recognized_texts)})


# 꿈 저장 API
@app.route('/save-dream', methods=['POST'])
def save_dream():
    data = request.json
    title = data.get('title')
    content = data.get('content')

    if not title or not content:
        return jsonify({'error': '제목과 내용은 필수입니다'}), 400

    response = add_dream_to_db(title, content)
    return jsonify({'message': response['message']})

# 편집된 텍스트 저장 API
@app.route('/save-edited-text', methods=['POST'])
def save_edited_text():
    data = request.json
    updated_text = data.get('updated_text')

    if not updated_text:
        return jsonify({'error': '수정된 텍스트가 없습니다.'}), 400

    print("수정된 텍스트:", updated_text)
    return jsonify({'message': '수정된 텍스트가 성공적으로 저장되었습니다.'})

# 꿈 해몽 생성 API ****미완성
@app.route('/generate-story', methods=['POST'])
def generate_story():
    user_input = request.json.get('updated_text')
    print(user_input)
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # GPT를 호출하여 이야기 생성
    try:
        response = gpt_response(user_input)
        if response and "interpretation" in response:
            return jsonify({"story": response["interpretation"]}), 200
        else:
            return jsonify({"error": "Failed to generate story"}), 500
    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



# 페이지 렌더링
@app.route('/home')
def home():
    return render_template('1_home.html')

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/signUp')
def signUp():
    return render_template('signUp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # 로그인 화면 렌더링
    elif request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return jsonify({'message': '로그인 성공'}), 200
        return jsonify({'error': '이메일 또는 비밀번호가 잘못되었습니다.'}), 401
    
@app.route('/save-user', methods=['POST'])
def save_user():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': '모든 필드를 입력해주세요.'}), 400

    # 이메일 중복 검사
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 존재하는 이메일입니다.'}), 400

    # 비밀번호 해시 생성
    hashed_password = generate_password_hash(password)

    # 데이터 저장
    new_user = User(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': '회원가입이 완료되었습니다.'}), 201

@app.route('/start-record', methods=['POST'])
def start_record():
    return redirect(url_for('record'))

@app.route('/record')
def record():
    return render_template('2_record.html')

@app.route('/edit')
def edit():
    return render_template('3_edit__haerim.html')

@app.route('/interpretation1')
def interpretation1():    
    return render_template('4_dream_interpretation.html')

@app.route('/image_generate1')
def image_generate1():
    return render_template('5_image_generation1.html')

@app.route('/story_generate1')
def story_generate1():
    return render_template('6_story_generation1.html')

@app.route('/story_generate2')
def story_generate2():
    return render_template('7_story_generation2.html')

@app.route('/image_generate2')
def image_generate2():
    return render_template('8_image_generation2.html')

@app.route('/dream_gallery')
def dream_gallery():
    dreams = Dream.query.order_by(Dream.timestamp.desc()).all()
    return render_template('1.1_dream_gallery.html', dreams=dreams)

@app.route('/delete_dreams', methods=['POST'])
def delete_dreams():
    try:
        data = request.json
        ids_to_delete = data.get('ids', [])
        if not ids_to_delete:
            return jsonify({'error': '삭제할 항목이 없습니다.'}), 400

        # 데이터베이스에서 꿈 삭제
        Dream.query.filter(Dream.id.in_(ids_to_delete)).delete(synchronize_session='fetch')
        db.session.commit()

        return jsonify({'message': '선택된 꿈이 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application")
    socketio.run(app, debug=True)
