# Multilingual TTS and Code-Switching Research

## Executive Summary

Deepgram's current TTS offering only supports English and Spanish voices. For proper Hindi, Gujarati, Korean, and code-switching support, we need to integrate additional TTS services that offer language-specific voices.

## Current Limitations

### Deepgram TTS
- **Available Languages**: English, Spanish only
- **Voices**: 
  - English: aura-asteria-en, aura-luna-en, aura-stella-en, aura-orion-en, aura-arcas-en
  - Spanish: aura-sofia-es, aura-mateo-es
- **Issue**: Cannot pronounce Hindi, Gujarati, or Korean text properly

## Code-Switching Challenges

### What is Code-Switching?
Code-switching is when speakers alternate between two or more languages within a single conversation or utterance.

**Examples**:
- "I need some दाल and rice" (English + Hindi)
- "오늘 special पर क्या है?" (Korean + Hindi)
- "Get me 2 kg આંટા please" (English + Gujarati)

### Technical Challenges
1. **Language Detection**: Need to identify which parts are in which language
2. **Voice Selection**: Different TTS engines for different language segments
3. **Seamless Blending**: Natural transitions between voices
4. **Pronunciation**: Proper handling of transliterated words

## Alternative TTS Solutions

### 1. Google Cloud Text-to-Speech
**Pros**:
- Extensive language support (220+ voices in 40+ languages)
- Hindi, Gujarati, Korean voices available
- WaveNet and Neural2 models for natural speech
- Supports SSML for fine control

**Language Support**:
```python
# Hindi voices
"hi-IN-Standard-A" (Female)
"hi-IN-Standard-B" (Male)
"hi-IN-Wavenet-A" (Female, higher quality)
"hi-IN-Wavenet-B" (Male, higher quality)

# Gujarati voices  
"gu-IN-Standard-A" (Female)
"gu-IN-Standard-B" (Male)

# Korean voices
"ko-KR-Standard-A" (Female)
"ko-KR-Standard-B" (Female)
"ko-KR-Standard-C" (Male)
"ko-KR-Wavenet-A" (Female, higher quality)
```

**Implementation**:
```python
from google.cloud import texttospeech

def google_tts(text: str, language_code: str) -> bytes:
    client = texttospeech.TextToSpeechClient()
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=f"{language_code}-Wavenet-A"
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content
```

### 2. Amazon Polly
**Pros**:
- Good language coverage
- Neural voices for some languages
- SSML support
- Reasonable pricing

**Language Support**:
```python
# Hindi
"Aditi" (Female, Standard)

# Korean  
"Seoyeon" (Female, Neural)

# No Gujarati support
```

### 3. Azure Cognitive Services Speech
**Pros**:
- Excellent language coverage
- Neural voices
- Real-time streaming
- Custom voice creation

**Language Support**:
```python
# Hindi
"hi-IN-MadhurNeural" (Male)
"hi-IN-SwaraNeural" (Female)

# Gujarati
"gu-IN-DhwaniNeural" (Female)
"gu-IN-NiranjanNeural" (Male)

# Korean
"ko-KR-InJoonNeural" (Male)
"ko-KR-SunHiNeural" (Female)
```

### 4. Eleven Labs Multilingual
**Pros**:
- High-quality voices
- Multilingual v2 model
- Single voice can speak multiple languages

**Limitations**:
- Limited API for language-specific control
- Better for single-language content

## Recommended Architecture

### 1. Hybrid Approach
```python
class MultilingualTTS:
    def __init__(self):
        self.deepgram = DeepgramTTS()  # English/Spanish
        self.google = GoogleTTS()      # Hindi/Gujarati/Korean
        self.language_detector = LanguageDetector()
    
    async def synthesize(self, text: str) -> bytes:
        # Detect language segments
        segments = self.language_detector.detect_segments(text)
        
        audio_parts = []
        for segment in segments:
            if segment.language in ['en', 'es']:
                audio = await self.deepgram.synthesize(segment.text)
            else:
                audio = await self.google.synthesize(
                    segment.text, 
                    segment.language
                )
            audio_parts.append(audio)
        
        # Combine audio segments
        return self.combine_audio(audio_parts)
```

### 2. Language Detection
```python
from langdetect import detect_langs
import regex

def detect_code_switching(text: str) -> List[Segment]:
    """Detect language segments in mixed text"""
    segments = []
    
    # Split by script changes
    pattern = r'(\p{Devanagari}+|\p{Gujarati}+|\p{Hangul}+|[a-zA-Z\s]+)'
    parts = regex.findall(pattern, text)
    
    for part in parts:
        if regex.match(r'\p{Devanagari}', part):
            lang = 'hi'  # Hindi
        elif regex.match(r'\p{Gujarati}', part):
            lang = 'gu'  # Gujarati
        elif regex.match(r'\p{Hangul}', part):
            lang = 'ko'  # Korean
        else:
            lang = 'en'  # Default to English
        
        segments.append(Segment(text=part, language=lang))
    
    return segments
```

### 3. Implementation Strategy

#### Phase 1: Single Language Support
1. Detect primary language of utterance
2. Route to appropriate TTS service
3. Use fallback for unsupported languages

```python
async def text_to_speech_v1(self, text: str) -> bytes:
    # Simple language detection
    primary_lang = detect(text)
    
    if primary_lang == 'hi':
        return await self.google_tts(text, 'hi-IN')
    elif primary_lang == 'gu':
        return await self.google_tts(text, 'gu-IN')
    elif primary_lang == 'ko':
        return await self.google_tts(text, 'ko-KR')
    else:
        return await self.deepgram_tts(text)  # English fallback
```

#### Phase 2: Code-Switching Support
1. Segment text by language
2. Generate audio for each segment
3. Stitch audio together

```python
async def text_to_speech_v2(self, text: str) -> bytes:
    segments = detect_code_switching(text)
    audio_segments = []
    
    for segment in segments:
        audio = await self.synthesize_segment(segment)
        audio_segments.append(audio)
    
    return concatenate_audio(audio_segments)
```

## Quick Implementation Path

### Option 1: Google Cloud TTS Integration (Recommended)
```bash
# Install
pip install google-cloud-texttospeech

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

### Option 2: Use ElevenLabs Multilingual
```python
# Already have API key
ELEVENLABS_API_KEY = "sk_1a5..."

import requests

def elevenlabs_multilingual_tts(text: str) -> bytes:
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.content
```

## Immediate Next Steps

1. **Test Google Cloud TTS**:
   - Set up service account
   - Test Hindi, Gujarati, Korean voices
   - Measure latency

2. **Implement Language Detection**:
   - Use langdetect or polyglot
   - Handle script-based detection
   - Test with mixed text

3. **Update Voice Pipeline**:
   ```python
   async def text_to_speech(self, text: str) -> bytes:
       # Detect language
       lang = detect_primary_language(text)
       
       # Route to appropriate service
       if lang in ['hi', 'gu', 'ko']:
           return await self.google_tts(text, lang)
       else:
           return await self.deepgram_tts(text)
   ```

## Cost Comparison

| Service | Price per Million Characters | Languages | Quality |
|---------|------------------------------|-----------|---------|
| Deepgram | $15 | 2 | High |
| Google Cloud | $4 (Standard), $16 (WaveNet) | 40+ | Very High |
| Amazon Polly | $4 (Standard), $16 (Neural) | 20+ | High |
| Azure | $16 (Neural) | 70+ | Very High |
| ElevenLabs | $30 | Multilingual | Excellent |

## Conclusion

For immediate implementation:
1. Use Google Cloud TTS for Hindi, Gujarati, Korean
2. Keep Deepgram for English (already integrated)
3. Implement simple language detection
4. Add code-switching support in Phase 2

This provides the best balance of:
- Language coverage
- Voice quality
- Implementation speed
- Cost effectiveness