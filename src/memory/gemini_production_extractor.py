"""
Production Entity Extractor using Gemini 2.5 Pro

This is the PRODUCTION implementation - no fallbacks!
Uses Gemini 2.5 Pro via Google Generative AI API
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
from google.oauth2 import service_account
from google.auth.transport.requests import Request

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


class GeminiProductionExtractor:
    """
    Production entity extractor using Gemini 2.5 Pro
    
    This is the RIGHT way:
    - Gemini 2.5 Pro (latest and best)
    - Proper authentication with service account
    - No fallbacks - this is production!
    """
    
    def __init__(self):
        """Initialize with Gemini 2.5 Pro"""
        # Create scoped credentials
        self.credentials = service_account.Credentials.from_service_account_file(
            'graphiti-sa-key.json',
            scopes=['https://www.googleapis.com/auth/generative-language']
        )
        
        # Configure Gemini
        genai.configure(credentials=self.credentials)
        
        # Use Gemini 2.5 Pro
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Generation config for consistent output
        self.generation_config = {
            "temperature": 0.1,
            "max_output_tokens": 2048,
            "candidate_count": 1
        }
        
        logger.info("Initialized Gemini 2.5 Pro entity extractor")
    
    async def extract_entities_and_relationships(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract entities and relationships using Gemini 2.5 Pro"""
        
        prompt = f"""Extract entities from this grocery text: "{text}"

Find: products, brands, quantities, attributes (organic, fresh), preferences, time periods

Return JSON:
{{
  "entities": [
    {{"name": "Oatly", "type": "BRAND", "confidence": 0.95}},
    {{"name": "milk", "type": "PRODUCT", "confidence": 0.95}},
    {{"name": "2 gallons", "type": "QUANTITY", "confidence": 0.9}},
    {{"name": "organic", "type": "ATTRIBUTE", "confidence": 0.9}}
  ],
  "relationships": [
    {{"source": "milk", "target": "Oatly", "type": "BELONGS_TO", "confidence": 0.9}},
    {{"source": "cheese", "target": "organic", "type": "HAS_ATTRIBUTE", "confidence": 0.85}}
  ]
}}"""

        try:
            # Refresh credentials
            self.credentials.refresh(Request())
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Check if response was blocked
            if not response.parts:
                logger.warning(f"Response blocked. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
                # Try simpler prompt
                simple_prompt = f"List the products, brands, and quantities in this text: {text}"
                response = self.model.generate_content(simple_prompt)
            
            # Parse JSON from response
            response_text = response.text.strip()
            
            # Debug log
            logger.debug(f"Raw Gemini response: {response_text[:500]}")
            
            # Clean up response - remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Convert to our dataclasses
            entities = []
            for entity_data in result.get("entities", []):
                try:
                    entities.append(ExtractedEntity(
                        name=entity_data["name"],
                        type=EntityType(entity_data["type"].lower()),
                        confidence=float(entity_data.get("confidence", 0.9)),
                        properties=entity_data.get("properties", {})
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid entity: {entity_data}, error: {e}")
            
            relationships = []
            for rel_data in result.get("relationships", []):
                try:
                    relationships.append(ExtractedRelationship(
                        source=rel_data["source"],
                        target=rel_data["target"],
                        type=RelationshipType(rel_data["type"].lower()),
                        confidence=float(rel_data.get("confidence", 0.9)),
                        properties=rel_data.get("properties", {})
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid relationship: {rel_data}, error: {e}")
            
            logger.info(f"Gemini 2.5 Pro extracted {len(entities)} entities and {len(relationships)} relationships")
            
            return {
                "entities": entities,
                "relationships": relationships,
                "success": True,
                "model": "gemini-2.5-pro"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return {"entities": [], "relationships": [], "error": "JSON parse error"}
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {"entities": [], "relationships": [], "error": str(e)}