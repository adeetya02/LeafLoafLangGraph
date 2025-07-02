"""
Production Entity Extractor using Vertex AI Gemini

This replaces the pattern-based extraction with proper LLM-based extraction.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from langchain_google_vertexai import VertexAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

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


class ExtractedEntity(BaseModel):
    """Entity extracted from text"""
    name: str = Field(description="Name of the entity")
    type: EntityType = Field(description="Type of entity")
    confidence: float = Field(description="Confidence score 0-1")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class ExtractedRelationship(BaseModel):
    """Relationship between entities"""
    source: str = Field(description="Source entity name")
    target: str = Field(description="Target entity name")
    type: RelationshipType = Field(description="Type of relationship")
    confidence: float = Field(description="Confidence score 0-1")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class ExtractionResult(BaseModel):
    """Result of entity and relationship extraction"""
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


class VertexAIEntityExtractor:
    """
    Production entity extractor using Vertex AI Gemini
    """
    
    def __init__(self, model_name: str = "gemini-1.5-pro-001"):
        """Initialize with Vertex AI"""
        self.llm = VertexAI(
            model_name=model_name,
            temperature=0.1,
            max_output_tokens=1024,
            project="leafloafai",
            location="us-central1"
        )
        
        # Set up output parser
        self.output_parser = PydanticOutputParser(pydantic_object=ExtractionResult)
        
        # Create extraction prompt
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting entities and relationships from grocery shopping conversations.

Extract the following types of entities:
- PRODUCT: Specific products mentioned (e.g., "milk", "oat milk", "Oatly")
- BRAND: Brand names (e.g., "Oatly", "Happy Cows", "Organic Valley")
- CATEGORY: Product categories (e.g., "dairy", "produce", "beverages")
- ATTRIBUTE: Product attributes (e.g., "organic", "lactose-free", "gluten-free")
- DIETARY_RESTRICTION: Dietary needs (e.g., "vegan", "kosher", "halal")
- PREFERENCE: User preferences (e.g., "I love", "my favorite", "I prefer")
- EVENT: Events or occasions (e.g., "party", "birthday", "weekly shopping")
- TIME_PERIOD: Time references (e.g., "every week", "monthly", "last time")
- QUANTITY: Quantities mentioned (e.g., "2 gallons", "a dozen", "large pack")
- LOCATION: Store or location references (e.g., "at Whole Foods", "local store")

Extract relationships between entities:
- PREFERS: User prefers something (e.g., user PREFERS "organic milk")
- AVOIDS: User avoids something (e.g., user AVOIDS "lactose")
- PURCHASED: Previous purchase (e.g., user PURCHASED "Oatly" last time)
- REORDERS: Regular reorder pattern (e.g., "milk" REORDERS "weekly")
- MENTIONED_WITH: Entities mentioned together (e.g., "cereal" MENTIONED_WITH "milk")
- BELONGS_TO: Category membership (e.g., "Oatly" BELONGS_TO "plant-based milk")
- HAS_ATTRIBUTE: Entity has attribute (e.g., "Happy Cows milk" HAS_ATTRIBUTE "organic")

Be specific and extract all relevant entities and relationships with confidence scores.

{format_instructions}"""),
            ("human", "Extract entities and relationships from this text: {text}")
        ])
        
        self.prompt = self.extraction_prompt.partial(
            format_instructions=self.output_parser.get_format_instructions()
        )
    
    async def extract_entities_and_relationships(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Extract entities and relationships from text using Vertex AI"""
        try:
            # Prepare the prompt
            prompt_value = self.prompt.format_prompt(text=text)
            
            # Get response from Vertex AI
            response = await self.llm.ainvoke(prompt_value.to_string())
            
            # Parse the response
            try:
                result = self.output_parser.parse(response)
                logger.info(f"Extracted {len(result.entities)} entities and {len(result.relationships)} relationships")
                return result
            except Exception as parse_error:
                logger.warning(f"Failed to parse LLM response: {parse_error}")
                # Try to extract JSON manually
                return self._fallback_parse(response)
                
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Return empty result on failure
            return ExtractionResult()
    
    def _fallback_parse(self, response: str) -> ExtractionResult:
        """Fallback parsing if structured parsing fails"""
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return ExtractionResult(**data)
        except:
            pass
        
        # Return empty result if all parsing fails
        return ExtractionResult()
    
    def extract_entities_and_relationships_sync(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
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