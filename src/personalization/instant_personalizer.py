"""
Production-Grade Instant Personalization System for LeafLoaf

High-performance, scalable personalization with sub-100ms response times.
Designed for production use with proper error handling, monitoring, and scalability.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
import structlog

from src.utils.metrics import track_timing, track_counter
from src.config.constants import (
    PERSONALIZATION_CACHE_TTL,
    PERSONALIZATION_MAX_SIGNALS_PER_USER,
    PERSONALIZATION_DECAY_FACTOR
)

logger = structlog.get_logger()


class SignalType(Enum):
    """Types of user interaction signals"""
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    VIEW_DETAILS = "view_details"
    REMOVE_FROM_CART = "remove_from_cart"
    SEARCH = "search"


@dataclass
class InteractionSignal:
    """Immutable representation of a user interaction"""
    user_id: str
    signal_type: SignalType
    product_id: str
    timestamp: datetime
    strength: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate signal data"""
        if not 0 <= self.strength <= 1.0:
            raise ValueError(f"Signal strength must be between 0 and 1, got {self.strength}")


@dataclass
class ProductFeatures:
    """Extracted features from a product for matching"""
    category: str
    subcategory: Optional[str]
    brand: Optional[str]
    attributes: Set[str]
    dietary_tags: Set[str]
    price_tier: str  # budget, standard, premium
    
    @classmethod
    def from_product(cls, product: Dict[str, Any]) -> 'ProductFeatures':
        """Factory method to create features from product data"""
        # Extract attributes safely
        name = product.get("name", "").lower()
        category = product.get("category", "").lower()
        brand = product.get("brand", "").lower()
        
        # Extract dietary attributes
        dietary_tags = set()
        dietary_info = product.get("dietary_info", [])
        if isinstance(dietary_info, list):
            dietary_tags.update(tag.lower() for tag in dietary_info)
        
        # Extract product attributes
        attributes = set()
        
        # Detect plant-based alternatives
        plant_indicators = ["oat", "almond", "soy", "coconut", "cashew", "rice", "hemp"]
        if any(plant in name for plant in plant_indicators):
            attributes.add("plant_based")
            
        # Detect organic
        if "organic" in name or "organic" in dietary_tags:
            attributes.add("organic")
            
        # Detect local/artisanal
        if any(term in name for term in ["local", "farm", "artisan", "craft"]):
            attributes.add("local")
            
        # Price tier classification
        price = product.get("price", 0)
        if price < 3:
            price_tier = "budget"
        elif price < 8:
            price_tier = "standard"
        else:
            price_tier = "premium"
            
        return cls(
            category=category,
            subcategory=product.get("subcategory", ""),
            brand=brand if brand not in ["", "generic", "store brand"] else None,
            attributes=attributes,
            dietary_tags=dietary_tags,
            price_tier=price_tier
        )


class UserPreferenceModel:
    """Production-grade user preference model with decay and normalization"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.category_scores: Dict[str, float] = defaultdict(float)
        self.brand_scores: Dict[str, float] = defaultdict(float)
        self.attribute_scores: Dict[str, float] = defaultdict(float)
        self.negative_signals: Dict[str, float] = defaultdict(float)
        self.last_interaction: datetime = datetime.utcnow()
        self.interaction_count: int = 0
        
        # Signal history for decay calculation
        self.signal_history: deque = deque(maxlen=PERSONALIZATION_MAX_SIGNALS_PER_USER)
        
    def add_signal(self, signal: InteractionSignal, features: ProductFeatures):
        """Add a new signal and update preferences"""
        # Update interaction metadata
        self.last_interaction = signal.timestamp
        self.interaction_count += 1
        
        # Apply time decay to existing preferences
        self._apply_time_decay()
        
        # Update scores based on signal type and strength
        multiplier = self._get_signal_multiplier(signal.signal_type)
        base_strength = signal.strength * multiplier
        
        # Update category preference
        if features.category:
            self.category_scores[features.category] += base_strength * 0.4
            
        # Update brand preference
        if features.brand:
            self.brand_scores[features.brand] += base_strength * 0.3
            
        # Update attribute preferences
        for attr in features.attributes:
            self.attribute_scores[attr] += base_strength * 0.3
            
        # Handle negative signals
        if signal.signal_type in [SignalType.REMOVE_FROM_CART]:
            self.negative_signals[signal.product_id] += abs(base_strength)
            
        # Add to history
        self.signal_history.append(signal)
        
        # Normalize scores to prevent unbounded growth
        self._normalize_scores()
        
    def _get_signal_multiplier(self, signal_type: SignalType) -> float:
        """Get multiplier based on signal type importance"""
        multipliers = {
            SignalType.PURCHASE: 1.0,
            SignalType.ADD_TO_CART: 0.5,
            SignalType.CLICK: 0.2,
            SignalType.VIEW_DETAILS: 0.3,
            SignalType.REMOVE_FROM_CART: -0.4,
            SignalType.SEARCH: 0.1
        }
        return multipliers.get(signal_type, 0.1)
        
    def _apply_time_decay(self):
        """Apply exponential decay to preferences based on time"""
        if not self.last_interaction:
            return
            
        time_since_last = datetime.utcnow() - self.last_interaction
        days_elapsed = time_since_last.total_seconds() / 86400
        
        if days_elapsed > 1:
            decay_factor = PERSONALIZATION_DECAY_FACTOR ** days_elapsed
            
            for scores in [self.category_scores, self.brand_scores, self.attribute_scores]:
                for key in scores:
                    scores[key] *= decay_factor
                    
    def _normalize_scores(self):
        """Normalize scores to prevent unbounded growth"""
        # Find max score across all dimensions
        all_scores = list(self.category_scores.values()) + \
                    list(self.brand_scores.values()) + \
                    list(self.attribute_scores.values())
                    
        if not all_scores:
            return
            
        max_score = max(all_scores)
        if max_score > 10:  # Normalize if any score exceeds threshold
            scale_factor = 10 / max_score
            
            for scores in [self.category_scores, self.brand_scores, self.attribute_scores]:
                for key in scores:
                    scores[key] *= scale_factor
                    
    def calculate_product_score(self, features: ProductFeatures) -> float:
        """Calculate personalization score for a product"""
        score = 0.0
        
        # Category matching (40% weight)
        if features.category in self.category_scores:
            score += self.category_scores[features.category] * 0.4
            
        # Brand matching (30% weight)
        if features.brand and features.brand in self.brand_scores:
            score += self.brand_scores[features.brand] * 0.3
            
        # Attribute matching (30% weight)
        attr_score = 0.0
        for attr in features.attributes:
            if attr in self.attribute_scores:
                attr_score += self.attribute_scores[attr]
        
        # Normalize attribute score by number of attributes
        if features.attributes:
            score += (attr_score / len(features.attributes)) * 0.3
            
        return min(score, 1.0)  # Cap at 1.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize preference model for caching"""
        return {
            "user_id": self.user_id,
            "category_scores": dict(self.category_scores),
            "brand_scores": dict(self.brand_scores),
            "attribute_scores": dict(self.attribute_scores),
            "negative_signals": dict(self.negative_signals),
            "last_interaction": self.last_interaction.isoformat(),
            "interaction_count": self.interaction_count
        }


class InstantPersonalizationEngine:
    """
    Production-grade instant personalization engine.
    Thread-safe, scalable, with proper monitoring and error handling.
    """
    
    def __init__(self):
        # Thread-safe user preference storage
        self._preferences: Dict[str, UserPreferenceModel] = {}
        self._preferences_lock = asyncio.Lock()
        
        # Product feature cache for performance
        self._feature_cache: Dict[str, ProductFeatures] = {}
        self._feature_cache_lock = asyncio.Lock()
        
        # Performance monitoring
        self._metrics = {
            "preference_updates": deque(maxlen=1000),
            "personalization_times": deque(maxlen=1000),
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Background executor for non-blocking operations
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Instant personalization engine initialized")
        
    async def track_interaction(
        self,
        user_id: str,
        product: Dict[str, Any],
        signal_type: Union[str, SignalType],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track user interaction and update preferences.
        Production-grade with proper error handling and monitoring.
        """
        start_time = time.time()
        
        try:
            # Convert string to SignalType if needed
            if isinstance(signal_type, str):
                signal_type = SignalType(signal_type)
                
            # Create interaction signal
            signal = InteractionSignal(
                user_id=user_id,
                signal_type=signal_type,
                product_id=product.get("sku", product.get("id", "")),
                timestamp=datetime.utcnow(),
                strength=self._calculate_signal_strength(signal_type, metadata),
                metadata=metadata or {}
            )
            
            # Get or create product features
            features = await self._get_product_features(product)
            
            # Update user preferences
            async with self._preferences_lock:
                if user_id not in self._preferences:
                    self._preferences[user_id] = UserPreferenceModel(user_id)
                    
                user_model = self._preferences[user_id]
                user_model.add_signal(signal, features)
            
            # Track metrics
            update_time_ms = (time.time() - start_time) * 1000
            self._metrics["preference_updates"].append(update_time_ms)
            
            # Log for monitoring
            track_counter("personalization.interaction.tracked", 1, {
                "signal_type": signal_type.value,
                "user_id": user_id
            })
            
            return {
                "success": True,
                "update_time_ms": round(update_time_ms, 2),
                "signal_type": signal_type.value,
                "preference_count": len(user_model.category_scores) + 
                                  len(user_model.brand_scores) + 
                                  len(user_model.attribute_scores)
            }
            
        except Exception as e:
            logger.error(f"Failed to track interaction: {e}", user_id=user_id)
            track_counter("personalization.interaction.error", 1)
            return {
                "success": False,
                "error": str(e),
                "update_time_ms": (time.time() - start_time) * 1000
            }
            
    async def personalize_results(
        self,
        user_id: str,
        products: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply personalization to search results.
        Returns personalized products and performance metrics.
        """
        start_time = time.time()
        
        try:
            # Get user preferences
            async with self._preferences_lock:
                user_model = self._preferences.get(user_id)
                
            if not user_model or user_model.interaction_count < 1:
                # No personalization for new users
                return products, {
                    "personalized": False,
                    "reason": "insufficient_data",
                    "time_ms": 0
                }
                
            # Score products in parallel for performance
            scored_products = await self._score_products_parallel(products, user_model)
            
            # Sort by personalization score
            scored_products.sort(key=lambda p: p.get("_personalization_score", 0), reverse=True)
            
            # Track metrics
            personalization_time_ms = (time.time() - start_time) * 1000
            self._metrics["personalization_times"].append(personalization_time_ms)
            
            # Check if order changed
            original_ids = [p.get("sku", p.get("id")) for p in products[:5]]
            new_ids = [p.get("sku", p.get("id")) for p in scored_products[:5]]
            reranked = original_ids != new_ids
            
            # Log for monitoring
            track_timing("personalization.apply", personalization_time_ms, {
                "user_id": user_id,
                "product_count": len(products),
                "reranked": str(reranked)
            })
            
            return scored_products, {
                "personalized": True,
                "time_ms": round(personalization_time_ms, 2),
                "products_scored": len(scored_products),
                "reranked": reranked,
                "preference_signals": {
                    "categories": len(user_model.category_scores),
                    "brands": len(user_model.brand_scores),
                    "attributes": len(user_model.attribute_scores)
                }
            }
            
        except Exception as e:
            logger.error(f"Personalization failed: {e}", user_id=user_id)
            track_counter("personalization.apply.error", 1)
            
            # Return original products on error
            return products, {
                "personalized": False,
                "reason": "error",
                "error": str(e),
                "time_ms": (time.time() - start_time) * 1000
            }
            
    async def _get_product_features(self, product: Dict[str, Any]) -> ProductFeatures:
        """Get product features with caching"""
        product_id = product.get("sku", product.get("id", ""))
        
        # Check cache first
        async with self._feature_cache_lock:
            if product_id in self._feature_cache:
                self._metrics["cache_hits"] += 1
                return self._feature_cache[product_id]
        
        # Extract features
        features = ProductFeatures.from_product(product)
        
        # Cache for future use
        async with self._feature_cache_lock:
            self._feature_cache[product_id] = features
            self._metrics["cache_misses"] += 1
            
            # Limit cache size
            if len(self._feature_cache) > 10000:
                # Remove oldest entries
                oldest_keys = list(self._feature_cache.keys())[:1000]
                for key in oldest_keys:
                    del self._feature_cache[key]
                    
        return features
        
    async def _score_products_parallel(
        self,
        products: List[Dict[str, Any]],
        user_model: UserPreferenceModel
    ) -> List[Dict[str, Any]]:
        """Score products in parallel for performance"""
        async def score_product(product: Dict[str, Any]) -> Dict[str, Any]:
            features = await self._get_product_features(product)
            score = user_model.calculate_product_score(features)
            
            product_copy = product.copy()
            product_copy["_personalization_score"] = score
            return product_copy
            
        # Process in parallel
        tasks = [score_product(p) for p in products]
        return await asyncio.gather(*tasks)
        
    def _calculate_signal_strength(
        self,
        signal_type: SignalType,
        metadata: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate signal strength based on type and context"""
        base_strengths = {
            SignalType.PURCHASE: 1.0,
            SignalType.ADD_TO_CART: 0.5,
            SignalType.CLICK: 0.2,
            SignalType.VIEW_DETAILS: 0.3,
            SignalType.REMOVE_FROM_CART: 0.4,
            SignalType.SEARCH: 0.1
        }
        
        strength = base_strengths.get(signal_type, 0.1)
        
        # Adjust based on context
        if metadata:
            # Higher strength for items found after scrolling
            if metadata.get("position", 0) > 5:
                strength *= 1.2
                
            # Higher strength for repeated actions
            if metadata.get("repeat_action", False):
                strength *= 1.5
                
        return min(strength, 1.0)
        
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get current user preferences for inspection"""
        async with self._preferences_lock:
            user_model = self._preferences.get(user_id)
            
        if not user_model:
            return {
                "user_id": user_id,
                "has_preferences": False
            }
            
        # Get top preferences
        top_categories = sorted(
            user_model.category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_brands = sorted(
            user_model.brand_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        top_attributes = sorted(
            user_model.attribute_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "user_id": user_id,
            "has_preferences": True,
            "interaction_count": user_model.interaction_count,
            "last_interaction": user_model.last_interaction.isoformat(),
            "top_categories": dict(top_categories),
            "top_brands": dict(top_brands),
            "top_attributes": dict(top_attributes)
        }
        
    async def reset_user_preferences(self, user_id: str):
        """Reset user preferences (for demo/testing)"""
        async with self._preferences_lock:
            if user_id in self._preferences:
                del self._preferences[user_id]
                
        logger.info(f"Reset preferences for user {user_id}")
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        update_times = list(self._metrics["preference_updates"])
        personalization_times = list(self._metrics["personalization_times"])
        
        return {
            "preference_updates": {
                "count": len(update_times),
                "avg_ms": round(sum(update_times) / len(update_times), 2) if update_times else 0,
                "p95_ms": round(sorted(update_times)[int(len(update_times) * 0.95)], 2) if update_times else 0
            },
            "personalization": {
                "count": len(personalization_times),
                "avg_ms": round(sum(personalization_times) / len(personalization_times), 2) if personalization_times else 0,
                "p95_ms": round(sorted(personalization_times)[int(len(personalization_times) * 0.95)], 2) if personalization_times else 0
            },
            "cache": {
                "hits": self._metrics["cache_hits"],
                "misses": self._metrics["cache_misses"],
                "hit_rate": round(self._metrics["cache_hits"] / (self._metrics["cache_hits"] + self._metrics["cache_misses"]), 2) if self._metrics["cache_hits"] + self._metrics["cache_misses"] > 0 else 0
            },
            "active_users": len(self._preferences),
            "cached_products": len(self._feature_cache)
        }


# Global singleton instance
_engine_instance = None

def get_personalization_engine() -> InstantPersonalizationEngine:
    """Get or create the global personalization engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = InstantPersonalizationEngine()
    return _engine_instance