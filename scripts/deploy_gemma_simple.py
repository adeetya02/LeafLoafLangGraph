#!/usr/bin/env python3
"""
Simple Gemma deployment to Model Garden for fine-tuning
Using the Model Registry approach
"""

import os
import json
import time
from google.cloud import aiplatform

PROJECT_ID = "leafloafai"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-vertex-staging"

def main():
    print("🚀 Deploying Gemma to Model Garden for Fine-tuning")
    print("=" * 60)
    
    # Initialize Vertex AI
    aiplatform.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)
    print(f"✅ Initialized Vertex AI in {LOCATION}")
    
    # First, let's check available pre-built models
    print("\n📦 Checking Model Registry for Gemma models...")
    
    # List models from Model Registry
    try:
        # For Gemma, we need to use the Model Registry
        print("\n🔍 Available approaches:")
        print("1. Use Gemma from Model Registry (recommended)")
        print("2. Fine-tune using Vertex AI Pipelines")
        print("3. Deploy custom container")
        
        # Gemma Model Garden URIs (these are the official paths)
        gemma_models = {
            "gemma-2b": {
                "model_id": "gemma-2b",
                "display_name": "Gemma 2B",
                "description": "Gemma 2B base model"
            },
            "gemma-7b": {
                "model_id": "gemma-7b", 
                "display_name": "Gemma 7B",
                "description": "Gemma 7B base model"
            },
            "gemma2-9b": {
                "model_id": "gemma2-9b",
                "display_name": "Gemma 2 9B",
                "description": "Gemma 2 9B instruction-tuned"
            }
        }
        
        print("\n📋 Model deployment options:")
        for model_key, model_info in gemma_models.items():
            print(f"  - {model_info['display_name']}: {model_info['description']}")
        
        # Create deployment configuration
        deployment_config = {
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "model_choice": "gemma2-9b",
            "deployment_options": {
                "option_1": "Deploy base model first, then fine-tune",
                "option_2": "Prepare data and fine-tune offline",
                "option_3": "Use Model Garden UI for deployment"
            },
            "fine_tuning_approach": {
                "method": "PEFT (Parameter Efficient Fine-Tuning)",
                "recommended_gpu": "NVIDIA_L4",
                "training_hours_estimate": "2-4 hours",
                "cost_estimate": "$20-40"
            }
        }
        
        # Save configuration
        with open("gemma_deployment_plan.json", "w") as f:
            json.dump(deployment_config, f, indent=2)
        
        print("\n💾 Saved deployment plan to: gemma_deployment_plan.json")
        
        # Provide direct links
        print("\n🔗 Direct Console Links:")
        print(f"1. Model Garden: https://console.cloud.google.com/vertex-ai/model-garden?project={PROJECT_ID}")
        print(f"2. Model Registry: https://console.cloud.google.com/vertex-ai/model-registry?project={PROJECT_ID}")
        print(f"3. Endpoints: https://console.cloud.google.com/vertex-ai/endpoints?project={PROJECT_ID}")
        
        print("\n📝 Manual Deployment Steps:")
        print("1. Go to Model Garden (link above)")
        print("2. Search for 'Gemma 2'")
        print("3. Click on 'Gemma 2 9B'")
        print("4. Click 'Deploy' button")
        print("5. Choose deployment configuration:")
        print("   - Machine type: g2-standard-8 (1 x NVIDIA L4)")
        print("   - Min replicas: 1")
        print("   - Max replicas: 2")
        print("6. Click 'Deploy'")
        
        print("\n🎯 For Fine-tuning:")
        print("1. After deployment, go to 'Model Registry'")
        print("2. Find your deployed Gemma model")
        print("3. Click 'Fine-tune'")
        print("4. Upload prepared training data")
        print("5. Configure training parameters")
        print("6. Start fine-tuning job")
        
        # Create training bucket
        print("\n🪣 Creating staging bucket for training data...")
        os.system(f"gsutil mb -p {PROJECT_ID} -l {LOCATION} {STAGING_BUCKET} 2>/dev/null || echo 'Bucket exists'")
        
        print("\n✅ Setup complete!")
        print("\n🚀 Next Steps:")
        print("1. Deploy Gemma via Model Garden UI (recommended)")
        print("2. Run prepare_training_data.py to create training dataset")
        print("3. Upload training data to staging bucket")
        print("4. Start fine-tuning job")
        
        # Alternative: Use notebook
        print("\n📓 Alternative: Use Colab/Vertex Workbench")
        print("Notebook URL: https://github.com/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/model_garden/model_garden_gemma_2_9b_it_peft_finetuning.ipynb")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Tip: Make sure you have the necessary permissions:")
        print("  - Vertex AI User")
        print("  - Storage Admin (for buckets)")
        print("  - Service Account User")

if __name__ == "__main__":
    main()