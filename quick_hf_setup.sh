#!/bin/bash

echo "=========================================="
echo "🤗 HUGGINGFACE PRO SETUP"
echo "=========================================="
echo ""
echo "1. Go to: https://huggingface.co/settings/tokens"
echo "2. Create a new token (or copy existing one)"
echo "3. Paste it below:"
echo ""
read -p "Enter your HuggingFace API key: " HF_KEY

# Export for current session
export HUGGINGFACE_API_KEY="$HF_KEY"

# Update .env.yaml
echo ""
echo "Updating .env.yaml..."
sed -i.bak "s/HUGGINGFACE_API_KEY: \".*\"/HUGGINGFACE_API_KEY: \"$HF_KEY\"/" .env.yaml

# Test the key
echo ""
echo "Testing API key..."
python3 -c "
import requests
headers = {'Authorization': f'Bearer $HF_KEY'}
r = requests.get('https://huggingface.co/api/whoami', headers=headers)
if r.status_code == 200:
    data = r.json()
    print(f'✅ Authenticated as: {data.get(\"name\")}')
else:
    print('❌ Authentication failed')
"

echo ""
echo "Ready to run: python3 setup_hf_vectorizer_fixed.py"