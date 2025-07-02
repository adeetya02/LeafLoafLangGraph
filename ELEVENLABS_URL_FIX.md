# ElevenLabs URL Configuration Fix

## The "Invalid URL" Issue

When setting up ElevenLabs webhooks, you might see "Invalid URL" error. Here's how to fix it:

### ✅ Correct URL Format

The webhook URLs should be entered **exactly** as shown below:

```
https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/search
```

### ❌ Common Mistakes

1. **Don't add quotes**: 
   - Wrong: `"https://leafloaf..."`
   - Right: `https://leafloaf...`

2. **Don't add spaces**:
   - Wrong: `https://leafloaf... /search`
   - Right: `https://leafloaf.../search`

3. **Don't forget the protocol**:
   - Wrong: `leafloaf-langraph-32905605817...`
   - Right: `https://leafloaf-langraph-32905605817...`

### 📋 Copy-Paste Ready URLs

Copy these exactly:

**Search Products:**
```
https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/search
```

**Add to Cart:**
```
https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/add_to_cart
```

**Show Cart:**
```
https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/show_cart
```

**Confirm Order:**
```
https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/confirm_order
```

### 🧪 Test Each URL First

Before adding to ElevenLabs, test each URL in your browser or with curl:

```bash
# Test search webhook
curl -X POST https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "session_id": "test"}'
```

You should see a JSON response with products.

### 🔧 ElevenLabs Setup Tips

1. **In the "Server URL" field**: Paste the full URL without any modifications
2. **Method**: Always select "POST"
3. **Headers**: Leave empty (not needed)
4. **Authentication**: None required

### 📱 Alternative: Use Custom Instructions

If URLs still don't work, try this approach in ElevenLabs:

Instead of tools, add this to your system prompt:

```
When users ask to search for products, respond with:
"I'll search for [product] for you. Here are the top options..."

When users want to add to cart, respond with:
"I've added [quantity] [product] to your cart."

Then handle the actual API calls through a middleware service.
```

### Need Help?

If you're still having issues:
1. Check that the API is running: https://leafloaf-langraph-32905605817.us-central1.run.app/health
2. Try the webhook test script: `python3 test_webhooks_manual.py`
3. Check ElevenLabs logs for specific error messages