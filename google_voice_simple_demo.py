"""
Simple Google Cloud Speech-to-Text and Text-to-Speech Demo
Following Google's official documentation
"""
from google.cloud import speech
from google.cloud import texttospeech
import pyaudio
import wave
import io

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    print(f"Recording for {duration} seconds...")
    
    # Audio recording parameters
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    
    for i in range(0, int(sample_rate / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("Recording complete")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Convert to bytes
    audio_data = b''.join(frames)
    return audio_data

def transcribe_audio(audio_data, sample_rate=16000):
    """Transcribe audio using Google STT"""
    client = speech.SpeechClient()
    
    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )
    
    print("Transcribing...")
    response = client.recognize(config=config, audio=audio)
    
    transcripts = []
    for result in response.results:
        transcripts.append(result.alternatives[0].transcript)
    
    return " ".join(transcripts)

def synthesize_speech(text, output_file="response.mp3"):
    """Convert text to speech using Google TTS"""
    client = texttospeech.TextToSpeechClient()
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-D",  # Nice voice option
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    
    # Select the audio format
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    print("Generating speech...")
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    # Save the audio
    with open(output_file, "wb") as out:
        out.write(response.audio_content)
    
    print(f"Audio saved to {output_file}")
    return response.audio_content

def main():
    """Simple demo flow"""
    print("=== Google Cloud Voice Demo ===")
    print("This demo will:")
    print("1. Record your voice for 5 seconds")
    print("2. Transcribe it using Google STT")
    print("3. Generate a response")
    print("4. Convert response to speech using Google TTS")
    print()
    
    try:
        # Step 1: Record audio
        input("Press Enter to start recording...")
        audio_data = record_audio(duration=5)
        
        # Step 2: Transcribe
        transcript = transcribe_audio(audio_data)
        print(f"\nYou said: {transcript}")
        
        # Step 3: Generate simple response (no AI, just echo)
        if transcript:
            response = f"I heard you say: {transcript}. This is a test of Google Cloud Speech services."
        else:
            response = "I didn't catch that. Please try speaking again."
        
        print(f"\nResponse: {response}")
        
        # Step 4: Convert to speech
        synthesize_speech(response)
        
        print("\nDemo complete! Check 'response.mp3' for the audio response.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Google Cloud credentials set up")
        print("2. pyaudio installed (pip install pyaudio)")
        print("3. Microphone permissions granted")

if __name__ == "__main__":
    main()