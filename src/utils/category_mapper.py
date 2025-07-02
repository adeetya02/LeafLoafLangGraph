"""
Category mapping for search queries

Maps common search terms to their expected product categories to improve search precision.
"""

from typing import List, Optional, Set
import re

# Category mappings for common product types
CATEGORY_MAPPINGS = {
    # Dairy products
    "milk": ["Dairy"],
    "cheese": ["Dairy", "Deli"],
    "yogurt": ["Dairy"],
    "butter": ["Dairy"],
    "cream": ["Dairy"],
    
    # Produce
    "apple": ["Produce", "Fruit"],
    "banana": ["Produce", "Fruit"],
    "lettuce": ["Produce", "Vegetables"],
    "tomato": ["Produce", "Vegetables"],
    "carrot": ["Produce", "Vegetables"],
    
    # Meat & Seafood
    "chicken": ["Meat", "Poultry"],
    "beef": ["Meat"],
    "salmon": ["Seafood", "Fish"],
    "shrimp": ["Seafood"],
    
    # Bakery
    "bread": ["Bakery"],
    "bagel": ["Bakery"],
    "muffin": ["Bakery"],
    "cake": ["Bakery"],
    
    # Beverages
    "juice": ["Beverages", "Juice"],
    "soda": ["Beverages"],
    "water": ["Beverages"],
    "coffee": ["Beverages", "Coffee"],
    "tea": ["Beverages", "Tea"],
    
    # Pantry
    "pasta": ["Pantry", "Pasta"],
    "rice": ["Pantry", "Grains"],
    "cereal": ["Pantry", "Breakfast"],
    "oil": ["Pantry", "Cooking"],
    
    # Snacks
    "chips": ["Snacks"],
    "cookies": ["Snacks", "Bakery"],
    "crackers": ["Snacks"],
    "nuts": ["Snacks", "Nuts"],
}

# Categories to exclude for specific queries
CATEGORY_EXCLUSIONS = {
    "milk": ["Produce", "Produce/Other", "Vegetables", "Fruit", "Meat", "Seafood", "Snacks"],
    "bread": ["Dairy", "Produce", "Meat", "Seafood"],
    "apple": ["Dairy", "Meat", "Seafood", "Bakery"],
}

# Broader category groups
CATEGORY_GROUPS = {
    "dairy": ["Dairy", "Dairy Alternatives", "Cheese", "Yogurt"],
    "produce": ["Produce", "Produce/Other", "Vegetables", "Fruit", "Fresh Herbs"],
    "meat": ["Meat", "Poultry", "Beef", "Pork", "Lamb"],
    "seafood": ["Seafood", "Fish", "Shellfish"],
    "bakery": ["Bakery", "Bread", "Pastries", "Cakes"],
}


class CategoryMapper:
    """Maps search queries to relevant product categories"""
    
    @staticmethod
    def get_relevant_categories(query: str) -> List[str]:
        """
        Get relevant categories for a search query.
        Returns a list of categories that should be included in the search.
        """
        query_lower = query.lower().strip()
        
        # Direct mapping
        if query_lower in CATEGORY_MAPPINGS:
            return CATEGORY_MAPPINGS[query_lower]
        
        # Check if query contains any mapped terms
        relevant_categories = set()
        for term, categories in CATEGORY_MAPPINGS.items():
            if term in query_lower:
                relevant_categories.update(categories)
        
        # If no specific mapping found, return None (search all categories)
        return list(relevant_categories) if relevant_categories else None
    
    @staticmethod
    def get_excluded_categories(query: str) -> List[str]:
        """
        Get categories that should be excluded for a search query.
        This helps filter out irrelevant results.
        """
        query_lower = query.lower().strip()
        
        # Direct exclusion mapping
        if query_lower in CATEGORY_EXCLUSIONS:
            return CATEGORY_EXCLUSIONS[query_lower]
        
        # Check if query contains any terms with exclusions
        excluded_categories = set()
        for term, exclusions in CATEGORY_EXCLUSIONS.items():
            if term in query_lower:
                excluded_categories.update(exclusions)
        
        return list(excluded_categories)
    
    @staticmethod
    def filter_products_by_category(products: List[dict], query: str) -> List[dict]:
        """
        Filter products based on category relevance to the query.
        Removes products from irrelevant categories.
        """
        excluded_categories = CategoryMapper.get_excluded_categories(query)
        
        if not excluded_categories:
            return products
        
        # Filter out products from excluded categories
        filtered_products = []
        for product in products:
            product_category = product.get("category", "").lower()
            
            # Check if product category is in excluded list
            excluded = False
            for excluded_cat in excluded_categories:
                if excluded_cat.lower() in product_category:
                    excluded = True
                    break
            
            if not excluded:
                filtered_products.append(product)
        
        return filtered_products
    
    @staticmethod
    def detect_category_intent(query: str) -> Optional[str]:
        """
        Detect if the query has a strong category intent.
        E.g., "organic milk" -> "dairy", "fresh vegetables" -> "produce"
        """
        query_lower = query.lower()
        
        # Check for category group mentions
        for group_name, categories in CATEGORY_GROUPS.items():
            if group_name in query_lower:
                return group_name
        
        # Check for specific product type
        for term, categories in CATEGORY_MAPPINGS.items():
            if term in query_lower and categories:
                # Return the primary category
                return categories[0].lower()
        
        return None