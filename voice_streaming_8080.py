"""
Alternative voice streaming server on port 8080
"""
from voice_streaming_deepgram import app
import uvicorn

if __name__ == "__main__":
    print("\n🚀 Starting Voice Server on PORT 8080")
    print("📍 Try: http://localhost:8080")
    print("📍 Or:  http://127.0.0.1:8080")
    print("\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8080)