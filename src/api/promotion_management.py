"""
Promotion management API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
from google.cloud import bigquery
from src.services.promotion_service import promotion_service
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/promotions", tags=["promotions"])

class PromotionCreate(BaseModel):
    """Model for creating a new promotion"""
    promotion_name: str = Field(..., example="Summer Sale 20% Off")
    promotion_type: str = Field(..., example="percentage_off", description="percentage_off, dollar_off, bogo, bundle")
    discount_value: float = Field(..., example=20.0)
    days_valid: int = Field(default=30, example=30)
    applicable_products: List[str] = Field(default=[], example=["OV_MILK_WH", "HO_YOGURT"])
    applicable_categories: List[str] = Field(default=[], example=["Dairy", "Beverages"])
    applicable_suppliers: List[str] = Field(default=[], example=["Organic Valley"])
    minimum_purchase: float = Field(default=0.0, example=25.0)
    maximum_discount: Optional[float] = Field(default=None, example=50.0)
    usage_limit_per_user: Optional[int] = Field(default=None, example=1)
    promo_code: Optional[str] = Field(default=None, example="SUMMER20")
    description: str = Field(..., example="Get 20% off select summer items")

class PromotionResponse(BaseModel):
    """Response model for promotion"""
    promotion_id: str
    promotion_name: str
    promotion_type: str
    discount_value: float
    start_date: str
    end_date: str
    promo_code: Optional[str]
    description: str
    is_active: bool
    created_at: str

@router.post("/create", response_model=PromotionResponse)
async def create_promotion(promotion: PromotionCreate):
    """Create a new promotion and save to BigQuery"""
    try:
        # Generate promotion ID
        promotion_id = f"promo_{uuid.uuid4().hex[:12]}"
        
        # Calculate dates
        start_date = datetime.now()
        end_date = start_date + timedelta(days=promotion.days_valid)
        
        # Create promotion object
        new_promotion = {
            "promotion_id": promotion_id,
            "promotion_name": promotion.promotion_name,
            "promotion_type": promotion.promotion_type,
            "discount_value": promotion.discount_value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "applicable_products": promotion.applicable_products,
            "applicable_categories": promotion.applicable_categories,
            "applicable_suppliers": promotion.applicable_suppliers,
            "minimum_purchase": promotion.minimum_purchase,
            "maximum_discount": promotion.maximum_discount,
            "usage_limit_per_user": promotion.usage_limit_per_user,
            "promo_code": promotion.promo_code,
            "is_active": True,
            "description": promotion.description,
            "created_at": start_date.isoformat(),
            "updated_at": start_date.isoformat()
        }
        
        # Save to BigQuery
        client = bigquery.Client(project="leafloafai")
        table_id = "leafloafai.promotions.active_promotions"
        
        errors = client.insert_rows_json(table_id, [new_promotion])
        if errors:
            logger.error(f"BigQuery insert errors: {errors}")
            raise HTTPException(status_code=500, detail="Failed to save promotion")
        
        # Add to in-memory service
        promotion_service.promotions.append(new_promotion)
        
        logger.info(f"Created promotion: {promotion_id}")
        
        return PromotionResponse(
            promotion_id=promotion_id,
            promotion_name=new_promotion["promotion_name"],
            promotion_type=new_promotion["promotion_type"],
            discount_value=new_promotion["discount_value"],
            start_date=new_promotion["start_date"],
            end_date=new_promotion["end_date"],
            promo_code=new_promotion["promo_code"],
            description=new_promotion["description"],
            is_active=new_promotion["is_active"],
            created_at=new_promotion["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error creating promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=List[PromotionResponse])
async def list_promotions(active_only: bool = True):
    """List all promotions"""
    try:
        if active_only:
            promotions = promotion_service.get_active_promotions()
        else:
            promotions = promotion_service.promotions
        
        return [
            PromotionResponse(
                promotion_id=p["promotion_id"],
                promotion_name=p["promotion_name"],
                promotion_type=p["promotion_type"],
                discount_value=p["discount_value"],
                start_date=p["start_date"],
                end_date=p["end_date"],
                promo_code=p.get("promo_code"),
                description=p["description"],
                is_active=p["is_active"],
                created_at=p.get("created_at", p["start_date"])
            )
            for p in promotions
        ]
    except Exception as e:
        logger.error(f"Error listing promotions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{promotion_id}")
async def deactivate_promotion(promotion_id: str):
    """Deactivate a promotion"""
    try:
        # Update in BigQuery
        client = bigquery.Client(project="leafloafai")
        query = f"""
        UPDATE `leafloafai.promotions.active_promotions`
        SET is_active = FALSE,
            updated_at = CURRENT_TIMESTAMP()
        WHERE promotion_id = @promotion_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("promotion_id", "STRING", promotion_id)
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        
        # Update in memory
        for promo in promotion_service.promotions:
            if promo["promotion_id"] == promotion_id:
                promo["is_active"] = False
                break
        
        return {"message": f"Promotion {promotion_id} deactivated"}
        
    except Exception as e:
        logger.error(f"Error deactivating promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test/{promo_code}")
async def test_promotion(promo_code: str, cart_total: float = 50.0):
    """Test if a promotion code is valid and calculate discount"""
    try:
        # Find promotion
        promotion = promotion_service.find_promotion_by_code(promo_code)
        if not promotion:
            return {
                "valid": False,
                "message": "Invalid promo code"
            }
        
        # Check if active
        if not promotion["is_active"]:
            return {
                "valid": False,
                "message": "Promotion is no longer active"
            }
        
        # Check dates
        now = datetime.now()
        start_date = datetime.fromisoformat(promotion["start_date"].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(promotion["end_date"].replace('Z', '+00:00'))
        
        if now < start_date or now > end_date:
            return {
                "valid": False,
                "message": "Promotion is not currently valid"
            }
        
        # Check minimum purchase
        if cart_total < promotion.get("minimum_purchase", 0):
            return {
                "valid": False,
                "message": f"Minimum purchase of ${promotion['minimum_purchase']} required"
            }
        
        # Calculate discount
        discount = 0
        if promotion["promotion_type"] == "percentage_off":
            discount = cart_total * (promotion["discount_value"] / 100)
        elif promotion["promotion_type"] == "dollar_off":
            discount = promotion["discount_value"]
        
        # Apply maximum discount cap
        if promotion.get("maximum_discount") and discount > promotion["maximum_discount"]:
            discount = promotion["maximum_discount"]
        
        return {
            "valid": True,
            "promotion_name": promotion["promotion_name"],
            "discount_amount": round(discount, 2),
            "final_total": round(cart_total - discount, 2),
            "message": f"Promo code applied! You save ${discount:.2f}"
        }
        
    except Exception as e:
        logger.error(f"Error testing promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))