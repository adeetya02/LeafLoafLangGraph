"""
Production Entity Extractor using deployed Gemma 2 model

This is the RIGHT approach for production:
- Uses our already-deployed Gemma 2 model
- No extra API calls or dependencies
- Clear separation: Gemma for ALL LLM tasks
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import httpx
from google.auth.transport.requests import Request
import google.auth

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


class ProductionEntityExtractor:
    """
    Production entity extractor using our deployed Gemma 2 endpoint
    
    This gives us:
    - Consistent LLM provider (all Gemma)
    - No external dependencies
    - Full control over prompts
    - Production-grade performance
    """
    
    def __init__(self):
        """Initialize with direct Gemma 2 endpoint access"""
        self.project_id = "leafloafai"
        self.location = "us-central1"
        self.endpoint_id = "1487855836171599872"  # Our Gemma 2 endpoint
        
        # Build endpoint URL
        self.endpoint_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/endpoints/{self.endpoint_id}:predict"
        
        # Get credentials
        try:
            self.credentials, _ = google.auth.default()
            self.use_auth = True
        except:
            logger.warning("No Google auth available")
            self.credentials = None
            self.use_auth = False
    
    async def extract_entities_and_relationships(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract entities using our Gemma 2 endpoint"""
        
        prompt = f"""Extract entities and relationships from this grocery shopping text.

ENTITIES (name, type, confidence 0-1):
- PRODUCT: Specific products
- BRAND: Brand names  
- QUANTITY: Amounts
- ATTRIBUTE: Product attributes
- PREFERENCE: User preferences

RELATIONSHIPS (source, target, type):
- PREFERS: User prefers something
- HAS_ATTRIBUTE: Product has attribute
- MENTIONED_WITH: Entities mentioned together

Text: {text}

Return JSON:
{{
  "entities": [
    {{"name": "Oatly", "type": "BRAND", "confidence": 0.95}},
    {{"name": "oat milk", "type": "PRODUCT", "confidence": 0.95}},
    {{"name": "2 gallons", "type": "QUANTITY", "confidence": 0.9}}
  ],
  "relationships": [
    {{"source": "oat milk", "target": "Oatly", "type": "BELONGS_TO", "confidence": 0.9}}
  ]
}}"""

        try:
            # Prepare request
            request_data = {
                "instances": [{
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 1024
                }]
            }
            
            # Get auth token if available
            headers = {"Content-Type": "application/json"}
            if self.use_auth and self.credentials:
                self.credentials.refresh(Request())
                headers["Authorization"] = f"Bearer {self.credentials.token}"
            
            # Make request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint_url,
                    json=request_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract the generated text
                    if "predictions" in result and len(result["predictions"]) > 0:
                        generated_text = result["predictions"][0].get("content", "")
                        
                        # Parse JSON from response
                        return self._parse_extraction_response(generated_text)
                    else:
                        logger.warning("No predictions in response")
                        return self._fallback_extraction(text)
                else:
                    logger.error(f"Endpoint returned {response.status_code}")
                    return self._fallback_extraction(text)
                    
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return self._fallback_extraction(text)
    
    def _parse_extraction_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the extraction response"""
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Convert to our dataclasses
                entities = []
                for entity_data in result.get("entities", []):
                    entities.append(ExtractedEntity(
                        name=entity_data["name"],
                        type=EntityType(entity_data["type"].lower()),
                        confidence=entity_data.get("confidence", 0.9),
                        properties=entity_data.get("properties", {})
                    ))
                
                relationships = []
                for rel_data in result.get("relationships", []):
                    relationships.append(ExtractedRelationship(
                        source=rel_data["source"],
                        target=rel_data["target"],
                        type=RelationshipType(rel_data["type"].lower()),
                        confidence=rel_data.get("confidence", 0.9),
                        properties=rel_data.get("properties", {})
                    ))
                
                logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
                return {"entities": entities, "relationships": relationships}
                
        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
        
        return self._fallback_extraction(response_text)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Simple pattern-based extraction as fallback"""
        entities = []
        text_lower = text.lower()
        
        # Products
        products = ["milk", "cheese", "bread", "eggs", "yogurt", "butter"]
        for product in products:
            if product in text_lower:
                entities.append(ExtractedEntity(
                    name=product,
                    type=EntityType.PRODUCT,
                    confidence=0.7
                ))
        
        # Brands
        brands = ["oatly", "happy cows", "organic valley", "amul"]
        for brand in brands:
            if brand in text_lower:
                entities.append(ExtractedEntity(
                    name=brand.title(),
                    type=EntityType.BRAND,
                    confidence=0.8
                ))
        
        # Quantities
        import re
        qty_pattern = r'\b(\d+)\s*(gallons?|liters?|pounds?|lbs?|dozen|pack)\b'
        for match in re.finditer(qty_pattern, text_lower):
            entities.append(ExtractedEntity(
                name=match.group(),
                type=EntityType.QUANTITY,
                confidence=0.9
            ))
        
        # Attributes
        attrs = ["organic", "fresh", "lactose-free", "gluten-free"]
        for attr in attrs:
            if attr in text_lower:
                entities.append(ExtractedEntity(
                    name=attr,
                    type=EntityType.ATTRIBUTE,
                    confidence=0.8
                ))
        
        return {"entities": entities, "relationships": []}