import json
import os
import azure.cognitiveservices.speech as speechsdk

# Azure Speech Service 설정
AZURE_SPEECH_API_KEY = os.getenv("AZURE_SPEECH_API_KEY")
AZURE_SPEECH_SERVICE_REGION = os.getenv("AZURE_SPEECH_SERVICE_REGION")

text_to_synthesize = "Azure를 사용해 텍스트를 음성으로 변환합니다."


def detect_language_and_transcribe():
    print("음성을 입력하세요. (중지하려면 Ctrl+C를 누르세요)")
    # Speech Configuration 설정
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_API_KEY, region=AZURE_SPEECH_SERVICE_REGION
    )
    auto_detect_source_language_config = (
        speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=["en-US", "ko-KR", "ja-JP"]
        )
    )
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        auto_detect_source_language_config=auto_detect_source_language_config,
    )

    print("마이크에서 말하세요...")

    try:
        # 음성을 비동기로 인식 및 언어 감지
        result = speech_recognizer.recognize_once_async().get()

        # 결과 처리
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            detected_language = result.properties[
                speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
            ]
            print(f"감지된 언어: {detected_language}")
            print(f"인식된 텍스트: {result.text}")
            return result.text, detected_language
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("인식된 음성이 없습니다.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"STT 작업이 취소되었습니다. 이유: {cancellation_details.reason}")
            if cancellation_details.error_details:
                print(f"에러 상세 정보: {cancellation_details.error_details}")
    except Exception as e:
        print(f"오류 발생: {e}")
        return None, None


# 실행
# text_to_synthesize, detected_language = detect_language_and_transcribe()


def synthesize_text_to_speech(text, language):
    # Speech 구성 설정
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_API_KEY, region=AZURE_SPEECH_SERVICE_REGION
    )

    # 감지된 언어에 따라 화자 설정
    if language == "en-US":
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    elif language == "ko-KR":
        speech_config.speech_synthesis_voice_name = "ko-KR-SunHiNeural"
    elif language == "ja-JP":
        speech_config.speech_synthesis_voice_name = (
            "ja-JP-NanamiNeural"  # 지원되는 일본어 음성
        )
    else:
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"  # 기본값

    # Audio 설정 (기본 스피커로 출력하거나 파일 저장을 선택 가능)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    # Speech Synthesizer 초기화
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    # 텍스트를 음성으로 변환 및 재생
    result = synthesizer.speak_text_async(text).get()

    # 오류 처리
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("텍스트가 성공적으로 음성으로 변환되었습니다.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"음성 합성 취소: {cancellation_details.reason}")
        if cancellation_details.error_details:
            print(f"에러 상세 정보: {cancellation_details.error_details}")

    # 실행
    # if text_to_synthesize and detected_language:
    #     synthesize_text_to_speech(text_to_synthesize, detected_language)


# for line in story.split("\n"):
#     print(line, end="")
#     synthesize_text_to_speech(line, "ko-KR")


# story.json 파일에서 내용을 읽어와서 처리
def read_story_and_synthesize(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        story = json.load(file)
        for line in story.get("story", "").split("\n"):
            print(line, end="")
            synthesize_text_to_speech(line, "en-US")


# story.json 파일 경로
# story_file_path = "./util/common/story.json"

# story.json 파일의 내용을 읽어와서 음성 합성 실행
# read_story_and_synthesize(story_file_path)


def synthesize_text_to_speech(text: str) -> bytes:
    from django.conf import settings
    import tempfile
    import os

    subscription_key = getattr(
        settings, "AZURE_SPEECH_API_KEY", os.getenv("AZURE_SPEECH_API_KEY")
    )
    region = getattr(
        settings,
        "AZURE_SPEECH_SERVICE_REGION",
        os.getenv("AZURE_SPEECH_SERVICE_REGION"),
    )
    if not subscription_key or not region:
        raise Exception(
            "AZURE_SPEECH_KEY와 AZURE_SPEECH_REGION 환경 변수를 설정하세요."
        )
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)

    # Detect language based on text content
    if any(char in text for char in "가나다라마바사아자차카타파하"):
        speech_config.speech_synthesis_voice_name = "ko-KR-SunHiNeural"
    else:
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    # Use a temporary file to capture synthesized audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_filename = tmp_file.name
    audio_config = speechsdk.audio.AudioOutputConfig(filename=tmp_filename)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        with open(tmp_filename, "rb") as f:
            audio_data = f.read()
        os.remove(tmp_filename)
        return audio_data
    else:
        os.remove(tmp_filename)
        raise Exception(f"음성 합성 실패: {result.error_details}")
