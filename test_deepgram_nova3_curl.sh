#!/bin/bash
# Test Deepgram Nova-3 with curl for ethnic products

API_KEY="36a821d351939023aabad9beeaa68b391caa124a"

echo "Testing Deepgram Nova-3 with ethnic product vocabulary"
echo "====================================================="

# Test 1: Create test audio with ethnic products
echo -e "\n1. Creating test audio..."
say "I need paneer and ghee for making curry. Also add some gochujang and kimchi to my cart" -o test_ethnic.aiff
ffmpeg -i test_ethnic.aiff -ar 16000 -ac 1 test_ethnic.wav -y 2>/dev/null

# Test 2: Send to Nova-3 with keyterms
echo -e "\n2. Testing Nova-3 with keyterms..."
curl -s \
  --request POST \
  --header "Authorization: Token $API_KEY" \
  --header "Content-Type: audio/wav" \
  --data-binary @test_ethnic.wav \
  --url "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&punctuate=true&keyterm=paneer:15&keyterm=ghee:15&keyterm=gochujang:15&keyterm=kimchi:12&keyterm=curry:10" \
  | jq '{
    transcript: .results.channels[0].alternatives[0].transcript,
    confidence: .results.channels[0].alternatives[0].confidence,
    model: .metadata.model_info[.metadata.models[0]].name,
    duration: .metadata.duration
  }'

# Test 3: Compare with Nova-2 using keywords
echo -e "\n3. Comparing with Nova-2 (keywords)..."
curl -s \
  --request POST \
  --header "Authorization: Token $API_KEY" \
  --header "Content-Type: audio/wav" \
  --data-binary @test_ethnic.wav \
  --url "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&punctuate=true&keywords=paneer:15,ghee:15,gochujang:15,kimchi:12,curry:10" \
  | jq '{
    transcript: .results.channels[0].alternatives[0].transcript,
    confidence: .results.channels[0].alternatives[0].confidence,
    model: .metadata.model_info[.metadata.models[0]].name
  }'

# Test 4: Test without any boosting
echo -e "\n4. Testing without keyword boosting..."
curl -s \
  --request POST \
  --header "Authorization: Token $API_KEY" \
  --header "Content-Type: audio/wav" \
  --data-binary @test_ethnic.wav \
  --url "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&punctuate=true" \
  | jq '{
    transcript: .results.channels[0].alternatives[0].transcript,
    confidence: .results.channels[0].alternatives[0].confidence
  }'

# Cleanup
rm -f test_ethnic.aiff test_ethnic.wav

echo -e "\nTest complete!"