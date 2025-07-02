# Getting Your HuggingFace Pro API Key

## Steps:

1. **Log in to HuggingFace**
   - Go to: https://huggingface.co/login

2. **Navigate to Settings**
   - Click your profile picture (top right)
   - Select "Settings"

3. **Go to Access Tokens**
   - Direct link: https://huggingface.co/settings/tokens
   
4. **Create New Token**
   - Click "New token"
   - Name: "LeafLoaf" (or any name)
   - Type: Select "Read" (or "Write" if you need it)
   - Click "Generate token"

5. **Copy the Token**
   - It will start with `hf_`
   - Copy the ENTIRE token (it's long!)

## Important Notes:

- Make sure you're logged into the account with Pro subscription
- The token should be ~48 characters long
- It will look like: `hf_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst`

## Test Your Token:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" https://huggingface.co/api/whoami
```

You should see your username and account info if it's valid.