const express = require('express');
const WebSocket = require('ws');
const app = express();

const DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a';

// Serve static HTML
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html>
<head>
    <title>Deepgram Nova-3 Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        button { padding: 15px 30px; font-size: 18px; margin: 10px; cursor: pointer; }
        #startBtn { background: #28a745; color: white; border: none; border-radius: 5px; }
        #stopBtn { background: #dc3545; color: white; border: none; border-radius: 5px; }
        button:disabled { background: #ccc; }
        .transcript { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; min-height: 200px; }
        .ethnic { background: #28a745; color: white; padding: 2px 6px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Deepgram Nova-3 Ethnic Products Test</h1>
        <p>Try saying: "I need paneer and ghee" or "Do you have kimchi?"</p>
        <button id="startBtn" onclick="start()">Start Recording</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop</button>
        <div class="transcript" id="transcript">Transcripts will appear here...</div>
    </div>
    <script>
        let ws, mediaRecorder, stream;
        
        async function start() {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            ws = new WebSocket('ws://localhost:9999/stream');
            
            ws.onopen = () => {
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => {
                    if (e.data.size > 0) ws.send(e.data);
                };
                mediaRecorder.start(100);
            };
            
            ws.onmessage = e => {
                const data = JSON.parse(e.data);
                if (data.transcript) {
                    let text = data.transcript;
                    ['paneer', 'ghee', 'kimchi', 'harissa', 'gochujang'].forEach(p => {
                        text = text.replace(new RegExp(p, 'gi'), '<span class="ethnic">' + p + '</span>');
                    });
                    document.getElementById('transcript').innerHTML += '<div>' + text + '</div>';
                }
            };
        }
        
        function stop() {
            if (mediaRecorder) mediaRecorder.stop();
            if (stream) stream.getTracks().forEach(t => t.stop());
            if (ws) ws.close();
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
    </script>
</body>
</html>
    `);
});

// WebSocket proxy
const wss = new WebSocket.Server({ port: 9999, path: '/stream' });

wss.on('connection', (ws) => {
    console.log('Client connected');
    
    // Connect to Deepgram
    const deepgramUrl = 'wss://api.deepgram.com/v1/listen?' +
        'model=nova-3&language=en-US&punctuate=true&' +
        'keyterm=paneer:15&keyterm=ghee:15&keyterm=kimchi:12&keyterm=harissa:15';
    
    const deepgramWs = new WebSocket(deepgramUrl, {
        headers: { 'Authorization': 'Token ' + DEEPGRAM_API_KEY }
    });
    
    deepgramWs.on('open', () => {
        console.log('Connected to Deepgram');
    });
    
    deepgramWs.on('message', (data) => {
        const response = JSON.parse(data);
        if (response.channel && response.channel.alternatives[0].transcript && response.is_final) {
            ws.send(JSON.stringify({
                transcript: response.channel.alternatives[0].transcript
            }));
        }
    });
    
    ws.on('message', async (data) => {
        // Convert blob to buffer if needed
        if (data instanceof Blob) {
            data = Buffer.from(await data.arrayBuffer());
        }
        deepgramWs.send(data);
    });
    
    ws.on('close', () => {
        deepgramWs.close();
        console.log('Client disconnected');
    });
});

app.listen(9999, () => {
    console.log('Server running at http://localhost:9999');
    console.log('Open your browser and click Start Recording');
});