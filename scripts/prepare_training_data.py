#!/usr/bin/env python3
"""
Prepare training data for fine-tuning Gemma on LeafLoaf conversations
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

class TrainingDataPreparer:
    """Prepare grocery conversation data for Gemma fine-tuning"""
    
    def __init__(self):
        self.training_examples = []
        self.validation_examples = []
        
    def create_grocery_examples(self):
        """Create examples from common grocery shopping patterns"""
        
        # Product search examples
        product_searches = [
            {
                "input": "I need Oatly Barista Edition",
                "output": json.dumps({
                    "intent": "product_search",
                    "entities": ["Oatly Barista Edition"],
                    "product_type": "oat milk",
                    "brand": "Oatly",
                    "specific_variant": "Barista Edition",
                    "search_alpha": 0.1,
                    "confidence": 0.95
                })
            },
            {
                "input": "Show me organic milk options",
                "output": json.dumps({
                    "intent": "product_search",
                    "entities": ["milk"],
                    "attributes": ["organic"],
                    "search_alpha": 0.3,
                    "confidence": 0.9
                })
            },
            {
                "input": "I need something for breakfast",
                "output": json.dumps({
                    "intent": "exploratory_search",
                    "category": "breakfast",
                    "search_alpha": 0.8,
                    "suggestions": ["cereal", "oatmeal", "bread", "eggs", "yogurt"],
                    "confidence": 0.85
                })
            }
        ]
        
        # Order management examples
        order_examples = [
            {
                "input": "Add 2 gallons of the organic milk to my cart",
                "output": json.dumps({
                    "intent": "add_to_order",
                    "product_reference": "previous_result",
                    "quantity": 2,
                    "unit": "gallons",
                    "attributes": ["organic"],
                    "confidence": 0.92
                })
            },
            {
                "input": "Remove the milk from my order",
                "output": json.dumps({
                    "intent": "remove_from_order",
                    "entities": ["milk"],
                    "scope": "all_matching",
                    "confidence": 0.88
                })
            },
            {
                "input": "What's in my cart?",
                "output": json.dumps({
                    "intent": "list_order",
                    "format": "detailed",
                    "confidence": 0.95
                })
            }
        ]
        
        # Conversational examples
        conversation_examples = [
            {
                "input": "I'm planning a dinner party and need appetizer ideas",
                "output": json.dumps({
                    "intent": "meal_planning",
                    "occasion": "dinner party",
                    "meal_type": "appetizers",
                    "search_alpha": 0.9,
                    "suggestions": ["cheese platter", "crackers", "olives", "hummus", "vegetables"],
                    "confidence": 0.87
                })
            },
            {
                "input": "What vegan options do you have?",
                "output": json.dumps({
                    "intent": "dietary_search",
                    "dietary_restriction": "vegan",
                    "search_alpha": 0.5,
                    "categories": ["dairy alternatives", "meat alternatives", "produce"],
                    "confidence": 0.91
                })
            }
        ]
        
        # Combine all examples
        all_examples = product_searches + order_examples + conversation_examples
        
        # Convert to Gemma fine-tuning format
        for example in all_examples:
            formatted_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a grocery shopping assistant. Analyze queries and respond with structured JSON containing intent, entities, and search parameters."
                    },
                    {
                        "role": "user",
                        "content": example["input"]
                    },
                    {
                        "role": "assistant",
                        "content": example["output"]
                    }
                ]
            }
            self.training_examples.append(formatted_example)
            
            # Add some to validation set (20%)
            if len(self.validation_examples) < len(self.training_examples) * 0.2:
                self.validation_examples.append(formatted_example)
    
    def create_supplier_examples(self):
        """Create examples for supplier-specific queries"""
        
        supplier_examples = [
            {
                "input": "Show me all Organic Valley products",
                "output": json.dumps({
                    "intent": "supplier_search",
                    "supplier": "Organic Valley",
                    "search_alpha": 0.1,
                    "filter_type": "exact_match",
                    "confidence": 0.95
                })
            },
            {
                "input": "What brands of oat milk do you carry?",
                "output": json.dumps({
                    "intent": "brand_discovery",
                    "product_type": "oat milk",
                    "search_alpha": 0.4,
                    "response_type": "brand_list",
                    "confidence": 0.88
                })
            }
        ]
        
        for example in supplier_examples:
            formatted_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a grocery shopping assistant with knowledge of suppliers and brands."
                    },
                    {
                        "role": "user",
                        "content": example["input"]
                    },
                    {
                        "role": "assistant",
                        "content": example["output"]
                    }
                ]
            }
            self.training_examples.append(formatted_example)
    
    def save_training_data(self, output_dir: str = "training_data"):
        """Save training data in JSONL format for Vertex AI"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save training data
        train_file = os.path.join(output_dir, "grocery_conversations_train.jsonl")
        with open(train_file, "w") as f:
            for example in self.training_examples:
                f.write(json.dumps(example) + "\n")
        
        print(f"✅ Saved {len(self.training_examples)} training examples to: {train_file}")
        
        # Save validation data
        val_file = os.path.join(output_dir, "grocery_conversations_val.jsonl")
        with open(val_file, "w") as f:
            for example in self.validation_examples:
                f.write(json.dumps(example) + "\n")
        
        print(f"✅ Saved {len(self.validation_examples)} validation examples to: {val_file}")
        
        # Create metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_examples": len(self.training_examples),
            "validation_examples": len(self.validation_examples),
            "categories": [
                "product_search",
                "order_management", 
                "conversational",
                "supplier_specific"
            ],
            "target_model": "gemma-2-9b-it"
        }
        
        metadata_file = os.path.join(output_dir, "training_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Saved metadata to: {metadata_file}")
        
        return train_file, val_file
    
    def upload_to_gcs(self, train_file: str, val_file: str):
        """Upload training data to Google Cloud Storage"""
        
        bucket_name = "leafloaf-training-data"
        
        print(f"\n📤 Uploading to Cloud Storage bucket: gs://{bucket_name}")
        
        # Commands to create bucket and upload
        commands = [
            f"gsutil mb -p leafloafai -l us-central1 gs://{bucket_name}",
            f"gsutil cp {train_file} gs://{bucket_name}/",
            f"gsutil cp {val_file} gs://{bucket_name}/",
            f"gsutil ls -l gs://{bucket_name}/"
        ]
        
        print("\nRun these commands to upload:")
        for cmd in commands:
            print(f"  {cmd}")
        
        return f"gs://{bucket_name}/{os.path.basename(train_file)}"

def main():
    """Prepare training data for Gemma fine-tuning"""
    print("🎯 LeafLoaf Training Data Preparation")
    print("=" * 50)
    
    preparer = TrainingDataPreparer()
    
    # Create examples
    print("\n📝 Creating training examples...")
    preparer.create_grocery_examples()
    preparer.create_supplier_examples()
    
    # Save data
    train_file, val_file = preparer.save_training_data()
    
    # Upload instructions
    preparer.upload_to_gcs(train_file, val_file)
    
    print("\n✨ Training data preparation complete!")
    print("\nNext steps:")
    print("1. Upload data to Cloud Storage using the commands above")
    print("2. Run deploy_gemma_model_garden.py to deploy base model")
    print("3. Start fine-tuning with the prepared data")

if __name__ == "__main__":
    main()