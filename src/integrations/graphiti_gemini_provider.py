"""
Custom Gemini Pro provider for Graphiti

Since Graphiti doesn't have built-in Gemini support, we create a custom provider
that implements the required interface for entity extraction and embeddings.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel

logger = logging.getLogger(__name__)


class GeminiProProvider:
    """
    Custom Gemini Pro provider for Graphiti entity extraction and embeddings
    
    This implements the interface expected by Graphiti for:
    1. Entity extraction from text
    2. Relationship extraction
    3. Text embeddings for semantic search
    """
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Initialize models
        self.llm_model = GenerativeModel("gemini-1.5-pro")
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
        # Entity extraction prompt template
        self.entity_prompt_template = """
You are an expert at extracting entities and relationships from text for a grocery shopping knowledge graph.

Extract the following from the text:
1. ENTITIES: Products, Brands, Categories, Events, People, Locations, Quantities, Prices
2. RELATIONSHIPS: BOUGHT, CONTAINS, PREFERS, SUBSTITUTE_FOR, BOUGHT_WITH, SHOPS_FOR

Text: {text}

Return the result in this exact JSON format:
{{
  "entities": [
    {{
      "type": "Product|Brand|Category|Event|Person|Location|Quantity|Price",
      "name": "entity name",
      "properties": {{
        "key": "value"
      }}
    }}
  ],
  "relationships": [
    {{
      "source": "source entity name",
      "target": "target entity name", 
      "type": "BOUGHT|CONTAINS|PREFERS|etc",
      "properties": {{
        "key": "value"
      }}
    }}
  ]
}}

Extract entities and relationships:"""
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities and relationships from text using Gemini Pro"""
        try:
            prompt = self.entity_prompt_template.format(text=text)
            
            # Generate response
            response = await self.llm_model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistency
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json"
                }
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.text)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting entities with Gemini: {e}")
            # Return empty result on error
            return {"entities": [], "relationships": []}
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using Vertex AI embedding model"""
        try:
            # Batch process for efficiency
            embeddings = []
            
            # Process in batches of 5 (Vertex AI limit)
            batch_size = 5
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Get embeddings
                batch_embeddings = self.embedding_model.get_embeddings(batch)
                
                for embedding in batch_embeddings:
                    embeddings.append(embedding.values)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return zero vectors on error
            return [[0.0] * 768 for _ in texts]  # 768 is default embedding size
    
    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a summary of the text"""
        try:
            prompt = f"""
Summarize the following grocery shopping interaction in {max_length} characters or less:

{text}

Summary:"""
            
            response = await self.llm_model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 100
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return text[:max_length]  # Fallback to truncation


class GraphitiGeminiAdapter:
    """
    Adapter to make GeminiProProvider work with Graphiti's expected interface
    
    This wraps our custom provider to match Graphiti's LLM provider interface.
    """
    
    def __init__(self, project_id: str = None):
        self.provider = GeminiProProvider(project_id)
        self.model_name = "gemini-1.5-pro"
    
    async def agenerate(self, prompts: List[str], **kwargs) -> List[str]:
        """Generate responses for multiple prompts"""
        responses = []
        
        for prompt in prompts:
            try:
                response = await self.provider.llm_model.generate_content_async(
                    prompt,
                    generation_config=kwargs.get("generation_config", {})
                )
                responses.append(response.text)
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                responses.append("")
        
        return responses
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for documents"""
        return await self.provider.generate_embeddings(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """Generate embedding for a query"""
        embeddings = await self.provider.generate_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def get_num_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation for Gemini)"""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4


# Example of how to configure Graphiti with Gemini
def create_graphiti_with_gemini(neo4j_config: Dict[str, Any]) -> Any:
    """
    Create a Graphiti instance configured with Gemini Pro
    
    Note: This would require modifying Graphiti to accept custom providers
    or using a wrapper approach.
    """
    # This is a conceptual example - actual implementation would depend
    # on Graphiti's extension points
    
    from graphiti_core import Graphiti
    
    # Create custom provider
    gemini_adapter = GraphitiGeminiAdapter()
    
    # Graphiti might need modification to accept custom providers
    # This is pseudocode showing the concept:
    """
    graphiti = Graphiti(
        neo4j_uri=neo4j_config["uri"],
        neo4j_user=neo4j_config["user"],
        neo4j_password=neo4j_config["password"],
        llm_provider=gemini_adapter,  # Custom provider
        embedding_provider=gemini_adapter  # Same for embeddings
    )
    """
    
    # For now, we'll need to use Graphiti's built-in providers
    # and potentially contribute Gemini support upstream
    
    return None


# Standalone entity extraction for testing
async def test_gemini_extraction():
    """Test entity extraction with Gemini Pro"""
    provider = GeminiProProvider()
    
    test_text = """
    Order placed by Priya Sharma:
    - 2 kg of Daawat Basmati Rice at ₹280
    - 1 kg of Tata Sampann Toor Dal at ₹155
    - 500ml of Figaro Olive Oil at ₹450
    
    This is for her daughter's birthday party next week.
    """
    
    result = await provider.extract_entities(test_text)
    
    print("Extracted Entities:")
    for entity in result.get("entities", []):
        print(f"  - {entity['type']}: {entity['name']}")
    
    print("\nExtracted Relationships:")
    for rel in result.get("relationships", []):
        print(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
    
    # Test embeddings
    embeddings = await provider.generate_embeddings(["Basmati rice", "Toor dal"])
    print(f"\nGenerated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini_extraction())