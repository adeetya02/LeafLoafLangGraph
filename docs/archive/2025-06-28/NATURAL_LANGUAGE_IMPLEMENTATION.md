# Natural Language Search Implementation Guide

## 🎯 Overview

Complete implementation for handling images, text, and voice inputs through LLM analysis to structured product suggestions.

---

## 📡 API Endpoint Definition

### Main Endpoint
**POST** `/api/v1/analyze`

### Content Types Supported
- `application/json` - For text/notes input
- `multipart/form-data` - For image uploads
- `application/octet-stream` - For base64 encoded images

---

## 📥 Request Formats

### 1. Image Upload Request

```python
# Using multipart/form-data
POST /api/v1/analyze
Content-Type: multipart/form-data

{
  "image": <binary_file>,  # The image file
  "user_id": "user123",
  "session_id": "session456",
  "context": {
    "user_type": "restaurant",
    "location": "NYC",
    "preferences": {
      "cuisines": ["Indian", "Thai"],
      "dietary": ["vegetarian"]
    }
  },
  "options": {
    "max_products_per_item": 5,
    "include_alternatives": true,
    "include_ml_recommendations": true,
    "confidence_threshold": 0.7
  }
}
```

### 2. Base64 Image Request

```python
# Using JSON with base64 encoding
POST /api/v1/analyze
Content-Type: application/json

{
  "input_type": "image",
  "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA...",
  "user_id": "user123",
  "session_id": "session456",
  "context": {
    "user_type": "retail",
    "meal_planning": true,
    "servings": 20
  }
}
```

### 3. Text/Notes Request

```python
# Direct text input
POST /api/v1/analyze
Content-Type: application/json

{
  "input_type": "text",
  "text": "Grocery List:\n- 2 bags basmati rice\n- Toor dal (1 kg)\n- Oatly milk x 3\n- Frozen okra\n- Samosas for party (30 people)",
  "source": "apple_notes",  # apple_notes | user_input | voice_transcript
  "user_id": "user123",
  "session_id": "session456",
  "context": {
    "user_type": "restaurant",
    "event_context": "party_planning"
  }
}
```

### 4. Voice Transcript Request

```python
# Voice converted to text
POST /api/v1/analyze
Content-Type: application/json

{
  "input_type": "voice",
  "text": "I need rice and lentils for my restaurant probably around 20 pounds each also get me some frozen vegetables",
  "voice_metadata": {
    "duration": 5.2,
    "language": "en-US",
    "confidence": 0.92,
    "accent": "Indian"
  },
  "user_id": "user123",
  "session_id": "session456"
}
```

---

## 🔧 Implementation

### 1. API Endpoint Handler

```python
# src/api/endpoints/analyze.py
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional, Dict, List
import base64
import io
from PIL import Image
import json

router = APIRouter()

@router.post("/api/v1/analyze")
async def analyze_input(
    # For multipart upload
    image: Optional[UploadFile] = File(None),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    context: Optional[str] = Form(None),  # JSON string
    options: Optional[str] = Form(None),  # JSON string
    
    # For JSON requests
    request_body: Optional[Dict] = None
):
    """
    Unified endpoint for natural language grocery extraction
    Supports: images, text, voice transcripts
    """
    
    # Determine input type and extract data
    input_data = None
    input_type = None
    
    # Handle multipart image upload
    if image:
        input_type = "image"
        image_bytes = await image.read()
        input_data = {
            "image_bytes": image_bytes,
            "filename": image.filename,
            "content_type": image.content_type
        }
        # Parse form data
        if context:
            context = json.loads(context)
        if options:
            options = json.loads(options)
    
    # Handle JSON request
    elif request_body:
        input_type = request_body.get("input_type")
        
        if input_type == "image":
            # Handle base64 image
            image_data = request_body.get("image_data", "")
            if image_data.startswith("data:image"):
                # Extract base64 part
                header, encoded = image_data.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                input_data = {"image_bytes": image_bytes}
            else:
                # Direct base64
                image_bytes = base64.b64decode(image_data)
                input_data = {"image_bytes": image_bytes}
        
        elif input_type in ["text", "voice"]:
            input_data = {
                "text": request_body.get("text"),
                "source": request_body.get("source", "user_input"),
                "metadata": request_body.get("voice_metadata", {})
            }
        
        user_id = request_body.get("user_id")
        session_id = request_body.get("session_id")
        context = request_body.get("context", {})
        options = request_body.get("options", {})
    
    else:
        raise HTTPException(400, "No input provided")
    
    # Process the input
    try:
        result = await process_natural_language_input(
            input_type=input_type,
            input_data=input_data,
            user_id=user_id,
            session_id=session_id,
            context=context,
            options=options
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

async def process_natural_language_input(
    input_type: str,
    input_data: Dict,
    user_id: str,
    session_id: str,
    context: Dict,
    options: Dict
) -> Dict:
    """
    Main processing pipeline
    """
    
    # Step 1: Extract text from input
    extracted_text = await extract_text(input_type, input_data)
    
    # Step 2: Send to LLM for analysis
    llm_analysis = await analyze_with_llm(
        text=extracted_text,
        input_type=input_type,
        context=context
    )
    
    # Step 3: Match products for each extraction
    enriched_results = await match_and_enrich_products(
        extractions=llm_analysis["extractions"],
        user_id=user_id,
        context=context,
        options=options
    )
    
    # Step 4: Generate suggestions and compile response
    response = await compile_analysis_response(
        input_analysis={
            "original_text": extracted_text,
            "input_type": input_type,
            "processing_method": "gemma_extraction"
        },
        extracted_items=enriched_results,
        user_id=user_id,
        session_id=session_id,
        context=context
    )
    
    return response
```

### 2. Text Extraction Service

```python
# src/services/text_extraction_service.py
import pytesseract
from PIL import Image
import cv2
import numpy as np

class TextExtractionService:
    def __init__(self):
        self.ocr_engine = "tesseract"  # or "cloud_vision"
        
    async def extract_text(self, input_type: str, input_data: Dict) -> str:
        """Extract text based on input type"""
        
        if input_type == "text":
            return input_data["text"]
        
        elif input_type == "voice":
            # Already transcribed
            return input_data["text"]
        
        elif input_type == "image":
            # Extract text from image
            return await self.extract_from_image(input_data["image_bytes"])
        
        else:
            raise ValueError(f"Unknown input type: {input_type}")
    
    async def extract_from_image(self, image_bytes: bytes) -> str:
        """Extract text from image using OCR"""
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Preprocess image for better OCR
        processed_image = self.preprocess_image(image)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(
            processed_image,
            config='--psm 6'  # Assume uniform block of text
        )
        
        # Alternative: Use Google Cloud Vision for better accuracy
        # text = await self.extract_with_cloud_vision(image_bytes)
        
        return text.strip()
    
    def preprocess_image(self, image: Image) -> Image:
        """Preprocess image for better OCR results"""
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh)
        
        # Convert back to PIL Image
        return Image.fromarray(denoised)
    
    async def extract_with_cloud_vision(self, image_bytes: bytes) -> str:
        """Use Google Cloud Vision for OCR (better accuracy)"""
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            return texts[0].description
        
        return ""

text_extraction_service = TextExtractionService()
```

### 3. LLM Analysis Service

```python
# src/services/llm_analysis_service.py
from typing import List, Dict
import json

class LLMAnalysisService:
    def __init__(self):
        self.model = "gemma-2-9b"
        self.client = VertexAIClient()  # or your LLM client
        
    async def analyze_grocery_text(
        self,
        text: str,
        input_type: str,
        context: Dict
    ) -> Dict:
        """Analyze text with LLM to extract grocery items"""
        
        # Build prompt based on input type
        prompt = self.build_extraction_prompt(text, input_type, context)
        
        # Call LLM
        response = await self.client.generate(
            prompt=prompt,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=1000
        )
        
        # Parse LLM response
        extractions = self.parse_llm_response(response)
        
        return {
            "extractions": extractions,
            "raw_response": response,
            "model_used": self.model
        }
    
    def build_extraction_prompt(self, text: str, input_type: str, context: Dict) -> str:
        """Build prompt for LLM"""
        
        user_context = ""
        if context.get("user_type") == "restaurant":
            user_context = "The user is a restaurant owner, so quantities might be large."
        elif context.get("meal_planning"):
            user_context = f"The user is meal planning for {context.get('servings', 'unknown')} servings."
        
        prompt = f"""Extract grocery items from the following {input_type} input.
For each item, identify:
1. The product name (normalized)
2. Quantity if specified (number and unit)
3. Any modifiers or specific requirements (brand, type, etc.)
4. Confidence score (0-1) for your extraction

{user_context}

Input text:
{text}

Return as JSON array with this structure:
[
  {{
    "raw_text": "original text for this item",
    "product": "normalized product name",
    "quantity": {{"amount": number or null, "unit": "unit or null"}},
    "modifiers": ["list", "of", "modifiers"],
    "confidence": 0.95
  }}
]

Examples:
- "2 bags rice" → {{"product": "rice", "quantity": {{"amount": 2, "unit": "bags"}}, "modifiers": [], "confidence": 0.95}}
- "oatly milk" → {{"product": "milk", "quantity": {{"amount": 1, "unit": "unit"}}, "modifiers": ["oatly"], "confidence": 0.90}}
- "dal (toor)" → {{"product": "dal", "quantity": {{"amount": 1, "unit": "unit"}}, "modifiers": ["toor"], "confidence": 0.88}}

JSON Response:"""
        
        return prompt
    
    def parse_llm_response(self, response: str) -> List[Dict]:
        """Parse LLM response to structured data"""
        
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            json_str = response[json_start:json_end]
            
            # Parse JSON
            extractions = json.loads(json_str)
            
            # Validate and clean
            validated = []
            for item in extractions:
                if item.get("product") and item.get("confidence", 0) > 0.5:
                    validated.append({
                        "raw_text": item.get("raw_text", ""),
                        "normalized_text": item.get("product", ""),
                        "quantity_detected": {
                            "amount": item.get("quantity", {}).get("amount"),
                            "unit": item.get("quantity", {}).get("unit"),
                            "confidence": item.get("confidence", 0.7)
                        },
                        "modifiers": item.get("modifiers", []),
                        "extraction_confidence": item.get("confidence", 0.7)
                    })
            
            return validated
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to basic extraction
            return self.fallback_extraction(response)

llm_analysis_service = LLMAnalysisService()
```

### 4. Product Matching Service

```python
# src/services/product_matching_service.py
from typing import List, Dict
import asyncio

class ProductMatchingService:
    def __init__(self):
        self.weaviate_client = WeaviateClient()
        self.ml_service = MLEnrichmentService()
        
    async def match_products_for_extraction(
        self,
        extraction: Dict,
        user_id: str,
        context: Dict,
        options: Dict
    ) -> List[Dict]:
        """Match products for a single extraction"""
        
        # Build search query
        search_query = self.build_search_query(extraction)
        
        # Search Weaviate
        search_results = await self.weaviate_client.hybrid_search(
            query=search_query,
            limit=options.get("max_products_per_item", 5),
            alpha=0.7  # Favor semantic search for natural language
        )
        
        # Enrich with ML metadata
        enriched_products = []
        for product in search_results:
            enriched = await self.enrich_product(
                product=product,
                extraction=extraction,
                user_id=user_id,
                context=context
            )
            enriched_products.append(enriched)
        
        # Sort by match score
        enriched_products.sort(
            key=lambda p: p["ml_metadata"]["match_score"],
            reverse=True
        )
        
        return enriched_products
    
    def build_search_query(self, extraction: Dict) -> str:
        """Build search query from extraction"""
        
        # Start with normalized product name
        query_parts = [extraction["normalized_text"]]
        
        # Add modifiers
        if modifiers := extraction.get("modifiers", []):
            query_parts.extend(modifiers)
        
        # Join into search query
        return " ".join(query_parts)
    
    async def enrich_product(
        self,
        product: Dict,
        extraction: Dict,
        user_id: str,
        context: Dict
    ) -> Dict:
        """Enrich product with full data structure"""
        
        # Calculate match score
        match_score = self.calculate_match_score(product, extraction)
        
        # Get ML recommendations
        ml_data = await self.ml_service.get_product_ml_data(
            product_id=product["product_id"],
            user_id=user_id
        )
        
        # Build enriched product structure
        return {
            "product": {
                "product_id": product["product_id"],
                "sku": product["sku"],
                "upc": product.get("upc"),
                "product_name": product["product_name"],
                "brand": product["brand"],
                "supplier": product["supplier"]
            },
            
            "attributes": {
                "category": product["category"],
                "subcategory": product.get("subcategory"),
                "cuisine": product.get("cuisine"),
                "ethnic_category": product.get("ethnic_category"),
                
                "packaging": {
                    "size": product.get("pack_size"),
                    "format": product.get("pack_format"),
                    "units_per_case": product.get("units_per_case", 1)
                },
                
                "dietary": {
                    "is_organic": product.get("is_organic", False),
                    "is_gluten_free": product.get("is_gluten_free", False),
                    "is_vegan": product.get("is_vegan", False),
                    "is_halal": product.get("is_halal", False)
                },
                
                "search_terms": product.get("search_terms", [])
            },
            
            "pricing": {
                "base_price": product["price"],
                "currency": "USD",
                "promotion": await self.get_active_promotion(product["sku"])
            },
            
            "ml_metadata": {
                "match_score": match_score,
                "match_reason": self.get_match_reason(match_score),
                "ranking_factors": {
                    "text_similarity": match_score,
                    "popularity_score": ml_data.get("popularity", 0.5),
                    "user_preference_match": ml_data.get("preference_score", 0.5)
                },
                "recommendation_context": ml_data.get("recommendations", {}),
                "personalization": ml_data.get("personalization", {})
            },
            
            "availability": {
                "in_stock": product.get("in_stock", True),
                "stock_level": "high"  # TODO: Real inventory check
            },
            
            "media": {
                "thumbnail": f"https://cdn.leafloaf.com/products/{product['sku']}_thumb.jpg",
                "main_image": f"https://cdn.leafloaf.com/products/{product['sku']}_main.jpg"
            }
        }
    
    def calculate_match_score(self, product: Dict, extraction: Dict) -> float:
        """Calculate how well product matches extraction"""
        
        score = 0.0
        
        # Exact product name match
        if extraction["normalized_text"].lower() in product["product_name"].lower():
            score += 0.4
        
        # Modifier matches
        for modifier in extraction.get("modifiers", []):
            if modifier.lower() in product["product_name"].lower():
                score += 0.2
            elif modifier.lower() in product.get("search_terms", []):
                score += 0.1
        
        # Category match
        if extraction["normalized_text"].lower() in product["category"].lower():
            score += 0.2
        
        # Boost for exact brand match
        if extraction.get("modifiers"):
            for modifier in extraction["modifiers"]:
                if modifier.lower() == product["brand"].lower():
                    score += 0.3
        
        # Normalize to 0-1
        return min(score, 1.0)

product_matching_service = ProductMatchingService()
```

### 5. Response Compilation

```python
# src/services/response_compilation_service.py

async def compile_analysis_response(
    input_analysis: Dict,
    extracted_items: List[Dict],
    user_id: str,
    session_id: str,
    context: Dict
) -> Dict:
    """Compile final response structure"""
    
    # Calculate analytics
    analytics = calculate_extraction_analytics(extracted_items)
    
    # Generate suggestions
    suggestions = generate_suggestions(extracted_items, context)
    
    # Build response
    response = {
        "status": "success",
        "data": {
            "input_analysis": input_analysis,
            "extracted_items": extracted_items,
            "suggestions": suggestions,
            "analytics": analytics
        },
        "meta": {
            "performance": {
                "total_ms": 450,  # TODO: Real timing
                "breakdown": {
                    "text_extraction": 120,
                    "llm_analysis": 150,
                    "product_matching": 100,
                    "enrichment": 80
                }
            },
            "model_used": "gemma-2-9b",
            "confidence_threshold": 0.70,
            "request_id": f"req_{generate_request_id()}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    return response
```

---

## 🧪 Testing the Implementation

### 1. Test with Image Upload

```bash
# Using curl
curl -X POST https://api.leafloaf.com/api/v1/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@shopping_list.jpg" \
  -F "user_id=user123" \
  -F "context={\"user_type\":\"restaurant\"}"

# Using Python
import requests

with open('shopping_list.jpg', 'rb') as f:
    response = requests.post(
        'https://api.leafloaf.com/api/v1/analyze',
        files={'image': f},
        data={
            'user_id': 'user123',
            'context': json.dumps({'user_type': 'restaurant'})
        }
    )
    
print(response.json())
```

### 2. Test with Text

```python
# Direct text input
response = requests.post(
    'https://api.leafloaf.com/api/v1/analyze',
    json={
        'input_type': 'text',
        'text': '''Grocery List:
        - 2 bags basmati rice
        - Toor dal (1 kg)
        - Oatly milk x 3
        - Frozen okra
        - Samosas for party''',
        'user_id': 'user123',
        'context': {
            'user_type': 'restaurant',
            'event_context': 'party_planning'
        }
    }
)
```

### 3. Response Monitoring

```python
# Log and monitor responses
def log_analysis_response(response: Dict):
    # Track extraction quality
    extraction_quality = response['data']['analytics']['extraction_quality']
    logger.info(f"Extraction quality: {extraction_quality}")
    
    # Track matching quality
    matching_quality = response['data']['analytics']['matching_quality']
    logger.info(f"Matching quality: {matching_quality}")
    
    # Send to analytics
    send_to_bigquery({
        'event_type': 'natural_language_analysis',
        'user_id': response['data']['analytics']['user_context']['user_id'],
        'extraction_count': extraction_quality['total_items_detected'],
        'match_rate': matching_quality['average_match_score'],
        'response_time_ms': response['meta']['performance']['total_ms']
    })
```

---

## 📊 Debugging Tools

### 1. Request/Response Logger

```python
# Middleware to log all requests/responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request
    body = await request.body()
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Body: {body[:1000]}")  # First 1000 chars
    
    # Process request
    response = await call_next(request)
    
    # Log response
    logger.info(f"Response: {response.status_code}")
    
    return response
```

### 2. Debug Mode Response

```python
# Add debug info when requested
if options.get("debug", False):
    response["debug"] = {
        "ocr_text": extracted_text,
        "llm_prompt": prompt,
        "llm_raw_response": llm_response,
        "search_queries": search_queries,
        "match_scores": match_scores
    }
```

This implementation provides a complete flow from image/text input through OCR, LLM analysis, product matching, and response generation with rich metadata for ML and analytics.