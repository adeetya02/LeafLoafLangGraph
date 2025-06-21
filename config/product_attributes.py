# config/product_attributes.py
"""Product attributes for dynamic alpha calculation"""

PRODUCT_ATTRIBUTES = {
    # High specificity attributes (lower alpha)
    "dietary": {
        "terms": [
            "organic", "non-gmo", "gluten-free", "gluten free", "vegan", 
            "vegetarian", "kosher", "halal", "dairy-free", "dairy free",
            "lactose-free", "lactose free", "nut-free", "nut free"
        ],
        "alpha_impact": -0.2  # Reduces alpha
    },
    
    "nutritional": {
        "terms": [
            "2%", "1%", "0%", "fat free", "fat-free", "sugar free", "sugar-free",
            "low sodium", "low-sodium", "low fat", "low-fat", "high protein",
            "high-protein", "low carb", "low-carb", "keto", "whole grain"
        ],
        "alpha_impact": -0.15
    },
    
    "certifications": {
        "terms": [
            "certified", "usda organic", "fair trade", "non gmo verified",
            "grass fed", "grass-fed", "pasture raised", "pasture-raised"
        ],
        "alpha_impact": -0.2
    },
    
    # Medium specificity (moderate alpha)
    "preparation": {
        "terms": [
            "fresh", "frozen", "dried", "canned", "sliced", "diced",
            "chopped", "shredded", "whole", "ground", "minced"
        ],
        "alpha_impact": -0.1
    },
    
    "size_descriptors": {
        "terms": [
            "large", "small", "medium", "mini", "jumbo", "family size",
            "family-size", "bulk", "individual"
        ],
        "alpha_impact": -0.1
    },
    
    # Exploratory/vague terms (higher alpha)
    "exploratory": {
        "terms": [
            "ideas", "suggestions", "something", "options", "alternatives",
            "recommendations", "what", "which", "help", "need"
        ],
        "alpha_impact": 0.3  # Increases alpha
    },
    
    "meal_context": {
        "terms": [
            "breakfast", "lunch", "dinner", "snack", "meal", "dessert",
            "appetizer", "side dish", "main course"
        ],
        "alpha_impact": 0.2
    },
    
    "purpose_driven": {
        "terms": [
            "for salad", "for pasta", "for baking", "for grilling",
            "for smoothie", "for sandwich", "for cooking"
        ],
        "alpha_impact": 0.1
    }
}

# Base alpha value
DEFAULT_ALPHA = 0.5

# Alpha boundaries
MIN_ALPHA = 0.2  # Most specific searches
MAX_ALPHA = 0.9  # Most exploratory searches