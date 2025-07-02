#!/usr/bin/env python3
"""
Deploy Gemma 2 9B via Model Garden for fine-tuning capabilities
"""

import os
import time
from google.cloud import aiplatform
from google.cloud.aiplatform import model_garden
import json

# Configuration
PROJECT_ID = "leafloafai"
LOCATION = "us-central1"
MODEL_NAME = "gemma-2-9b-it"
ENDPOINT_NAME = "leafloaf-gemma-endpoint"
DEPLOYED_MODEL_NAME = "leafloaf-gemma-deployed"

def initialize_vertex_ai():
    """Initialize Vertex AI with project settings"""
    aiplatform.init(
        project=PROJECT_ID,
        location=LOCATION
    )
    print(f"✅ Initialized Vertex AI for project: {PROJECT_ID}")

def deploy_gemma_from_model_garden():
    """Deploy Gemma model from Model Garden"""
    
    print("\n🚀 Deploying Gemma 2 9B from Model Garden")
    print("=" * 50)
    
    # Model artifact URI for Gemma
    # These are the official Model Garden URIs
    model_uris = {
        "gemma-2-9b-it": "gs://vertex-model-garden-public-us-central1/gemma2/gemma-2-9b-it",
        "gemma-2-2b-it": "gs://vertex-model-garden-public-us-central1/gemma2/gemma-2-2b-it",
    }
    
    model_uri = model_uris.get(MODEL_NAME)
    
    try:
        # Step 1: Upload the model
        print(f"\n📦 Step 1: Uploading model {MODEL_NAME}")
        model = aiplatform.Model.upload(
            display_name=f"leafloaf-{MODEL_NAME}",
            artifact_uri=model_uri,
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.1-13:latest",
            description="Gemma 2 9B for LeafLoaf grocery assistant with fine-tuning capability"
        )
        print(f"✅ Model uploaded: {model.resource_name}")
        
        # Step 2: Create endpoint
        print(f"\n🎯 Step 2: Creating endpoint")
        endpoint = aiplatform.Endpoint.create(
            display_name=ENDPOINT_NAME,
            description="LeafLoaf Gemma endpoint for inference and fine-tuning"
        )
        print(f"✅ Endpoint created: {endpoint.resource_name}")
        
        # Step 3: Deploy model to endpoint
        print(f"\n🔄 Step 3: Deploying model to endpoint")
        print("This may take 10-15 minutes...")
        
        # Machine configuration for Gemma 2 9B
        machine_type = "n1-standard-8"  # 8 vCPUs, 30GB memory
        accelerator_type = "NVIDIA_TESLA_T4"
        accelerator_count = 1
        
        deployed_model = endpoint.deploy(
            model=model,
            deployed_model_display_name=DEPLOYED_MODEL_NAME,
            machine_type=machine_type,
            accelerator_type=accelerator_type,
            accelerator_count=accelerator_count,
            min_replica_count=1,
            max_replica_count=2,
            traffic_percentage=100,
        )
        
        print(f"✅ Model deployed successfully!")
        print(f"\n📊 Deployment Details:")
        print(f"   Endpoint ID: {endpoint.name}")
        print(f"   Model ID: {model.name}")
        print(f"   Machine Type: {machine_type}")
        print(f"   Accelerator: {accelerator_type} x {accelerator_count}")
        
        # Save deployment info
        deployment_info = {
            "endpoint_id": endpoint.name,
            "endpoint_resource_name": endpoint.resource_name,
            "model_id": model.name,
            "model_resource_name": model.resource_name,
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": MODEL_NAME,
            "machine_config": {
                "machine_type": machine_type,
                "accelerator_type": accelerator_type,
                "accelerator_count": accelerator_count,
                "min_replicas": 1,
                "max_replicas": 2
            }
        }
        
        with open("gemma_deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"\n💾 Deployment info saved to: gemma_deployment_info.json")
        
        return endpoint, model
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        print("\nPossible solutions:")
        print("1. Check if you have sufficient quota for GPU")
        print("2. Try with a smaller model (gemma-2-2b-it)")
        print("3. Ensure billing is enabled")
        print("4. Check IAM permissions")
        raise

def test_deployed_model(endpoint):
    """Test the deployed model with a sample query"""
    print("\n🧪 Testing deployed model...")
    
    test_query = {
        "instances": [{
            "prompt": "Analyze this grocery query: 'I need organic milk and gluten-free bread'. Return JSON with intent and entities.",
            "temperature": 0.7,
            "max_tokens": 256
        }]
    }
    
    try:
        response = endpoint.predict(instances=test_query["instances"])
        print(f"✅ Model response: {response.predictions}")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

def create_fine_tuning_pipeline():
    """Create a pipeline for fine-tuning Gemma on custom data"""
    print("\n📚 Setting up fine-tuning pipeline...")
    
    fine_tuning_config = {
        "display_name": "leafloaf-gemma-finetuning",
        "training_data_uri": "gs://leafloaf-training-data/grocery_conversations.jsonl",
        "validation_data_uri": "gs://leafloaf-training-data/grocery_conversations_val.jsonl",
        "hyperparameters": {
            "learning_rate": 2e-5,
            "num_train_epochs": 3,
            "batch_size": 4,
            "warmup_steps": 100,
        },
        "output_model_name": "leafloaf-gemma-finetuned"
    }
    
    with open("fine_tuning_config.json", "w") as f:
        json.dump(fine_tuning_config, f, indent=2)
    
    print("✅ Fine-tuning configuration saved to: fine_tuning_config.json")
    print("\nTo start fine-tuning:")
    print("1. Prepare training data in JSONL format")
    print("2. Upload to Cloud Storage")
    print("3. Run: python scripts/start_fine_tuning.py")

def main():
    """Main deployment process"""
    print("🌟 LeafLoaf Gemma Model Garden Deployment")
    print("This will deploy Gemma 2 9B with fine-tuning capability")
    
    # Initialize Vertex AI
    initialize_vertex_ai()
    
    # Deploy model
    try:
        endpoint, model = deploy_gemma_from_model_garden()
        
        # Test deployment
        test_deployed_model(endpoint)
        
        # Set up fine-tuning
        create_fine_tuning_pipeline()
        
        print("\n✨ Deployment complete!")
        print("\n📝 Next steps:")
        print("1. Update gemma_client.py to use the deployed endpoint")
        print("2. Prepare training data from user interactions")
        print("3. Implement Redis caching for model responses")
        print("4. Start fine-tuning process")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())