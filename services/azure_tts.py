import azure.cognitiveservices.speech as speechsdk
import os
from config import Config

def generate_speech(text, output_path, voice_name="en-US-JennyNeural"):
    """
    Generates speech from text using Azure TTS and saves it to output_path.
    """
    if not Config.AZURE_SPEECH_KEY or not Config.AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech credentials are not configured.")

    speech_config = speechsdk.SpeechConfig(subscription=Config.AZURE_SPEECH_KEY, region=Config.AZURE_SPEECH_REGION)
    speech_config.speech_synthesis_voice_name = voice_name
    
    # Set output to file
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # XML for more control (optional, but good for future) or simple text
    # Using simple text for now
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
        raise Exception(f"TTS Failed: {cancellation_details.reason}")
    
    return False
