"""
Dietary & Cultural Intelligence Agent

This module provides intelligent dietary pattern detection and cultural food understanding.
It learns from user purchase history to provide personalized filtering and suggestions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from enum import Enum
import time
import logging

from src.models.user_preferences import UserPreferences
from src.config.constants import DIETARY_ATTRIBUTES

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for pattern detection"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class DietaryRestriction(Enum):
    """Common dietary restrictions"""
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    GLUTEN_FREE = "gluten-free"
    DAIRY_FREE = "dairy-free"
    NUT_FREE = "nut-free"
    KOSHER = "kosher"
    HALAL = "halal"
    LOW_SODIUM = "low-sodium"
    DIABETIC = "diabetic"


@dataclass
class DietaryProfile:
    """User's dietary profile based on purchase patterns"""
    restrictions: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    avoided_ingredients: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    insufficient_data: bool = False
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class CulturalPattern:
    """Detected cultural food patterns"""
    pattern_name: str
    common_ingredients: List[str]
    meal_types: List[str] = field(default_factory=list)
    shopping_frequency: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0
    suggests_vegetarian: bool = False


class DietaryCulturalIntelligence:
    """Main class for dietary and cultural intelligence"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache = {}
        self.min_orders_for_pattern = 5
        self.confidence_threshold = 0.7
        
    def analyze_dietary_patterns(
        self, 
        user_id: str, 
        purchase_history: List[Dict]
    ) -> DietaryProfile:
        """Analyze purchase history to detect dietary patterns"""
        if not purchase_history:
            return DietaryProfile(insufficient_data=True)
            
        # Check cache first
        cache_key = f"dietary_profile_{user_id}"
        if self.cache_enabled and cache_key in self._cache:
            cached_profile = self._cache[cache_key]
            if (datetime.now() - cached_profile.last_updated).seconds < 3600:
                return cached_profile
        
        # Analyze patterns
        dietary_counts = defaultdict(int)
        total_products = 0
        
        for order in purchase_history:
            for product in order.get("products", []):
                total_products += 1
                
                # Check for dietary indicators
                categories = product.get("categories", [])
                tags = product.get("tags", [])
                all_attributes = categories + tags
                
                # Detect vegan pattern
                if "vegan" in all_attributes:
                    dietary_counts["vegan"] += 1
                elif any(attr in ["meat", "dairy", "eggs"] for attr in all_attributes):
                    dietary_counts["non-vegan"] += 1
                
                # Detect gluten-free pattern
                if "gluten-free" in all_attributes:
                    dietary_counts["gluten-free"] += 1
                elif "gluten" in all_attributes:
                    dietary_counts["has-gluten"] += 1
                    
                # Detect other patterns
                for attr in ["dairy-free", "nut-free", "kosher", "halal", "low-sodium"]:
                    if attr in all_attributes:
                        dietary_counts[attr] += 1
        
        # Calculate confidence scores
        profile = DietaryProfile()
        
        if total_products >= self.min_orders_for_pattern:
            # Vegan detection
            vegan_ratio = dietary_counts["vegan"] / total_products if total_products > 0 else 0
            non_vegan_ratio = dietary_counts["non-vegan"] / total_products if total_products > 0 else 0
            
            if vegan_ratio > 0.8 and non_vegan_ratio < 0.1:
                profile.restrictions.append("vegan")
                profile.confidence_scores["vegan"] = min(vegan_ratio, 0.95)
            
            # Gluten-free detection
            gf_ratio = dietary_counts["gluten-free"] / total_products if total_products > 0 else 0
            if gf_ratio > 0.7:
                profile.restrictions.append("gluten-free")
                profile.confidence_scores["gluten-free"] = min(gf_ratio, 0.95)
                
            # Other restrictions
            for restriction in ["dairy-free", "nut-free", "low-sodium"]:
                ratio = dietary_counts[restriction] / total_products if total_products > 0 else 0
                if ratio > 0.6:
                    profile.restrictions.append(restriction)
                    profile.confidence_scores[restriction] = min(ratio, 0.95)
        else:
            profile.insufficient_data = True
            
        # Cache the result
        if self.cache_enabled:
            self._cache[cache_key] = profile
            
        return profile
    
    def detect_cultural_patterns(
        self,
        user_id: str,
        purchase_history: List[Dict]
    ) -> Optional[CulturalPattern]:
        """Detect cultural cuisine patterns from purchase history"""
        if not purchase_history:
            return None
            
        # Analyze ingredient patterns
        ingredient_counts = Counter()
        cuisine_indicators = {
            "south_indian_cooking": ["toor dal", "curry leaves", "sambar powder", 
                                   "idli rice", "urad dal", "mustard seeds"],
            "italian_cooking": ["pasta", "basil", "mozzarella", "olive oil", 
                              "parmesan", "tomatoes"],
            "mexican_cooking": ["tortillas", "cilantro", "jalapeños", "black beans",
                              "salsa", "avocado"],
            "indian_vegetarian": ["paneer", "garam masala", "basmati rice", 
                                "turmeric", "cumin", "coriander"]
        }
        
        # Count ingredients
        for order in purchase_history:
            for product in order.get("products", []):
                name = product.get("name", "").lower()
                ingredient_counts[name] += 1
                
                # Check categories
                categories = product.get("categories", [])
                for cat in categories:
                    if "indian" in cat.lower():
                        ingredient_counts["_indian_category"] += 1
                    elif "italian" in cat.lower():
                        ingredient_counts["_italian_category"] += 1
        
        # Find best matching pattern
        best_pattern = None
        best_score = 0
        
        for pattern_name, indicators in cuisine_indicators.items():
            score = sum(ingredient_counts.get(ind.lower(), 0) for ind in indicators)
            category_boost = ingredient_counts.get(f"_{pattern_name.split('_')[0]}_category", 0)
            total_score = score + (category_boost * 0.5)
            
            if total_score > best_score and total_score >= 3:  # Minimum threshold
                best_score = total_score
                best_pattern = pattern_name
                
        if best_pattern:
            pattern = CulturalPattern(
                pattern_name=best_pattern,
                common_ingredients=[ing for ing in cuisine_indicators[best_pattern]
                                  if ingredient_counts.get(ing.lower(), 0) > 0],
                confidence=min(best_score / 8, 0.95)  # Adjusted for better scoring
            )
            
            # Set vegetarian flag for Indian patterns
            if "indian" in best_pattern:
                pattern.suggests_vegetarian = True
                
            return pattern
            
        return None
    
    def filter_products(
        self,
        products: List[Dict],
        dietary_profile: DietaryProfile
    ) -> List[Dict]:
        """Filter products based on dietary restrictions"""
        if not dietary_profile.restrictions:
            return products
            
        filtered = []
        
        for product in products:
            tags = product.get("tags", [])
            should_include = True
            
            for restriction in dietary_profile.restrictions:
                if restriction == "vegan":
                    # Exclude if contains animal products
                    if any(tag in ["dairy", "meat", "eggs", "honey"] for tag in tags):
                        should_include = False
                        break
                    # Include if explicitly vegan
                    if "vegan" not in tags and "plant-based" not in tags:
                        # Check if it's implicitly vegan (like fruits, vegetables)
                        categories = product.get("categories", [])
                        if not any(cat in ["produce", "grains", "legumes"] for cat in categories):
                            should_include = False
                            break
                            
                elif restriction == "gluten-free":
                    if "gluten" in tags or "wheat" in tags:
                        should_include = False
                        break
                        
                elif restriction == "dairy-free":
                    if "dairy" in tags or "milk" in tags or "cheese" in tags:
                        should_include = False
                        break
                        
                elif restriction == "nut-free":
                    if any("nut" in tag for tag in tags) or "peanut" in tags:
                        should_include = False
                        break
                        
                elif restriction == "low-sodium":
                    if "high-sodium" in tags:
                        should_include = False
                        break
            
            if should_include:
                filtered.append(product)
                
        return filtered
    
    def suggest_cultural_alternatives(
        self,
        search_query: str,
        cultural_pattern: Optional[CulturalPattern]
    ) -> List[str]:
        """Suggest culturally appropriate alternatives"""
        if not cultural_pattern:
            return []
            
        alternatives = []
        
        # Define cultural substitutions
        cultural_substitutions = {
            "south_indian_cooking": {
                "pasta": ["rice sevai", "idiappam", "rice noodles"],
                "bread": ["dosa", "idli", "appam", "chapati"],
                "cheese": ["paneer", "coconut", "cashew cream"],
                "noodles": ["sevai", "idiappam", "rice vermicelli"]
            },
            "indian_vegetarian": {
                "meat": ["paneer", "tofu", "soy chunks", "mushrooms"],
                "chicken": ["soy chunks", "paneer tikka", "mushrooms"],
                "beef": ["jackfruit", "mushrooms", "plant-based meat"]
            }
        }
        
        # Get alternatives for the cultural pattern
        if cultural_pattern.pattern_name in cultural_substitutions:
            subs = cultural_substitutions[cultural_pattern.pattern_name]
            query_lower = search_query.lower()
            
            for item, alts in subs.items():
                if item in query_lower:
                    alternatives.extend(alts)
                    
        return alternatives[:5]  # Return top 5 alternatives
    
    def learn_ingredient_combinations(
        self,
        user_id: str,
        purchase_history: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Learn common ingredient combinations from purchase history"""
        combinations = defaultdict(int)
        combination_details = {}
        
        for order in purchase_history:
            products = order.get("products", [])
            if len(products) >= 2:
                # Extract product names
                product_names = [p.get("name", "").lower() for p in products]
                
                # Find frequent pairs
                for i in range(len(product_names)):
                    for j in range(i + 1, len(product_names)):
                        pair = tuple(sorted([product_names[i], product_names[j]]))
                        combinations[pair] += 1
                        
                # Find frequent triplets
                if len(product_names) >= 3:
                    for i in range(len(product_names)):
                        for j in range(i + 1, len(product_names)):
                            for k in range(j + 1, len(product_names)):
                                triplet = tuple(sorted([product_names[i], 
                                                      product_names[j], 
                                                      product_names[k]]))
                                combinations[triplet] += 1
        
        # Convert to list format
        result = []
        for combo, frequency in combinations.items():
            if frequency >= 2:  # Minimum frequency threshold
                result.append({
                    "ingredients": list(combo),
                    "frequency": frequency,
                    "type": "pair" if len(combo) == 2 else "triplet"
                })
                
        # Sort by frequency
        result.sort(key=lambda x: x["frequency"], reverse=True)
        
        return result[:20]  # Return top 20 combinations
    
    def apply_intelligence(
        self,
        products: List[Dict],
        user_preferences: UserPreferences,
        dietary_profile: Optional[DietaryProfile] = None
    ) -> List[Dict]:
        """Apply dietary intelligence with feature toggle respect"""
        # Check if feature is enabled
        if not user_preferences.is_feature_enabled("dietary_filters"):
            return products
            
        # If no profile provided, return original products
        if not dietary_profile or not dietary_profile.restrictions:
            return products
            
        # Apply filtering
        return self.filter_products(products, dietary_profile)
    
    def filter_with_explanation(
        self,
        products: List[Dict],
        dietary_profile: DietaryProfile
    ) -> Dict[str, Any]:
        """Filter products and provide detailed explanation"""
        filtered_products = []
        filter_reasons = {}
        removed_count = 0
        
        for product in products:
            tags = product.get("tags", [])
            product_id = product.get("id", product.get("name", "unknown"))
            include = True
            reason = None
            
            for restriction in dietary_profile.restrictions:
                if restriction == "vegan" and any(tag in ["dairy", "meat", "eggs"] for tag in tags):
                    include = False
                    reason = "Contains dairy (non-vegan)" if "dairy" in tags else "Contains animal products (non-vegan)"
                    break
                    
            if include:
                filtered_products.append(product)
            else:
                removed_count += 1
                filter_reasons[product_id] = reason
                
        # Build explanation
        restriction_text = ", ".join(dietary_profile.restrictions)
        confidence_text = f"(confidence: {dietary_profile.confidence_scores.get(dietary_profile.restrictions[0], 0):.0%})" if dietary_profile.restrictions else ""
        
        explanation = f"Filtered to show {restriction_text} options {confidence_text}"
        if removed_count > 0:
            explanation += f". Removed {removed_count} incompatible products."
            
        return {
            "filtered_products": filtered_products,
            "explanation": explanation,
            "removed_count": removed_count,
            "filter_reasons": filter_reasons
        }
    
    def detect_allergen_avoidance(
        self,
        user_id: str,
        purchase_history: List[Dict],
        viewed_but_not_purchased: List[str] = None
    ) -> Dict[str, Any]:
        """Detect potential allergen avoidance patterns"""
        allergen_data = {}
        
        # Check for consistent avoidance
        all_products = []
        for order in purchase_history:
            all_products.extend(order.get("products", []))
            
        # Check common allergens
        allergens_to_check = ["nut", "peanut", "shellfish", "egg", "soy", "wheat"]
        
        for allergen in allergens_to_check:
            found_count = sum(1 for p in all_products 
                            if allergen in str(p.get("allergens", [])).lower() 
                            or allergen in p.get("name", "").lower())
            
            if found_count == 0 and len(all_products) > 20:
                # Check viewed but not purchased
                avoided_count = 0
                if viewed_but_not_purchased:
                    avoided_count = sum(1 for item in viewed_but_not_purchased 
                                      if allergen in item.lower())
                
                if avoided_count >= 3:
                    allergen_data[f"{allergen}_allergy"] = {
                        "confidence": 0.95,
                        "requires_confirmation": True,
                        "evidence": f"Never purchased {allergen} products, viewed but avoided {avoided_count} times"
                    }
                    
        return allergen_data
    
    def detect_seasonal_patterns(
        self,
        user_id: str,
        purchase_history: List[Dict]
    ) -> Dict[str, Any]:
        """Detect seasonal and festival-based shopping patterns"""
        seasonal_data = {
            "patterns": [],
            "upcoming_suggestions": None
        }
        
        # Group purchases by season/month
        seasonal_products = defaultdict(list)
        
        for order in purchase_history:
            order_date = order.get("date")
            if isinstance(order_date, datetime):
                month = order_date.month
                
                # Categorize by season/festival
                if month == 11:  # November - Thanksgiving
                    for product in order.get("products", []):
                        if any(holiday in str(product.get("categories", [])).lower() 
                              for holiday in ["holiday", "thanksgiving", "turkey"]):
                            seasonal_products["thanksgiving"].append(product["name"])
                            
        # Detect patterns
        for season, products in seasonal_products.items():
            if len(products) >= 3:
                seasonal_data["patterns"].append(season)
                
        # Add upcoming suggestions if patterns detected
        if seasonal_data["patterns"]:
            current_month = datetime.now().month
            if "thanksgiving" in seasonal_data["patterns"] and current_month in [10, 11]:
                seasonal_data["upcoming_suggestions"] = "Consider stocking up on holiday essentials"
                
        return seasonal_data