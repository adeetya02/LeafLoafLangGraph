# Graphiti Use Cases for LeafLoaf (Without ML)

## 🎯 Powerful Use Cases to Implement

### 1. "Order my usual monthly supplies"
```python
# User says: "Order my usual monthly supplies"

# Graphiti Query:
context = await graphiti.search(
    "User123 monthly regular purchases",
    time_range=timedelta(days=90)
)

# Returns:
{
    "monthly_items": [
        {"product": "Basmati Rice", "typical_quantity": 2, "frequency": "every 28 days"},
        {"product": "Toor Dal", "typical_quantity": 3, "frequency": "every 30 days"},
        {"product": "Atta Flour", "typical_quantity": 1, "frequency": "every 25 days"}
    ],
    "total_orders": 12,
    "pattern": "consistent_monthly"
}
```

### 2. "What did I get for the last party?"
```python
# User says: "What did I order for my last party?"

# Graphiti traverses:
User → [ORDERED_FOR_EVENT] → "Diwali Party 2024"
     → [EVENT_INCLUDED] → Products[]
     → [SERVED] → "30 people"

# Returns complete party order with quantities
```

### 3. "I need rice like last time"
```python
# User says: "I need rice like last time"

# Graphiti finds:
Last rice order → [WAS_BRAND] → "Laxmi Basmati"
               → [QUANTITY] → "2 x 20 LB"
               → [ORDERED_WITH] → "Ghee", "Saffron"
               → [DATE] → "2 weeks ago"
```

### 4. Shopping Pattern Recognition
```python
# Weekend bulk shopping pattern
Friday/Saturday → [ORDERS_INCREASE] → +40%
                → [COMMON_ITEMS] → "Paneer", "Vegetables"
                → [PURPOSE] → "Weekend cooking"

# Monthly restaurant supplies
Month_Start → [BULK_ORDER] → "Rice", "Dal", "Flour"
           → [QUANTITY] → "Restaurant pack sizes"
```

### 5. Product Relationships
```python
# Graphiti discovers relationships
"Paneer" → [BOUGHT_WITH] → "Spinach" (75% of time)
        → [FOLLOWED_BY] → "Cream" (within 2 days)
        → [RECIPE_CONTEXT] → "Palak Paneer"
```

### 6. Consumption Patterns (No ML Needed)
```python
# Simple time-based patterns
"Milk" → [PURCHASE_FREQUENCY] → "Every 3 days"
      → [LAST_PURCHASED] → "3 days ago"
      → [STATUS] → "Due for reorder"

# Seasonal patterns
"October" → [INCREASED_ORDERS] → "Ghee", "Sugar", "Nuts"
         → [EVENT_CORRELATION] → "Diwali prep"
```

### 7. Event-Based Shopping Memory
```python
# Graphiti remembers event shopping
"Super Bowl 2024" → [ORDERED] → "Chips", "Salsa", "Soda"
                 → [QUANTITY] → "Party size"
                 → [TOTAL_SPENT] → "$125"

# User says: "I'm having another Super Bowl party"
# System suggests the same items with similar quantities
```

### 8. Brand Loyalty Tracking
```python
"Rice" → [BRAND_HISTORY] → {
    "Laxmi": 15 purchases,
    "Vistar": 2 purchases,
    "Other": 1 purchase
}
→ [PREFERENCE] → "Strong Laxmi preference"
```

### 9. Quantity Intelligence
```python
# Graphiti tracks quantity patterns
"Restaurant User" → [TYPICAL_ORDER] → {
    "Rice": "20-40 LB",
    "Dal": "10-15 LB",
    "Oil": "1 gallon"
}

# vs Retail User
"Home User" → [TYPICAL_ORDER] → {
    "Rice": "5-10 LB",
    "Dal": "2-4 LB",
    "Oil": "1 liter"
}
```

### 10. Reorder Timing (Simple Math, No ML)
```python
# Calculate reorder needs
Product → [LAST_ORDERED] → Date
       → [TYPICAL_FREQUENCY] → Days
       → [CALCULATE] → Days until reorder

# "Your rice order is due in 3 days based on your usual pattern"
```

### 11. Recipe-Based Grouping
```python
# User says: "I want to make biryani"
"Biryani" → [REQUIRES] → "Basmati Rice", "Ghee", "Saffron"
         → [PAST_ORDERS] → Show previous biryani shopping
         → [QUANTITIES] → Based on serving size
```

### 12. Substitution Memory
```python
# Remember substitutions
"Oat Milk" → [SUBSTITUTED_FOR] → "Dairy Milk"
          → [WHEN] → "3 months ago"
          → [REASON] → "Dietary change"
          → [CONSISTENT] → "Yes, every order since"
```

### 13. Price Sensitivity Patterns
```python
# Track price-based decisions
Product → [PURCHASED_WHEN] → "On sale"
       → [SKIPPED_WHEN] → "Regular price"
       → [PATTERN] -> "Price sensitive"
```

### 14. Delivery Day Preferences
```python
User → [PREFERS_DELIVERY] → "Tuesday"
    → [TIME_SLOT] → "Morning"
    → [FREQUENCY] → "90% of orders"
```

### 15. Forgotten Items Detection
```python
# Common cart patterns
"Rice" + "Dal" → [USUALLY_WITH] → "Ghee"
              → [FORGOTTEN_RATE] → "30%"

# Prompt: "You usually also get ghee with rice and dal"
```

## 🔧 Implementation Examples

### Basic Graphiti Setup
```python
class LeafLoafMemory:
    def __init__(self):
        self.graphiti = Graphiti()
    
    async def get_usual_order(self, user_id: str):
        """Get user's regular monthly items"""
        
        # Query for recurring patterns
        results = await self.graphiti.search(
            query=f"{user_id} regular monthly purchases",
            time_range=timedelta(days=90)
        )
        
        # Extract patterns (no ML needed)
        monthly_items = []
        for memory in results:
            if memory.frequency > 2:  # Ordered 3+ times
                monthly_items.append({
                    "product": memory.product,
                    "typical_quantity": memory.avg_quantity,
                    "last_ordered": memory.last_date,
                    "due_in_days": calculate_days_until_due(memory)
                })
        
        return monthly_items
    
    async def get_event_orders(self, user_id: str, event_type: str):
        """Get previous orders for similar events"""
        
        results = await self.graphiti.search(
            query=f"{user_id} {event_type} shopping",
            relationship_type="ORDERED_FOR_EVENT"
        )
        
        return {
            "previous_events": results,
            "common_items": extract_common_items(results),
            "typical_spend": calculate_average_spend(results)
        }
```

### Voice Conversation Using Graphiti
```python
# User: "I need my usual stuff"
usual_items = await memory.get_usual_order(user_id)

response = f"Your usual monthly order includes {len(usual_items)} items: "
for item in usual_items[:3]:  # Top 3
    response += f"{item['typical_quantity']} {item['product']}, "

response += "Should I add all of these to your cart?"
```

## 💡 Why These Use Cases Are Powerful

1. **No ML Required** - All based on graph traversal and simple calculations
2. **Immediate Value** - Users see their patterns reflected instantly
3. **Natural Conversations** - "my usual", "like last time", "for my party"
4. **Builds Trust** - System remembers and understands context
5. **Reduces Friction** - Fewer clicks, faster ordering
6. **Competitive Advantage** - Most grocery apps don't have this memory

## 🚀 Quick Wins to Implement First

1. **"My usual order"** - Highest value, easiest to implement
2. **"Like last time"** - Simple last order lookup
3. **Event memory** - "What did I get for my last party?"
4. **Reorder reminders** - "You usually order rice every 2 weeks"
5. **Forgotten items** - "You usually get ghee with this"

These use cases will make LeafLoaf feel intelligent WITHOUT needing ML!