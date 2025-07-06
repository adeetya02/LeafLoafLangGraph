"""
Simple Voice Server - Testing connectivity
"""
import asyncio
from aiohttp import web
import aiohttp
import json
import os

# Set environment
os.environ['DEEPGRAM_API_KEY'] = '36a821d351939023aabad9beeaa68b391caa124a'

async def index(request):
    """Serve the main page"""
    return web.Response(text="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Test - Port 7777</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                text-align: center;
            }
            .status { 
                padding: 20px; 
                margin: 20px; 
                background: #e8f5e9;
                border-radius: 10px;
                font-size: 20px;
            }
            button {
                padding: 15px 30px;
                font-size: 18px;
                margin: 10px;
                cursor: pointer;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            button:hover { background: #45a049; }
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
        <h1>🎤 Voice Test on Port 7777</h1>
        <div class="status">Server is working! ✅</div>
        
        <button onclick="testVoice()">Test Voice</button>
        
        <div class="transcript" id="transcript">Ready to test...</div>
        
        <script>
            async function testVoice() {
                document.getElementById('transcript').innerHTML = 'Testing voice connection...';
                
                try {
                    // Test WebSocket
                    const ws = new WebSocket('ws://localhost:7777/ws');
                    
                    ws.onopen = () => {
                        document.getElementById('transcript').innerHTML = 'WebSocket connected! ✅';
                        ws.send(JSON.stringify({test: 'hello'}));
                    };
                    
                    ws.onmessage = (e) => {
                        const data = JSON.parse(e.data);
                        document.getElementById('transcript').innerHTML = 
                            'Received: ' + JSON.stringify(data);
                    };
                    
                    ws.onerror = (e) => {
                        document.getElementById('transcript').innerHTML = 
                            'WebSocket error! ❌';
                    };
                    
                } catch (error) {
                    document.getElementById('transcript').innerHTML = 
                        'Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """, content_type='text/html')

async def websocket_handler(request):
    """Handle WebSocket connections"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    print("WebSocket client connected")
    await ws.send_json({"status": "connected", "message": "WebSocket is working!"})
    
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = json.loads(msg.data)
            print(f"Received: {data}")
            await ws.send_json({"echo": data, "status": "ok"})
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print(f'WebSocket error: {ws.exception()}')
    
    print("WebSocket client disconnected")
    return ws

def create_app():
    """Create the web application"""
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_handler)
    return app

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting Simple Voice Server")
    print("📍 Open http://localhost:7777")
    print("✅ Using aiohttp for better compatibility")
    print("="*50 + "\n")
    
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=7777)