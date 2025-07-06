"""
Minimal voice server - no complex imports
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json

app = FastAPI()

@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Minimal Voice Test</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 600px; 
                margin: 50px auto; 
                padding: 20px;
                text-align: center;
            }
            .status { 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
            }
            .connected { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            button { 
                padding: 15px 30px; 
                font-size: 18px; 
                margin: 10px;
                cursor: pointer;
            }
            .transcript {
                background: #f0f0f0;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                min-height: 100px;
            }
        </style>
    </head>
    <body>
        <h1>🎤 Minimal Voice Test</h1>
        <div class="status" id="status">Click Start to begin</div>
        
        <button onclick="startVoice()" id="startBtn">Start Voice</button>
        <button onclick="stopVoice()" id="stopBtn" disabled>Stop</button>
        
        <div class="transcript" id="transcript">Ready...</div>
        
        <script>
            let ws, stream;
            
            async function startVoice() {
                try {
                    // Get microphone
                    stream = await navigator.mediaDevices.getUserMedia({audio: true});
                    
                    // Connect WebSocket
                    ws = new WebSocket('ws://localhost:7777/ws');
                    
                    ws.onopen = () => {
                        document.getElementById('status').textContent = 'Connected!';
                        document.getElementById('status').className = 'status connected';
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('stopBtn').disabled = false;
                        
                        // Send a test message
                        ws.send(JSON.stringify({type: 'start', message: 'Voice started'}));
                    };
                    
                    ws.onmessage = (e) => {
                        const data = JSON.parse(e.data);
                        document.getElementById('transcript').textContent = data.message || JSON.stringify(data);
                    };
                    
                    ws.onerror = (e) => {
                        console.error('WebSocket error:', e);
                        document.getElementById('status').textContent = 'Error!';
                        document.getElementById('status').className = 'status error';
                    };
                    
                    ws.onclose = () => {
                        stopVoice();
                    };
                    
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            function stopVoice() {
                if (stream) {
                    stream.getTracks().forEach(t => t.stop());
                    stream = null;
                }
                if (ws) {
                    ws.close();
                    ws = null;
                }
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status';
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
            }
        </script>
    </body>
    </html>
    """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    
    try:
        # Send initial message
        await websocket.send_json({"message": "WebSocket connected! (No Deepgram yet)"})
        
        while True:
            # Receive data
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back
            await websocket.send_json({
                "message": f"Received: {message}",
                "echo": True
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Minimal Voice Server")
    print("📍 Open http://localhost:7777")
    print("✅ No complex imports - just FastAPI")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=7777)