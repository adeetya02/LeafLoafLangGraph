"""
Production Entity Extractor using Gemini Model Garden directly

This is the RIGHT way - no API overhead, direct Model Garden access.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of entities we track"""
    PRODUCT = "product"
    BRAND = "brand"
    CATEGORY = "category"
    ATTRIBUTE = "attribute"
    DIETARY_RESTRICTION = "dietary_restriction"
    PREFERENCE = "preference"
    EVENT = "event"
    TIME_PERIOD = "time_period"
    QUANTITY = "quantity"
    LOCATION = "location"


class RelationshipType(str, Enum):
    """Types of relationships between entities"""
    PREFERS = "prefers"
    AVOIDS = "avoids"
    PURCHASED = "purchased"
    REORDERS = "reorders"
    MENTIONED_WITH = "mentioned_with"
    BELONGS_TO = "belongs_to"
    HAS_ATTRIBUTE = "has_attribute"


@dataclass
class ExtractedEntity:
    """Entity extracted from text"""
    name: str
    type: EntityType
    confidence: float
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class ExtractedRelationship:
    """Relationship between entities"""
    source: str
    target: str
    type: RelationshipType
    confidence: float
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class GeminiEntityExtractor:
    """
    Production entity extractor using Gemini Model Garden directly
    No API wrapper, no overhead - just direct Model Garden access
    """
    
    def __init__(self):
        """Initialize with Gemini from Model Garden"""
        # Initialize Vertex AI
        vertexai.init(project="leafloafai", location="us-central1")
        
        # Use Gemini 1.5 Pro directly from Model Garden
        self.model = GenerativeModel("gemini-1.5-pro")
        
        # Configuration for structured output
        self.generation_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
            candidate_count=1,
        )
        
        # System prompt for entity extraction
        self.system_prompt = """You are an expert at extracting entities and relationships from grocery shopping conversations.

Extract entities with these types:
- PRODUCT: Specific products (e.g., "milk", "oat milk", "Oatly")
- BRAND: Brand names (e.g., "Oatly", "Happy Cows", "Organic Valley")
- CATEGORY: Product categories (e.g., "dairy", "produce", "beverages")
- ATTRIBUTE: Product attributes (e.g., "organic", "lactose-free", "gluten-free")
- DIETARY_RESTRICTION: Dietary needs (e.g., "vegan", "kosher", "halal")
- PREFERENCE: User preferences (e.g., "I love", "my favorite", "I prefer")
- EVENT: Events or occasions (e.g., "party", "birthday", "weekly shopping")
- TIME_PERIOD: Time references (e.g., "every week", "monthly", "last time")
- QUANTITY: Quantities (e.g., "2 gallons", "a dozen", "large pack")
- LOCATION: Store references (e.g., "at Whole Foods", "local store")

Extract relationships:
- PREFERS: User prefers something
- AVOIDS: User avoids something
- PURCHASED: Previous purchase
- REORDERS: Regular reorder pattern
- MENTIONED_WITH: Entities mentioned together
- BELONGS_TO: Category membership
- HAS_ATTRIBUTE: Entity has attribute

Return JSON with this exact structure:
{
  "entities": [
    {
      "name": "entity name",
      "type": "ENTITY_TYPE",
      "confidence": 0.95,
      "properties": {}
    }
  ],
  "relationships": [
    {
      "source": "source entity name",
      "target": "target entity name",
      "type": "RELATIONSHIP_TYPE",
      "confidence": 0.9,
      "properties": {}
    }
  ]
}

Be specific and extract ALL relevant entities and relationships."""

    async def extract_entities_and_relationships(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract entities and relationships using Gemini directly"""
        try:
            # Build the prompt
            prompt = f"""{self.system_prompt}

Text to analyze: {text}

Extract all entities and relationships. Return only valid JSON."""

            # Generate response using Gemini directly
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to parse JSON
            try:
                # Find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Try parsing the whole response
                    result = json.loads(response_text)
                
                # Convert to our dataclasses
                entities = []
                for entity_data in result.get("entities", []):
                    entities.append(ExtractedEntity(
                        name=entity_data["name"],
                        type=EntityType(entity_data["type"]),
                        confidence=entity_data.get("confidence", 0.9),
                        properties=entity_data.get("properties", {})
                    ))
                
                relationships = []
                for rel_data in result.get("relationships", []):
                    relationships.append(ExtractedRelationship(
                        source=rel_data["source"],
                        target=rel_data["target"],
                        type=RelationshipType(rel_data["type"]),
                        confidence=rel_data.get("confidence", 0.9),
                        properties=rel_data.get("properties", {})
                    ))
                
                logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships using Gemini")
                
                return {
                    "entities": entities,
                    "relationships": relationships,
                    "raw_response": response_text[:200] + "..." if len(response_text) > 200 else response_text
                }
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini response as JSON: {e}")
                logger.debug(f"Response: {response_text[:500]}")
                return {"entities": [], "relationships": [], "error": "JSON parse error"}
                
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {"entities": [], "relationships": [], "error": str(e)}
    
    def extract_entities_and_relationships_sync(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous version for compatibility"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.extract_entities_and_relationships(text, context)
            )
        finally:
            loop.close()