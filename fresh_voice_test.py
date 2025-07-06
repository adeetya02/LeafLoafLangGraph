"""
Fresh start - minimal voice test
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fresh Voice Test</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 600px; 
                margin: 50px auto; 
                padding: 20px;
                text-align: center;
            }
            h1 { color: #333; }
            .status { 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
            }
            .working { background: #d4edda; color: #155724; }
        </style>
    </head>
    <body>
        <h1>🎉 Fresh Voice Test</h1>
        <div class="status working">
            ✅ Server is working on port 7777!
        </div>
        <p>If you can see this, we have a working server.</p>
        <p>Next step: Add voice functionality</p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    port = 7777  # Using a different port
    print(f"\n{'='*50}")
    print(f"🚀 Starting Fresh Voice Test")
    print(f"📍 Open http://localhost:{port}")
    print(f"{'='*50}\n")
    
    uvicorn.run(app, host="127.0.0.1", port=port)