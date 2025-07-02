#!/usr/bin/env python3
"""
Complete Dialogflow Setup for LeafLoaf with Personalization
Sets up all intents, entities, and training phrases for the grocery shopping system
"""
import os
import sys
from google.cloud import dialogflow_v2 as dialogflow
from google.api_core import exceptions

PROJECT_ID = "leafloafai"

def create_agent():
    """Create or update the Dialogflow agent"""
    agents_client = dialogflow.AgentsClient()
    parent = f"projects/{PROJECT_ID}"
    
    agent = dialogflow.Agent(
        parent=parent,
        display_name="LeafLoaf Personalized Shopping",
        default_language_code="en",
        time_zone="America/New_York",
        description="Personalized grocery shopping with voice, supporting dietary preferences, reorders, and smart recommendations",
        enable_logging=True
    )
    
    try:
        response = agents_client.set_agent(request={"agent": agent})
        print(f"✅ Agent configured: {response.parent}")
        return parent
    except Exception as e:
        print(f"⚠️  Agent configuration error: {e}")
        return parent

def create_entities(parent):
    """Create custom entities for grocery items"""
    entities_client = dialogflow.EntityTypesClient()
    
    # Product entity with common grocery items
    product_entity = dialogflow.EntityType(
        display_name="product",
        kind=dialogflow.EntityType.Kind.KIND_MAP,
        entities=[
            dialogflow.EntityType.Entity(value="milk", synonyms=["milk", "whole milk", "2% milk", "skim milk"]),
            dialogflow.EntityType.Entity(value="bread", synonyms=["bread", "loaf", "sliced bread", "whole wheat bread"]),
            dialogflow.EntityType.Entity(value="eggs", synonyms=["eggs", "dozen eggs", "free range eggs"]),
            dialogflow.EntityType.Entity(value="bananas", synonyms=["bananas", "banana", "organic bananas"]),
            dialogflow.EntityType.Entity(value="apples", synonyms=["apples", "apple", "red apples", "green apples"]),
            dialogflow.EntityType.Entity(value="chicken", synonyms=["chicken", "chicken breast", "whole chicken"]),
            dialogflow.EntityType.Entity(value="rice", synonyms=["rice", "white rice", "brown rice", "basmati rice"]),
            dialogflow.EntityType.Entity(value="pasta", synonyms=["pasta", "spaghetti", "penne", "macaroni"]),
            dialogflow.EntityType.Entity(value="tomatoes", synonyms=["tomatoes", "tomato", "cherry tomatoes"]),
            dialogflow.EntityType.Entity(value="onions", synonyms=["onions", "onion", "red onion", "white onion"]),
        ]
    )
    
    # Category entity
    category_entity = dialogflow.EntityType(
        display_name="category",
        kind=dialogflow.EntityType.Kind.KIND_MAP,
        entities=[
            dialogflow.EntityType.Entity(value="dairy", synonyms=["dairy", "dairy products", "milk products"]),
            dialogflow.EntityType.Entity(value="produce", synonyms=["produce", "fruits", "vegetables", "fresh produce"]),
            dialogflow.EntityType.Entity(value="meat", synonyms=["meat", "meats", "protein", "poultry"]),
            dialogflow.EntityType.Entity(value="bakery", synonyms=["bakery", "bread", "baked goods"]),
            dialogflow.EntityType.Entity(value="organic", synonyms=["organic", "natural", "non-gmo"]),
            dialogflow.EntityType.Entity(value="gluten-free", synonyms=["gluten-free", "gluten free", "no gluten"]),
            dialogflow.EntityType.Entity(value="vegan", synonyms=["vegan", "plant-based", "dairy-free"]),
        ]
    )
    
    # Quantity entity
    quantity_entity = dialogflow.EntityType(
        display_name="quantity",
        kind=dialogflow.EntityType.Kind.KIND_MAP,
        entities=[
            dialogflow.EntityType.Entity(value="1", synonyms=["1", "one", "a", "single"]),
            dialogflow.EntityType.Entity(value="2", synonyms=["2", "two", "a couple", "pair"]),
            dialogflow.EntityType.Entity(value="3", synonyms=["3", "three"]),
            dialogflow.EntityType.Entity(value="6", synonyms=["6", "six", "half dozen"]),
            dialogflow.EntityType.Entity(value="12", synonyms=["12", "twelve", "dozen"]),
        ]
    )
    
    # Dietary preference entity
    dietary_entity = dialogflow.EntityType(
        display_name="dietary",
        kind=dialogflow.EntityType.Kind.KIND_MAP,
        entities=[
            dialogflow.EntityType.Entity(value="vegetarian", synonyms=["vegetarian", "veggie"]),
            dialogflow.EntityType.Entity(value="vegan", synonyms=["vegan", "plant-based"]),
            dialogflow.EntityType.Entity(value="gluten-free", synonyms=["gluten-free", "gluten free", "celiac"]),
            dialogflow.EntityType.Entity(value="dairy-free", synonyms=["dairy-free", "dairy free", "lactose-free"]),
            dialogflow.EntityType.Entity(value="keto", synonyms=["keto", "ketogenic", "low-carb"]),
            dialogflow.EntityType.Entity(value="halal", synonyms=["halal"]),
            dialogflow.EntityType.Entity(value="kosher", synonyms=["kosher"]),
        ]
    )
    
    # Create all entities
    for entity_type in [product_entity, category_entity, quantity_entity, dietary_entity]:
        try:
            entities_client.create_entity_type(
                parent=parent,
                entity_type=entity_type
            )
            print(f"✅ Created entity: @{entity_type.display_name}")
        except exceptions.AlreadyExists:
            print(f"⚠️  Entity @{entity_type.display_name} already exists")
        except Exception as e:
            print(f"❌ Error creating entity @{entity_type.display_name}: {e}")

def create_intents(parent):
    """Create all intents for personalized shopping"""
    intents_client = dialogflow.IntentsClient()
    
    intents_config = [
        {
            "display_name": "product.search",
            "training_phrases": [
                "I need milk",
                "Show me bananas",
                "Do you have organic vegetables",
                "Find gluten-free bread",
                "I'm looking for chicken",
                "Search for pasta",
                "What dairy products do you have",
                "Show me all fruits",
                "I want to buy eggs",
                "Looking for vegan options"
            ],
            "messages": ["I'll help you find that. Let me search for {product}"],
            "parameters": ["product", "category", "dietary"]
        },
        {
            "display_name": "order.add",
            "training_phrases": [
                "Add milk to my cart",
                "Put 2 bananas in my basket",
                "I want to buy a dozen eggs",
                "Add bread to cart",
                "Get me 3 apples",
                "Add that to my cart",
                "Put it in my basket",
                "I'll take 2 of those"
            ],
            "messages": ["I've added {quantity} {product} to your cart"],
            "parameters": ["product", "quantity"]
        },
        {
            "display_name": "order.remove",
            "training_phrases": [
                "Remove milk from cart",
                "Delete bananas",
                "Take out the eggs",
                "Remove that item",
                "I don't want the bread anymore",
                "Cancel the apples"
            ],
            "messages": ["I've removed {product} from your cart"],
            "parameters": ["product"]
        },
        {
            "display_name": "order.update",
            "training_phrases": [
                "Change milk quantity to 2",
                "I want 3 bananas instead",
                "Update eggs to 2 dozen",
                "Make it 5 apples",
                "Change the quantity"
            ],
            "messages": ["I've updated {product} quantity to {quantity}"],
            "parameters": ["product", "quantity"]
        },
        {
            "display_name": "order.view",
            "training_phrases": [
                "Show my cart",
                "What's in my basket",
                "View my order",
                "Check my cart",
                "What am I buying",
                "Show me what I have"
            ],
            "messages": ["Here's what's in your cart"]
        },
        {
            "display_name": "order.checkout",
            "training_phrases": [
                "Checkout",
                "I'm ready to pay",
                "Complete my order",
                "Finish shopping",
                "Place my order",
                "That's everything"
            ],
            "messages": ["Let me prepare your order for checkout"]
        },
        {
            "display_name": "personalization.usual",
            "training_phrases": [
                "My usual order",
                "What do I usually buy",
                "My regular items",
                "The usual please",
                "My standard order",
                "What I always get"
            ],
            "messages": ["I'll add your usual items"]
        },
        {
            "display_name": "personalization.reorder",
            "training_phrases": [
                "Reorder my last purchase",
                "Same as last time",
                "Repeat my last order",
                "What did I buy last week",
                "My previous order"
            ],
            "messages": ["I'll help you reorder your previous items"]
        },
        {
            "display_name": "personalization.dietary",
            "training_phrases": [
                "I'm vegetarian",
                "I need gluten-free options",
                "Show me vegan products",
                "I eat halal",
                "Dairy-free alternatives",
                "I'm on keto diet"
            ],
            "messages": ["I'll remember your {dietary} preference and show suitable options"],
            "parameters": ["dietary"]
        },
        {
            "display_name": "personalization.preferences",
            "training_phrases": [
                "I prefer organic",
                "Always get the cheapest option",
                "I like local products",
                "Brand name only",
                "Best quality please"
            ],
            "messages": ["I'll remember your preference"]
        },
        {
            "display_name": "recommendation.complementary",
            "training_phrases": [
                "What goes well with pasta",
                "Suggest something with chicken",
                "What should I cook with this",
                "Recipe suggestions",
                "What else do I need"
            ],
            "messages": ["Based on {product}, I recommend these complementary items"],
            "parameters": ["product"]
        },
        {
            "display_name": "general.greeting",
            "training_phrases": [
                "Hello",
                "Hi",
                "Hey there",
                "Good morning",
                "How are you"
            ],
            "messages": ["Hello! Welcome to LeafLoaf. What groceries can I help you find today?"]
        },
        {
            "display_name": "general.thanks",
            "training_phrases": [
                "Thank you",
                "Thanks",
                "That's helpful",
                "Great",
                "Perfect"
            ],
            "messages": ["You're welcome! Anything else you need?"]
        },
        {
            "display_name": "general.goodbye",
            "training_phrases": [
                "Bye",
                "Goodbye",
                "See you later",
                "That's all",
                "I'm done"
            ],
            "messages": ["Thank you for shopping with LeafLoaf! Have a great day!"]
        }
    ]
    
    # Create each intent
    for intent_config in intents_config:
        intent = dialogflow.Intent(
            display_name=intent_config["display_name"],
            training_phrases=[
                dialogflow.Intent.TrainingPhrase(
                    parts=[dialogflow.Intent.TrainingPhrase.Part(text=phrase)]
                ) for phrase in intent_config["training_phrases"]
            ],
            messages=[
                dialogflow.Intent.Message(
                    text=dialogflow.Intent.Message.Text(text=[msg])
                ) for msg in intent_config["messages"]
            ]
        )
        
        try:
            intents_client.create_intent(parent=parent, intent=intent)
            print(f"✅ Created intent: {intent_config['display_name']}")
        except exceptions.AlreadyExists:
            print(f"⚠️  Intent {intent_config['display_name']} already exists")
        except Exception as e:
            print(f"❌ Error creating intent {intent_config['display_name']}: {e}")

def setup_webhook(parent):
    """Configure webhook for fulfillment"""
    print("\n📌 Webhook Configuration:")
    print("To enable dynamic responses, set up webhook in Dialogflow console:")
    print(f"1. Go to: https://dialogflow.cloud.google.com/?project={PROJECT_ID}")
    print("2. Click on 'Fulfillment' in the left menu")
    print("3. Enable Webhook")
    print("4. Set URL to: https://your-domain.com/api/v1/dialogflow/webhook")
    print("5. Enable webhook for all intents that need dynamic responses")

def main():
    print("🚀 Setting up Dialogflow for LeafLoaf Personalized Shopping\n")
    
    # Set up authentication
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("⚠️  Using Application Default Credentials")
        print("   Run: gcloud auth application-default login")
    
    # Create/update agent
    parent = create_agent()
    
    # Create entities
    print("\n📝 Creating entities...")
    create_entities(parent)
    
    # Create intents
    print("\n🎯 Creating intents...")
    create_intents(parent)
    
    # Webhook info
    setup_webhook(parent)
    
    print("\n✅ Dialogflow setup complete!")
    print(f"\n🔧 Next steps:")
    print(f"1. Get your agent ID from: https://dialogflow.cloud.google.com/?project={PROJECT_ID}")
    print(f"2. Add to .env.yaml:")
    print(f"   DIALOGFLOW_AGENT_ID: 'your-agent-id'")
    print(f"3. Test with: http://localhost:8080/static/voice_dialogflow_test.html")

if __name__ == "__main__":
    main()