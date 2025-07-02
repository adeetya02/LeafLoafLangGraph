#!/usr/bin/env python3
"""
Setup Dialogflow agent for LeafLoaf
"""
import os
from google.cloud import dialogflow_v2 as dialogflow

PROJECT_ID = "leafloafai"
LOCATION = "global"  # Use global location for Dialogflow ES

def create_agent():
    """Create a Dialogflow agent"""
    # Create a client
    agents_client = dialogflow.AgentsClient()
    
    # Create parent path
    parent = f"projects/{PROJECT_ID}"
    
    # Define the agent
    agent = dialogflow.Agent(
        parent=parent,
        display_name="LeafLoaf Shopping Assistant",
        default_language_code="en",
        time_zone="America/New_York",
        description="Grocery shopping assistant with natural language understanding",
        enable_logging=True
    )
    
    try:
        # Create the agent
        response = agents_client.set_agent(request={"agent": agent})
        print(f"Agent created: {response.parent}")
        return response.parent
    except Exception as e:
        print(f"Agent might already exist or error: {e}")
        return parent

def create_intents(parent):
    """Create basic intents"""
    intents_client = dialogflow.IntentsClient()
    
    # For Dialogflow ES, intents are created under the agent
    agent_path = f"{parent}/agent"
    
    # Product search intent
    training_phrases = [
        "I need milk",
        "Show me bananas", 
        "Find organic vegetables",
        "I'm looking for bread",
        "Do you have apples?"
    ]
    
    messages = [
        dialogflow.Intent.Message(
            text=dialogflow.Intent.Message.Text(
                text=["I'll help you find that product.", "Let me search for that."]
            )
        )
    ]
    
    intent = dialogflow.Intent(
        display_name="product.search",
        training_phrases=[
            dialogflow.Intent.TrainingPhrase(
                parts=[
                    dialogflow.Intent.TrainingPhrase.Part(text=phrase)
                ]
            ) for phrase in training_phrases
        ],
        messages=messages
    )
    
    try:
        response = intents_client.create_intent(
            request={"parent": agent_path, "intent": intent}
        )
        print(f"Intent created: {response.name}")
    except Exception as e:
        print(f"Intent might already exist or error: {e}")

    # Add to cart intent
    cart_phrases = [
        "Add milk to my cart",
        "Put 2 bananas in my basket",
        "I want to buy apples"
    ]
    
    cart_intent = dialogflow.Intent(
        display_name="order.add",
        training_phrases=[
            dialogflow.Intent.TrainingPhrase(
                parts=[
                    dialogflow.Intent.TrainingPhrase.Part(text=phrase)
                ]
            ) for phrase in cart_phrases
        ],
        messages=[
            dialogflow.Intent.Message(
                text=dialogflow.Intent.Message.Text(
                    text=["I'll add that to your cart.", "Added to your basket."]
                )
            )
        ]
    )
    
    try:
        response = intents_client.create_intent(
            request={"parent": agent_path, "intent": cart_intent}
        )
        print(f"Cart intent created: {response.name}")
    except Exception as e:
        print(f"Cart intent might already exist or error: {e}")

if __name__ == "__main__":
    print(f"Setting up Dialogflow for project: {PROJECT_ID}")
    parent = create_agent()
    create_intents(parent)
    print("\nSetup complete! Dialogflow agent is ready.")
    print(f"Agent ID: {parent}")