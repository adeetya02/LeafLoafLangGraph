"""
Google Cloud Streaming Speech Recognition Demo
Following Google's official streaming documentation
"""
from google.cloud import speech
import queue
import threading

class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""
    
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True
        
    def __enter__(self):
        import pyaudio
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self
        
    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()
        
    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue
        
    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            
            # Now consume whatever else is still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
                    
            yield b"".join(data)

def listen_print_loop(responses):
    """Iterates through server responses and prints them."""
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue
            
        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue
            
        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript
        
        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        if not result.is_final:
            overwrite_chars = " " * (num_chars_printed - len(transcript))
            print(transcript + overwrite_chars + "\r", end="", flush=True)
            num_chars_printed = len(transcript)
        else:
            print(transcript + overwrite_chars)
            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if any(keyword in transcript.lower() for keyword in ["exit", "quit", "stop"]):
                print("Exiting..")
                break
            num_chars_printed = 0

def main():
    """Main function for streaming speech recognition"""
    # Audio recording parameters
    RATE = 16000
    CHUNK = int(RATE / 10)  # 100ms
    
    print("=== Google Cloud Streaming Speech Demo ===")
    print("Start speaking! Say 'exit', 'quit', or 'stop' to end.")
    print()
    
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
        enable_automatic_punctuation=True,
        # Enable voice activity detection
        enable_voice_activity_events=True,
        # Optional: add speech contexts for better recognition
        speech_contexts=[
            speech.SpeechContext(
                phrases=["LeafLoaf", "groceries", "shopping", "organic", "add to cart"],
                boost=20.0,
            ),
        ],
    )
    
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
        # Voice activity detection config
        voice_activity_timeout=speech.StreamingRecognitionConfig.VoiceActivityTimeout(
            speech_begin_timeout={"seconds": 5},
            speech_end_timeout={"seconds": 1},
        ),
    )
    
    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        
        responses = client.streaming_recognize(streaming_config, requests)
        
        # Now, put the transcription responses to use.
        listen_print_loop(responses)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Google Cloud credentials configured")
        print("2. pyaudio installed")
        print("3. Microphone permissions")