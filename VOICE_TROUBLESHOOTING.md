# Voice Implementation Troubleshooting Guide

## Current Issue: "This site can't be reached"

### Symptoms
- Server starts successfully
- API endpoints work (curl http://localhost:8080/api/v1/google-test/health returns OK)
- Browser cannot access static HTML files
- "This site can't be reached" error in browser

### Possible Causes & Solutions

#### 1. Static Files Not Mounted Correctly
Check in `/src/api/main.py`:
```python
# Should have:
app.mount("/static", StaticFiles(directory="src/static"), name="static")
```

#### 2. Wrong URL Path
Try these URLs:
- http://localhost:8080/static/voice_google_test.html ✓ (should work)
- http://localhost:8080/voice_google_test.html ✗ (won't work)
- http://127.0.0.1:8080/static/voice_google_test.html (try IP)

#### 3. Browser Issues
- Clear browser cache
- Try incognito/private mode
- Try different browser
- Check browser console for errors

#### 4. Firewall/Security
- Check macOS firewall settings
- Check if Python has network permissions
- Try: `sudo lsof -i :8080` to see what's listening

#### 5. Server Process Issues
The server showed repeated errors:
```
"Cannot call "receive" once a disconnect message has been received"
```
This suggests WebSocket connection issues that might be blocking the server.

### Quick Debug Steps

1. **Check if server is truly running:**
```bash
ps aux | grep run.py
lsof -i :8080
```

2. **Test static file serving:**
```bash
curl -v http://localhost:8080/static/voice_google_test.html
```

3. **Check server logs:**
```bash
tail -f server.log | grep -E "(GET|POST|static|404|500)"
```

4. **Test with simple HTTP server:**
```bash
cd src/static
python3 -m http.server 8081
# Then visit http://localhost:8081/voice_google_test.html
```

5. **Check FastAPI static mount:**
Look for this line in server startup logs:
```
Static files mounted from: /Users/adi/Desktop/LeafLoafLangGraph/src/static
```

### If All Else Fails

1. **Restart everything:**
```bash
pkill -f python
python3 run.py
```

2. **Use ngrok for external access:**
```bash
ngrok http 8080
# Use the ngrok URL instead
```

3. **Run simplified test server:**
Create a minimal FastAPI app just for testing static files.

### WebSocket Error Fix

The "Cannot call receive" error suggests the WebSocket handler needs better cleanup:

```python
try:
    # WebSocket code
except WebSocketDisconnect:
    logger.info("WebSocket disconnected")
finally:
    # Ensure proper cleanup
    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.close()
```

## For Tomorrow

1. First, verify server is cleanly running without errors
2. Test static file access with curl
3. If curl works but browser doesn't, it's a browser/network issue
4. If curl fails too, it's a server configuration issue
5. Consider adding explicit static file routes as fallback