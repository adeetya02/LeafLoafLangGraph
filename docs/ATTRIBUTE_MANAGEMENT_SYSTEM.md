# Attribute Management System - Configuration-Driven Updates

## Overview
This document describes the configuration-driven approach for managing product attributes and categories in LeafLoaf. The system allows for seamless updates, re-categorization, and attribute changes without code modifications or downtime.

## Core Principles
1. **Configuration-Driven**: All attributes defined in config files
2. **Version Control**: Track attribute changes over time
3. **Backward Compatible**: Old attributes remain searchable
4. **Zero Downtime**: Updates happen gradually
5. **ML Continuity**: Models keep working during transitions

## 1. Master Attribute Configuration

### Structure
```yaml
# config/attributes_master.yaml
version: "2.0"
effective_date: "2025-07-01"

# Category hierarchy with versioning
categories:
  version: "v2"
  previous_version: "v1"
  
  hierarchy:
    - id: "fresh"
      name: "Fresh"
      children:
        - id: "vegetables"
          name: "Vegetables"
          children:
            - id: "nightshades"
              name: "Nightshades"
              children: ["peppers", "tomatoes", "eggplant"]
            - id: "leafy_greens"
              name: "Leafy Greens"
              children: ["lettuce", "spinach", "kale"]
              
  # Mapping from old to new
  migrations:
    "Produce/Vegetables/Peppers": "Fresh/Vegetables/Nightshades/Peppers"
    "Produce/Vegetables/Tomatoes": "Fresh/Vegetables/Nightshades/Tomatoes"
    "Dairy/Milk": "Dairy & Eggs/Milk & Cream"

# Product attributes with allowed values
attributes:
  dietary:
    version: "1.2"
    values:
      - id: "organic"
        display: "Organic"
        search_terms: ["organic", "certified organic", "usda organic"]
      - id: "non_gmo"
        display: "Non-GMO"
        search_terms: ["non gmo", "non-gmo", "gmo free"]
      - id: "gluten_free"
        display: "Gluten Free"
        search_terms: ["gluten free", "gluten-free", "no gluten"]
        
  nutritional:
    version: "1.1"
    values:
      - id: "low_fat"
        display: "Low Fat"
        criteria: "fat_per_serving < 3g"
      - id: "sugar_free"
        display: "Sugar Free"
        criteria: "sugar_per_serving < 0.5g"
        
  certifications:
    version: "1.0"
    values:
      - id: "usda_organic"
        display: "USDA Organic"
        validator: "has_certification('USDA-ORG')"
      - id: "fair_trade"
        display: "Fair Trade"
        validator: "has_certification('FAIR-TRADE')"

# ML-specific attributes
ml_attributes:
  usage_context:
    values: ["breakfast", "lunch", "dinner", "snack", "baking", "cooking"]
  
  seasonality:
    values:
      - id: "year_round"
        index: 1.0
      - id: "summer"
        index: {"jun": 1.5, "jul": 1.5, "aug": 1.5, "default": 0.7}
      - id: "winter"
        index: {"dec": 1.5, "jan": 1.5, "feb": 1.5, "default": 0.7}
```

## 2. Attribute Change Management

### Version Control System
```python
# src/config/attribute_manager.py
class AttributeManager:
    def __init__(self):
        self.config = self.load_config("attributes_master.yaml")
        self.version = self.config["version"]
        
    def get_current_attributes(self, attribute_type):
        """Get current valid attributes"""
        return self.config["attributes"][attribute_type]["values"]
    
    def validate_attribute(self, attribute_type, value):
        """Check if attribute value is valid"""
        valid_values = self.get_valid_values(attribute_type)
        return value in valid_values
    
    def migrate_attribute(self, old_value, attribute_type):
        """Map old attribute to new version"""
        migration_map = self.config["attributes"][attribute_type].get("migrations", {})
        return migration_map.get(old_value, old_value)
```

### Product Storage with Versioning
```json
{
  "sku": "BELL-001",
  "name": "Bell Peppers Tri Color",
  
  "attributes": {
    "current": {
      "dietary": ["organic", "non_gmo"],
      "certifications": ["usda_organic"],
      "version": "2.0"
    },
    "history": [
      {
        "dietary": ["organic", "non-gmo"],  // Old format
        "version": "1.0",
        "deprecated": "2025-07-01"
      }
    ]
  },
  
  "categories": {
    "current": "Fresh/Vegetables/Nightshades/Peppers",
    "legacy": ["Produce/Vegetables/Peppers"],
    "version": "v2"
  }
}
```

## 3. Search Compatibility

### Multi-Version Search
```python
def search_products(query, filters):
    # Search across all attribute versions
    attribute_conditions = []
    
    for attr_type, values in filters.items():
        # Get all valid variations of the attribute
        expanded_values = expand_attribute_values(values)
        
        attribute_conditions.append({
            "OR": [
                {"path": ["attributes", "current", attr_type], "operator": "Contains", "valueTextArray": expanded_values},
                {"path": ["attributes", "history", attr_type], "operator": "Contains", "valueTextArray": expanded_values}
            ]
        })
    
    return weaviate_search(query, attribute_conditions)
```

## 4. Configuration Update Process

### Step 1: Update Configuration File
```yaml
# Add new dietary attribute
dietary:
  version: "1.3"  # Increment version
  values:
    # ... existing values ...
    - id: "keto"
      display: "Keto Friendly"
      search_terms: ["keto", "ketogenic", "low carb"]
      added_version: "1.3"
```

### Step 2: Run Migration Script
```python
# scripts/migrate_attributes.py
def migrate_attributes(mode="dry_run"):
    manager = AttributeManager()
    
    if mode == "dry_run":
        # Show what would change
        changes = manager.preview_changes()
        print(f"Would update {len(changes)} products")
        
    elif mode == "shadow":
        # Add new attributes without removing old
        manager.add_new_attributes(keep_old=True)
        
    elif mode == "migrate":
        # Full migration with cleanup
        manager.migrate_all_products()
```

### Step 3: Gradual Rollout
```python
# Rollout stages
ROLLOUT_STAGES = {
    "stage_1": {
        "percentage": 10,
        "duration_days": 3,
        "rollback_threshold": 0.95  # Rollback if accuracy drops below 95%
    },
    "stage_2": {
        "percentage": 50,
        "duration_days": 7
    },
    "stage_3": {
        "percentage": 100,
        "duration_days": None
    }
}
```

## 5. Supplier Data Integration

### Supplier Attribute Mapping
```yaml
# config/supplier_mappings.yaml
baldor:
  attribute_mappings:
    "Organic": "organic"
    "Certified Organic": "usda_organic"
    "Local": "local"
    
  category_mappings:
    "Vegetables/Peppers": "Fresh/Vegetables/Nightshades/Peppers"
    "Fruit/Berries": "Fresh/Fruit/Berries"
    
supplier_2:
  attribute_mappings:
    "ORG": "organic"
    "GF": "gluten_free"
```

### Auto-Enrichment Pipeline
```python
def enrich_supplier_product(supplier, raw_product):
    # Load supplier-specific mappings
    mappings = load_supplier_mappings(supplier)
    
    # Map to standard attributes
    standard_attributes = {}
    for supplier_attr, value in raw_product["attributes"].items():
        standard_attr = mappings["attribute_mappings"].get(supplier_attr)
        if standard_attr and validate_attribute(standard_attr, value):
            standard_attributes[standard_attr] = value
    
    # Map categories
    supplier_category = raw_product["category"]
    standard_category = mappings["category_mappings"].get(supplier_category)
    
    return {
        "attributes": standard_attributes,
        "category": standard_category,
        "supplier_original": raw_product  # Keep original for reference
    }
```

## 6. ML Pipeline Adaptation

### Feature Engineering with Versioning
```python
def extract_ml_features(product):
    features = {}
    
    # Version-agnostic features
    features["has_dietary_restriction"] = bool(product["attributes"]["current"].get("dietary"))
    features["is_certified"] = bool(product["attributes"]["current"].get("certifications"))
    
    # Category level features (works across versions)
    category_parts = product["categories"]["current"].split("/")
    features["category_depth"] = len(category_parts)
    features["top_category"] = category_parts[0] if category_parts else None
    
    # Historical consistency
    features["attribute_stability"] = calculate_attribute_stability(product["attributes"]["history"])
    
    return features
```

## 7. Monitoring & Rollback

### Health Checks
```python
ATTRIBUTE_HEALTH_METRICS = {
    "search_accuracy": {
        "threshold": 0.95,
        "measurement": "percentage of successful searches"
    },
    "attribute_coverage": {
        "threshold": 0.99,
        "measurement": "percentage of products with valid attributes"
    },
    "ml_model_performance": {
        "threshold": 0.90,
        "measurement": "model accuracy with new attributes"
    }
}

def monitor_attribute_health():
    metrics = calculate_health_metrics()
    
    for metric, value in metrics.items():
        if value < ATTRIBUTE_HEALTH_METRICS[metric]["threshold"]:
            trigger_rollback(metric, value)
```

## 8. Benefits of This Approach

1. **No Code Changes**: Update attributes via config files
2. **Gradual Migration**: Test with small percentage first
3. **Full History**: Never lose old categorizations
4. **Supplier Flexibility**: Each supplier keeps their schema
5. **ML Continuity**: Models keep working during transitions
6. **Instant Rollback**: Revert configuration if issues arise

## 9. Implementation Timeline

1. **Week 1**: Set up configuration files and version control
2. **Week 2**: Implement AttributeManager and migration scripts
3. **Week 3**: Test with shadow mode on 10% of products
4. **Week 4**: Full rollout with monitoring

This system ensures that as your business grows and categories evolve, the technical infrastructure adapts seamlessly without disrupting operations or requiring extensive code changes.