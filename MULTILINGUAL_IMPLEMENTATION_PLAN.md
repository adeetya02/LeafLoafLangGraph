# Multilingual TTS Implementation Plan

## Current Status
- ✅ Deepgram STT with Nova-3 multilingual (working)
- ✅ Language detection in transcripts (working)
- ✅ Gemini 1.5 Pro multilingual responses (working)
- ❌ Deepgram TTS only supports English/Spanish
- ❌ ElevenLabs API key invalid

## Immediate Solution (Without Additional APIs)

### 1. Phonetic Approximation Approach
For now, we can use Deepgram's English TTS with phonetic approximations:

```python
def transliterate_to_phonetic(text: str, source_lang: str) -> str:
    """Convert non-English text to phonetic English approximation"""
    
    # Hindi to phonetic mapping
    hindi_phonetic = {
        'नमस्ते': 'namaste',
        'धन्यवाद': 'dhanyawaad',
        'कृपया': 'kripaya',
        'दूध': 'doodh',
        'पनीर': 'paneer',
        'दाल': 'daal',
        'चावल': 'chaawal',
        'आटा': 'aata',
        'घी': 'ghee'
    }
    
    # Gujarati to phonetic mapping
    gujarati_phonetic = {
        'નમસ્તે': 'namaste',
        'આભાર': 'aabhaar',
        'કૃપા કરીને': 'krupa karine',
        'દૂધ': 'doodh',
        'ઘી': 'ghee',
        'દાળ': 'daal',
        'ચોખા': 'chokha',
        'આટો': 'aato'
    }
    
    # Korean to phonetic mapping
    korean_phonetic = {
        '안녕하세요': 'annyeonghaseyo',
        '감사합니다': 'gamsahamnida',
        '김치': 'kimchi',
        '된장': 'doenjang',
        '고추장': 'gochujang',
        '라면': 'ramyeon'
    }
    
    # Apply transliteration
    result = text
    if source_lang == 'hi':
        for hindi, phonetic in hindi_phonetic.items():
            result = result.replace(hindi, phonetic)
    elif source_lang == 'gu':
        for gujarati, phonetic in gujarati_phonetic.items():
            result = result.replace(gujarati, phonetic)
    elif source_lang == 'ko':
        for korean, phonetic in korean_phonetic.items():
            result = result.replace(korean, phonetic)
    
    return result
```

### 2. Language-Aware Response Strategy

```python
async def text_to_speech_fallback(self, text: str, language: str) -> bytes:
    """TTS with fallback strategies"""
    
    if language in ['en', 'es']:
        # Use Deepgram directly
        return await self.deepgram_tts(text)
    
    elif language in ['hi', 'gu', 'ko']:
        # Option 1: Return text-only response with language indicator
        await self.websocket.send_json({
            "type": "text_response",
            "text": text,
            "language": language,
            "message": f"Audio not available for {language}. Displaying text."
        })
        
        # Option 2: Transliterate and use English TTS
        phonetic_text = transliterate_to_phonetic(text, language)
        return await self.deepgram_tts(phonetic_text)
    
    else:
        # Unknown language - use English
        return await self.deepgram_tts("I understood your message but cannot speak in that language yet.")
```

### 3. Enhanced UI for Multilingual Support

Update the HTML interface to better handle multilingual responses:

```javascript
// Show language-specific UI elements
function handleMultilingualResponse(data) {
    if (data.type === 'text_response') {
        // Display text prominently when audio not available
        showTextResponse(data.text, data.language);
        
        // Show language indicator
        showLanguageIndicator(data.language);
        
        // Optional: Play notification sound
        playNotificationSound();
    }
}

// Visual language indicators
function showLanguageIndicator(lang) {
    const indicators = {
        'hi': '🇮🇳 हिन्दी',
        'gu': '🇮🇳 ગુજરાતી', 
        'ko': '🇰🇷 한국어',
        'en': '🇺🇸 English'
    };
    
    document.getElementById('language-indicator').textContent = indicators[lang] || lang;
}
```

## Implementation Phases

### Phase 1: Basic Multilingual (Current Focus)
1. ✅ STT with language detection
2. ✅ LLM responses in detected language
3. 🔄 Phonetic TTS fallback for non-English
4. 🔄 Enhanced UI for text display

### Phase 2: Proper TTS Integration (Future)
1. Set up Google Cloud TTS
2. Implement language-specific voices
3. Handle code-switching properly
4. Add voice selection UI

### Phase 3: Advanced Features
1. Real-time translation
2. Language preference learning
3. Dialect detection
4. Custom voice training

## Next Steps

1. **Update voice_streaming_debug.py** with:
   - Language detection display
   - Phonetic transliteration
   - Text-only fallback for non-English

2. **Enhance UI** with:
   - Language indicators
   - Text prominence for non-audio responses
   - Copy-to-clipboard for non-English text

3. **Test with users** to determine if:
   - Phonetic approximation is acceptable
   - Text-only responses are sufficient
   - Google Cloud TTS integration is necessary

## Alternative Free Options

### 1. gTTS (Google Translate TTS)
```python
from gtts import gTTS

def free_multilingual_tts(text: str, lang: str) -> bytes:
    """Free TTS using Google Translate"""
    tts = gTTS(text=text, lang=lang)
    tts.save("temp_audio.mp3")
    
    with open("temp_audio.mp3", "rb") as f:
        audio_data = f.read()
    
    return audio_data
```

### 2. Edge-TTS (Microsoft Edge)
```python
import edge_tts

async def edge_multilingual_tts(text: str, lang: str) -> bytes:
    """Free TTS using Microsoft Edge"""
    voices = {
        'hi': 'hi-IN-MadhurNeural',
        'gu': 'gu-IN-DhwaniNeural',
        'ko': 'ko-KR-SunHiNeural'
    }
    
    voice = voices.get(lang, 'en-US-AriaNeural')
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("temp_audio.mp3")
    
    with open("temp_audio.mp3", "rb") as f:
        return f.read()
```

## Recommendation

For immediate implementation:
1. Use phonetic transliteration with Deepgram English TTS
2. Display native script text prominently in UI
3. Add "Audio in English accent" disclaimer
4. Test with users to gauge acceptance

For production:
1. Integrate Google Cloud TTS (best language coverage)
2. Implement proper code-switching support
3. Add language preference settings
4. Cache common phrases for performance