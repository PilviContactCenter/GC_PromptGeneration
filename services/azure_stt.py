"""
Azure Speech-to-Text and Translation Service

Uses Azure Cognitive Services Speech SDK to:
1. Transcribe audio to text (in original language)
2. Translate the transcription to English

Uses the same AZURE_SPEECH_KEY and AZURE_SPEECH_REGION from config.
"""
import azure.cognitiveservices.speech as speechsdk
import requests
import tempfile
import os
from config import Config


def transcribe_and_translate(audio_url, source_language=None):
    """
    Downloads audio from URL, transcribes it, and translates to English.
    
    Args:
        audio_url: URL to the audio file (e.g., from Genesys Cloud)
        source_language: Optional source language code (e.g., 'de-DE', 'fr-FR')
                        If None, auto-detection will be attempted
    
    Returns:
        dict with:
            - original_text: Transcription in original language
            - translated_text: English translation
            - detected_language: Detected or specified language code
            - success: Boolean indicating success
            - error: Error message if failed
    """
    if not Config.AZURE_SPEECH_KEY or not Config.AZURE_SPEECH_REGION:
        return {
            'success': False,
            'error': 'Azure Speech credentials are not configured.'
        }
    
    temp_file = None
    try:
        # Download audio file to temporary location
        temp_file = _download_audio(audio_url)
        
        if not temp_file:
            return {
                'success': False,
                'error': 'Failed to download audio file'
            }
        
        # If source language is English, just transcribe (no translation needed)
        if source_language and source_language.lower().startswith('en'):
            result = _transcribe_audio(temp_file, source_language)
            if result['success']:
                result['translated_text'] = result['original_text']
            return result
        
        # For non-English, use translation
        result = _translate_audio(temp_file, source_language)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def _download_audio(audio_url):
    """Downloads audio from URL to a temporary file."""
    try:
        response = requests.get(audio_url, timeout=30)
        response.raise_for_status()
        
        # Create temp file with .wav extension
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        with os.fdopen(fd, 'wb') as f:
            f.write(response.content)
        
        return temp_path
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None


def _transcribe_audio(audio_file, language='en-US'):
    """
    Simple transcription without translation.
    Used when source language is English.
    """
    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=Config.AZURE_SPEECH_KEY,
            region=Config.AZURE_SPEECH_REGION
        )
        speech_config.speech_recognition_language = language
        
        audio_config = speechsdk.AudioConfig(filename=audio_file)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Recognize all speech in the audio
        all_results = []
        done = False
        
        def handle_result(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                all_results.append(evt.result.text)
        
        def handle_session_stopped(evt):
            nonlocal done
            done = True
        
        def handle_canceled(evt):
            nonlocal done
            done = True
        
        recognizer.recognized.connect(handle_result)
        recognizer.session_stopped.connect(handle_session_stopped)
        recognizer.canceled.connect(handle_canceled)
        
        recognizer.start_continuous_recognition()
        
        # Wait for completion (max 60 seconds)
        import time
        timeout = 60
        start = time.time()
        while not done and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        recognizer.stop_continuous_recognition()
        
        full_text = ' '.join(all_results).strip()
        
        if full_text:
            return {
                'success': True,
                'original_text': full_text,
                'translated_text': full_text,
                'detected_language': language
            }
        else:
            return {
                'success': False,
                'error': 'No speech detected in audio'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Transcription failed: {str(e)}'
        }


def _translate_audio(audio_file, source_language=None):
    """
    Transcribes and translates audio to English using Azure Speech Translation.
    """
    try:
        # Map common language codes to Azure format
        language_map = {
            'de-de': 'de-DE',
            'de-at': 'de-AT',
            'de-ch': 'de-CH',
            'fr-fr': 'fr-FR',
            'fr-ca': 'fr-CA',
            'es-es': 'es-ES',
            'es-mx': 'es-MX',
            'it-it': 'it-IT',
            'nl-nl': 'nl-NL',
            'pt-br': 'pt-BR',
            'pt-pt': 'pt-PT',
            'pl-pl': 'pl-PL',
            'ja-jp': 'ja-JP',
            'zh-cn': 'zh-CN',
            'ko-kr': 'ko-KR',
            'ru-ru': 'ru-RU',
            'ar-sa': 'ar-SA',
            'en-us': 'en-US',
            'en-gb': 'en-GB',
            'en-au': 'en-AU',
        }
        
        # Normalize source language
        if source_language:
            source_lang = language_map.get(source_language.lower(), source_language)
            # Extract base language for translation (e.g., 'de-DE' -> 'de')
            base_lang = source_lang.split('-')[0]
        else:
            # Default to German if not specified (common for Genesys prompts)
            base_lang = 'de'
            source_lang = 'de-DE'
        
        # Configure translation
        translation_config = speechsdk.translation.SpeechTranslationConfig(
            subscription=Config.AZURE_SPEECH_KEY,
            region=Config.AZURE_SPEECH_REGION
        )
        translation_config.speech_recognition_language = source_lang
        translation_config.add_target_language('en')  # Translate to English
        
        audio_config = speechsdk.AudioConfig(filename=audio_file)
        
        recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=translation_config,
            audio_config=audio_config
        )
        
        # Collect all results
        original_texts = []
        translated_texts = []
        done = False
        error_msg = None
        
        def handle_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
                original_texts.append(evt.result.text)
                if 'en' in evt.result.translations:
                    translated_texts.append(evt.result.translations['en'])
        
        def handle_canceled(evt):
            nonlocal done, error_msg
            done = True
            if evt.reason == speechsdk.CancellationReason.Error:
                error_msg = f"Translation canceled: {evt.error_details}"
        
        def handle_session_stopped(evt):
            nonlocal done
            done = True
        
        recognizer.recognized.connect(handle_recognized)
        recognizer.canceled.connect(handle_canceled)
        recognizer.session_stopped.connect(handle_session_stopped)
        
        recognizer.start_continuous_recognition()
        
        # Wait for completion (max 60 seconds)
        import time
        timeout = 60
        start = time.time()
        while not done and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        recognizer.stop_continuous_recognition()
        
        if error_msg:
            return {
                'success': False,
                'error': error_msg
            }
        
        original_text = ' '.join(original_texts).strip()
        translated_text = ' '.join(translated_texts).strip()
        
        if original_text or translated_text:
            return {
                'success': True,
                'original_text': original_text or '(No speech detected)',
                'translated_text': translated_text or original_text or '(No translation available)',
                'detected_language': source_lang
            }
        else:
            return {
                'success': False,
                'error': 'No speech detected in audio'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Translation failed: {str(e)}'
        }


def get_supported_languages():
    """Returns list of supported source languages for transcription/translation."""
    return [
        {'code': 'de-de', 'name': 'German (Germany)'},
        {'code': 'de-at', 'name': 'German (Austria)'},
        {'code': 'de-ch', 'name': 'German (Switzerland)'},
        {'code': 'fr-fr', 'name': 'French (France)'},
        {'code': 'fr-ca', 'name': 'French (Canada)'},
        {'code': 'es-es', 'name': 'Spanish (Spain)'},
        {'code': 'es-mx', 'name': 'Spanish (Mexico)'},
        {'code': 'it-it', 'name': 'Italian'},
        {'code': 'nl-nl', 'name': 'Dutch'},
        {'code': 'pt-br', 'name': 'Portuguese (Brazil)'},
        {'code': 'pl-pl', 'name': 'Polish'},
        {'code': 'ja-jp', 'name': 'Japanese'},
        {'code': 'en-us', 'name': 'English (US)'},
        {'code': 'en-gb', 'name': 'English (UK)'},
    ]
