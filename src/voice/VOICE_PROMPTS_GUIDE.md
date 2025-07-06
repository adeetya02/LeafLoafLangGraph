# Voice Prompts Configuration Guide

The voice prompts system allows you to customize how Gemini handles different types of conversations in the LeafLoaf voice interface.

## Overview

The system provides:
- **Conversation Styles**: Different personality modes (friendly, efficient, personal shopper)
- **Scenario Detection**: Automatically detects conversation context (greeting, search, cart, etc.)
- **Custom Prompts**: Create your own scenarios and styles
- **Entity Extraction**: Focuses on relevant entities based on scenario

## Quick Start

```python
from src.voice.models.gemini_voice import GeminiVoiceModel

# Initialize with default prompts
model = GeminiVoiceModel()

# Generate response with auto-detection
response, entities = await model.generate_response(
    "Hello, I need organic milk",
    auto_detect_scenario=True  # Auto-detects this as greeting + search
)
```

## Conversation Styles

### Built-in Styles

1. **friendly_assistant** (default)
   - Warm, helpful, patient
   - Brief responses for voice
   - Example: "I'd be happy to help you find that!"

2. **efficient_helper**
   - Concise, professional
   - Very brief responses
   - Example: "Found it. Adding to cart."

3. **personal_shopper**
   - Personable, recommendation-focused
   - Moderate length responses
   - Example: "Based on what you usually get, you might also like..."

### Using Different Styles

```python
# Set conversation style
model.set_conversation_style("efficient_helper")

# Or specify per request
response, entities = await model.generate_response(
    user_input="Add milk to cart",
    conversation_style="efficient_helper"
)
```

## Scenarios

### Built-in Scenarios

1. **greeting** - Initial conversation
2. **product_search** - Finding products
3. **cart_management** - Add/remove items
4. **recommendations** - Suggestions
5. **order_completion** - Checkout
6. **clarification** - Unclear requests

### Scenario Detection

The system automatically detects scenarios based on keywords:

```python
# These will auto-detect as "greeting"
"Hello!"
"Hi, how are you?"

# These will auto-detect as "cart_management"
"Add 2 milks to cart"
"Remove the bananas"

# These will auto-detect as "recommendations"
"What do you recommend?"
"Any deals today?"
```

## Custom Configuration

### Adding Custom Scenarios

```python
# Add a custom scenario
model.add_custom_scenario(
    scenario_name="dietary_help",
    prompt="""Help with dietary restrictions.
Be knowledgeable about ingredients.
Suggest alternatives when items contain allergens.""",
    examples=[
        {"user": "Is this gluten free?", 
         "assistant": "Let me check the ingredients for you."}
    ]
)

# Use the custom scenario
response, entities = await model.generate_response(
    "Does this bread have gluten?",
    system_prompt=model.voice_prompts.get_prompt_for_scenario("dietary_help")
)
```

### Configuration File

Create a `prompts_config.json` file:

```json
{
  "styles": {
    "busy_parent": {
      "name": "Busy Parent Helper",
      "tone": "understanding",
      "response_length": "brief",
      "personality_traits": ["time-conscious", "family-aware"],
      "example_phrases": ["I'll add the family size for better value."]
    }
  },
  "scenarios": {
    "meal_planning": {
      "scenario": "meal_planning",
      "description": "Help plan meals",
      "system_prompt": "Help plan meals for the week...",
      "example_interactions": [...]
    }
  }
}
```

Load custom config:

```python
model = GeminiVoiceModel(prompts_config="path/to/prompts_config.json")
```

## Entity Extraction

Different scenarios focus on different entities:

```python
# Product search focuses on: products, brands, categories
"I need Cheerios" → {"products": ["Cheerios"], "brands": ["General Mills"]}

# Cart management focuses on: quantities, actions
"Add 2 milks" → {"products": ["milk"], "quantity": 2, "action": "add"}

# Recommendations focus on: preferences, dietary needs
"Something healthy for breakfast" → {"meal": "breakfast", "preference": "healthy"}
```

## Best Practices

1. **Keep responses brief** - They'll be spoken aloud
2. **Use scenario detection** - Let the system pick appropriate prompts
3. **Test different styles** - Find what works for your users
4. **Create custom scenarios** - For domain-specific needs
5. **Monitor entity extraction** - Ensure Graphiti gets good data

## Advanced Usage

### Disable Auto-Detection

```python
# Use specific prompt without detection
response, entities = await model.generate_response(
    user_input="Hello",
    system_prompt="You are a cheerful assistant who loves puns.",
    auto_detect_scenario=False
)
```

### Chain Scenarios

```python
# Start with greeting
response1, _ = await model.generate_response("Hello!")

# Continue with personalized style
model.set_conversation_style("personal_shopper")
response2, _ = await model.generate_response("What's good today?")
```

### Voice-Specific Adjustments

The prompts are optimized for voice:
- Short sentences
- Natural pauses
- Clear acknowledgments
- No complex punctuation

## Testing

Run the test script to see all features:

```bash
python test_voice_prompts.py
```

This will demonstrate:
- All available styles and scenarios
- Automatic scenario detection
- Custom scenario creation
- Conversation flow with style changes