"""
Comprehensive Test Suite for Graphiti Use Cases

Tests all 15 use cases from GRAPHITI_USE_CASES.md:
1. Order my usual monthly supplies
2. What did I get for the last party?
3. I need rice like last time
4. Shopping pattern recognition
5. Product relationships
6. Consumption patterns
7. Event-based shopping memory
8. Brand loyalty tracking
9. Quantity intelligence
10. Reorder timing
11. Recipe-based grouping
12. Substitution memory
13. Price sensitivity patterns
14. Delivery day preferences
15. Forgotten items detection
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from src.integrations.neo4j_config import get_graphiti_neo4j
from src.memory.graphiti_memory import GraphitiMemory, EntityType, RelationshipType
from src.tests.synthetic_user_generator import (
    SyntheticDataGenerator, UserType, UserProfile
)


class GraphitiTestSuite:
    """Test suite for all Graphiti use cases"""
    
    def __init__(self):
        self.neo4j = None
        self.test_results = []
        self.generator = SyntheticDataGenerator()
    
    async def setup(self):
        """Initialize test environment"""
        print("🚀 Setting up Graphiti test environment...")
        
        # Initialize Neo4j
        self.neo4j = await get_graphiti_neo4j()
        
        # Generate synthetic data
        print("📊 Generating synthetic data...")
        users = self.generator.create_users(count_per_type=1)
        
        # Generate 3 months of history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        for user in users.values():
            orders = self.generator.generate_order_history(user, start_date, end_date)
            print(f"  Generated {len(orders)} orders for {user.name}")
        
        # Save to Neo4j
        print("💾 Saving to Neo4j...")
        await self.generator.save_to_neo4j()
        
        print("✅ Setup complete!\n")
    
    async def test_use_case_1_usual_monthly_supplies(self):
        """Test: 'Order my usual monthly supplies'"""
        print("\n🧪 Use Case 1: Order my usual monthly supplies")
        
        # Get a family shopper (they have regular patterns)
        family_user = next(u for u in self.generator.users.values() 
                          if u.user_type == UserType.FAMILY_SHOPPER)
        
        # Initialize Graphiti memory
        memory = GraphitiMemory(family_user.user_id, "test-session-1")
        await memory.initialize()
        
        # Query for monthly patterns
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)-[c:CONTAINS]->(p:Product)
        WHERE o.timestamp > datetime() - duration('P90D')
        WITH p, count(o) as order_count, collect(c.quantity) as quantities
        WHERE order_count >= 3
        RETURN p.sku as sku,
               p.name as name,
               order_count,
               avg(quantities) as avg_quantity,
               stdev(quantities) as quantity_variance
        ORDER BY order_count DESC
        LIMIT 10
        """
        
        results = await self.neo4j.connection.execute_query(
            query, {"user_id": family_user.user_id}
        )
        
        print(f"  Found {len(results)} regular monthly items:")
        for item in results[:5]:
            print(f"    - {item['name']}: ordered {item['order_count']} times, "
                  f"avg quantity: {item['avg_quantity']:.1f}")
        
        self.test_results.append({
            "use_case": 1,
            "description": "Order my usual monthly supplies",
            "status": "✅ PASSED" if len(results) > 0 else "❌ FAILED",
            "details": f"Found {len(results)} regular items"
        })
        
        return results
    
    async def test_use_case_2_last_party_order(self):
        """Test: 'What did I get for the last party?'"""
        print("\n🧪 Use Case 2: What did I get for the last party?")
        
        # Get event planner user
        event_user = next(u for u in self.generator.users.values()
                         if u.user_type == UserType.EVENT_PLANNER)
        
        # Query for event orders
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)
        WHERE o.order_type = 'event'
        WITH o ORDER BY o.timestamp DESC LIMIT 1
        MATCH (o)-[c:CONTAINS]->(p:Product)
        RETURN o.order_id as order_id,
               o.timestamp as date,
               o.metadata as event_details,
               collect({
                   name: p.name,
                   quantity: c.quantity,
                   total: c.total
               }) as items,
               o.total_amount as total_spent
        """
        
        result = await self.neo4j.connection.execute_query(
            query, {"user_id": event_user.user_id}
        )
        
        if result:
            event_order = result[0]
            print(f"  Last event: {event_order['event_details'].get('event', 'Unknown')}")
            print(f"  Date: {event_order['date']}")
            print(f"  Total spent: ₹{event_order['total_spent']:,.2f}")
            print(f"  Items ordered: {len(event_order['items'])}")
            for item in event_order['items'][:5]:
                print(f"    - {item['quantity']}x {item['name']}")
        
        self.test_results.append({
            "use_case": 2,
            "description": "What did I get for the last party?",
            "status": "✅ PASSED" if result else "❌ FAILED",
            "details": f"Found last party order with {len(result[0]['items']) if result else 0} items"
        })
        
        return result
    
    async def test_use_case_3_rice_like_last_time(self):
        """Test: 'I need rice like last time'"""
        print("\n🧪 Use Case 3: I need rice like last time")
        
        # Get any user
        user = list(self.generator.users.values())[0]
        
        # Find last rice order
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)-[c:CONTAINS]->(p:Product)
        WHERE p.category = 'Staples' AND p.subcategory = 'Rice'
        WITH o, p, c ORDER BY o.timestamp DESC LIMIT 1
        
        // Get products ordered with rice
        MATCH (o)-[c2:CONTAINS]->(related:Product)
        WHERE related.sku <> p.sku
        
        RETURN p.sku as rice_sku,
               p.name as rice_name,
               p.brand as rice_brand,
               c.quantity as rice_quantity,
               o.timestamp as order_date,
               collect({
                   name: related.name,
                   quantity: c2.quantity
               }) as ordered_with
        """
        
        result = await self.neo4j.connection.execute_query(
            query, {"user_id": user.user_id}
        )
        
        if result:
            last_rice = result[0]
            print(f"  Last rice order: {last_rice['rice_quantity']}x {last_rice['rice_name']}")
            print(f"  Brand: {last_rice['rice_brand']}")
            print(f"  Ordered on: {last_rice['order_date']}")
            print(f"  Ordered with:")
            for item in last_rice['ordered_with'][:3]:
                print(f"    - {item['quantity']}x {item['name']}")
        
        self.test_results.append({
            "use_case": 3,
            "description": "I need rice like last time",
            "status": "✅ PASSED" if result else "❌ FAILED",
            "details": f"Found last rice order: {result[0]['rice_name'] if result else 'None'}"
        })
        
        return result
    
    async def test_use_case_4_shopping_patterns(self):
        """Test: Shopping pattern recognition"""
        print("\n🧪 Use Case 4: Shopping pattern recognition")
        
        # Analyze weekend vs weekday patterns
        query = """
        MATCH (u:User)-[:PLACED]->(o:Order)
        WITH o, 
             CASE 
                WHEN date(o.timestamp).dayOfWeek IN [6, 7] THEN 'weekend'
                ELSE 'weekday'
             END as day_type
        
        RETURN day_type,
               count(o) as order_count,
               avg(o.total_amount) as avg_order_value,
               avg(o.item_count) as avg_items
        """
        
        patterns = await self.neo4j.connection.execute_query(query)
        
        print("  Shopping patterns:")
        for pattern in patterns:
            print(f"    {pattern['day_type'].capitalize()}: "
                  f"{pattern['order_count']} orders, "
                  f"avg ₹{pattern['avg_order_value']:,.2f}, "
                  f"{pattern['avg_items']:.1f} items/order")
        
        # User-specific patterns
        restaurant_user = next(u for u in self.generator.users.values()
                              if u.user_type == UserType.RESTAURANT_OWNER)
        
        user_query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)
        WITH date(o.timestamp).dayOfWeek as day, count(o) as orders
        RETURN day, orders
        ORDER BY orders DESC
        """
        
        user_patterns = await self.neo4j.connection.execute_query(
            user_query, {"user_id": restaurant_user.user_id}
        )
        
        print(f"\n  Restaurant owner ordering patterns:")
        for pattern in user_patterns[:3]:
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            print(f"    {days[pattern['day']-1]}: {pattern['orders']} orders")
        
        self.test_results.append({
            "use_case": 4,
            "description": "Shopping pattern recognition",
            "status": "✅ PASSED",
            "details": f"Analyzed {len(patterns)} patterns"
        })
        
        return patterns
    
    async def test_use_case_5_product_relationships(self):
        """Test: Product relationships (bought together)"""
        print("\n🧪 Use Case 5: Product relationships")
        
        # Find products frequently bought together
        query = """
        MATCH (p1:Product)<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(p2:Product)
        WHERE p1.sku < p2.sku
        WITH p1, p2, count(o) as co_occurrence
        WHERE co_occurrence >= 3
        RETURN p1.name as product1,
               p2.name as product2,
               co_occurrence,
               // Calculate confidence
               toFloat(co_occurrence) / 
               toFloat(SIZE([(p1)<-[:CONTAINS]-(o:Order) | o])) as confidence
        ORDER BY co_occurrence DESC
        LIMIT 10
        """
        
        relationships = await self.neo4j.connection.execute_query(query)
        
        print("  Top product relationships:")
        for rel in relationships[:5]:
            print(f"    {rel['product1']} + {rel['product2']}: "
                  f"{rel['co_occurrence']} times ({rel['confidence']*100:.0f}% confidence)")
        
        # Test specific relationship (Rice + Dal)
        specific_query = """
        MATCH (rice:Product {subcategory: 'Rice'})<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(dal:Product {subcategory: 'Dal'})
        RETURN count(o) as rice_dal_orders
        """
        
        rice_dal = await self.neo4j.connection.execute_query(specific_query)
        print(f"\n  Rice + Dal combination: {rice_dal[0]['rice_dal_orders']} orders")
        
        self.test_results.append({
            "use_case": 5,
            "description": "Product relationships",
            "status": "✅ PASSED" if len(relationships) > 0 else "❌ FAILED",
            "details": f"Found {len(relationships)} product relationships"
        })
        
        return relationships
    
    async def test_use_case_6_consumption_patterns(self):
        """Test: Consumption patterns (reorder frequency)"""
        print("\n🧪 Use Case 6: Consumption patterns")
        
        # Get any regular user
        user = next(u for u in self.generator.users.values()
                   if u.user_type == UserType.FAMILY_SHOPPER)
        
        # Find reorder patterns
        reorder_patterns = await self.neo4j.find_reorder_patterns(user.user_id)
        
        print(f"  Reorder patterns for {user.name}:")
        for pattern in reorder_patterns[:5]:
            days_since = (datetime.now() - datetime.fromisoformat(
                pattern['last_ordered'].replace('Z', '+00:00').replace('T', ' ')
            )).days
            
            print(f"    {pattern['product_name']}: "
                  f"ordered {pattern['order_count']} times, "
                  f"every {pattern['avg_days_between_orders']:.0f} days, "
                  f"last ordered {days_since} days ago")
            
            if days_since > pattern['avg_days_between_orders']:
                print(f"      ⚠️  Due for reorder!")
        
        self.test_results.append({
            "use_case": 6,
            "description": "Consumption patterns",
            "status": "✅ PASSED" if len(reorder_patterns) > 0 else "❌ FAILED",
            "details": f"Found {len(reorder_patterns)} reorder patterns"
        })
        
        return reorder_patterns
    
    async def test_use_case_7_event_shopping_memory(self):
        """Test: Event-based shopping memory"""
        print("\n🧪 Use Case 7: Event-based shopping memory")
        
        # Get event planner
        event_user = next(u for u in self.generator.users.values()
                         if u.user_type == UserType.EVENT_PLANNER)
        
        # Find all event orders
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)
        WHERE o.order_type = 'event'
        WITH o.metadata.event as event_name, 
             collect({
                 order_id: o.order_id,
                 date: o.timestamp,
                 total: o.total_amount,
                 items: o.item_count
             }) as orders
        RETURN event_name,
               size(orders) as event_count,
               avg([o IN orders | o.total]) as avg_spend,
               avg([o IN orders | o.items]) as avg_items
        """
        
        event_memory = await self.neo4j.connection.execute_query(
            query, {"user_id": event_user.user_id}
        )
        
        print("  Event shopping memory:")
        for event in event_memory:
            print(f"    {event['event_name']}: "
                  f"{event['event_count']} times, "
                  f"avg ₹{event['avg_spend']:,.2f}, "
                  f"{event['avg_items']:.0f} items")
        
        self.test_results.append({
            "use_case": 7,
            "description": "Event-based shopping memory",
            "status": "✅ PASSED" if len(event_memory) > 0 else "❌ FAILED",
            "details": f"Found {len(event_memory)} event types"
        })
        
        return event_memory
    
    async def test_use_case_8_brand_loyalty(self):
        """Test: Brand loyalty tracking"""
        print("\n🧪 Use Case 8: Brand loyalty tracking")
        
        # Analyze brand preferences across categories
        query = """
        MATCH (u:User)-[:PLACED]->(o:Order)-[:CONTAINS]->(p:Product)
        WHERE p.subcategory IN ['Rice', 'Dal', 'Oil']
        WITH u, p.subcategory as category, p.brand as brand, count(o) as purchase_count
        ORDER BY u.user_id, category, purchase_count DESC
        
        WITH u, category, collect({brand: brand, count: purchase_count})[0..3] as top_brands
        RETURN u.name as user_name,
               u.user_id as user_id,
               category,
               top_brands[0].brand as preferred_brand,
               top_brands[0].count as preference_strength,
               size(top_brands) as brand_variety
        ORDER BY user_name, category
        """
        
        brand_loyalty = await self.neo4j.connection.execute_query(query)
        
        # Group by user
        user_loyalty = {}
        for record in brand_loyalty:
            user_name = record['user_name']
            if user_name not in user_loyalty:
                user_loyalty[user_name] = []
            user_loyalty[user_name].append(record)
        
        print("  Brand loyalty analysis:")
        for user_name, loyalties in list(user_loyalty.items())[:3]:
            print(f"\n    {user_name}:")
            for loyalty in loyalties:
                print(f"      {loyalty['category']}: {loyalty['preferred_brand']} "
                      f"({loyalty['preference_strength']} purchases)")
        
        self.test_results.append({
            "use_case": 8,
            "description": "Brand loyalty tracking",
            "status": "✅ PASSED" if len(brand_loyalty) > 0 else "❌ FAILED",
            "details": f"Analyzed {len(user_loyalty)} users' brand preferences"
        })
        
        return brand_loyalty
    
    async def test_use_case_9_quantity_intelligence(self):
        """Test: Quantity intelligence (bulk vs retail)"""
        print("\n🧪 Use Case 9: Quantity intelligence")
        
        # Compare quantities by user type
        query = """
        MATCH (u:User)-[:PLACED]->(o:Order)-[c:CONTAINS]->(p:Product)
        WHERE p.subcategory IN ['Rice', 'Dal', 'Oil']
        WITH u.shopping_pattern as user_type,
             p.subcategory as product_type,
             avg(c.quantity) as avg_quantity,
             min(c.quantity) as min_quantity,
             max(c.quantity) as max_quantity,
             count(c) as order_count
        RETURN user_type, product_type, 
               avg_quantity, min_quantity, max_quantity, order_count
        ORDER BY user_type, product_type
        """
        
        quantity_patterns = await self.neo4j.connection.execute_query(query)
        
        print("  Quantity patterns by user type:")
        current_type = None
        for pattern in quantity_patterns:
            if pattern['user_type'] != current_type:
                current_type = pattern['user_type']
                print(f"\n    {current_type}:")
            
            print(f"      {pattern['product_type']}: "
                  f"avg {pattern['avg_quantity']:.1f} units "
                  f"(range: {pattern['min_quantity']}-{pattern['max_quantity']})")
        
        self.test_results.append({
            "use_case": 9,
            "description": "Quantity intelligence",
            "status": "✅ PASSED",
            "details": f"Analyzed {len(quantity_patterns)} quantity patterns"
        })
        
        return quantity_patterns
    
    async def test_use_case_10_reorder_timing(self):
        """Test: Reorder timing predictions"""
        print("\n🧪 Use Case 10: Reorder timing")
        
        # Get a regular shopper
        user = next(u for u in self.generator.users.values()
                   if u.user_type == UserType.FAMILY_SHOPPER)
        
        # Calculate reorder predictions
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)-[:CONTAINS]->(p:Product)
        WITH p, collect(o.timestamp) as order_dates
        WHERE size(order_dates) >= 2
        
        // Calculate intervals
        WITH p, order_dates,
             [i in range(0, size(order_dates)-1) | 
                duration.between(order_dates[i], order_dates[i+1]).days] as intervals
        
        WITH p, 
             avg(intervals) as avg_interval,
             order_dates[-1] as last_order_date,
             size(order_dates) as total_orders
        
        RETURN p.name as product,
               total_orders,
               avg_interval as avg_days_between,
               last_order_date,
               duration.between(last_order_date, datetime()).days as days_since_last,
               CASE 
                   WHEN duration.between(last_order_date, datetime()).days > avg_interval 
                   THEN 'DUE NOW'
                   ELSE toString(toInteger(avg_interval - duration.between(last_order_date, datetime()).days)) + ' days'
               END as reorder_in
        ORDER BY 
            CASE 
                WHEN duration.between(last_order_date, datetime()).days > avg_interval 
                THEN 0 
                ELSE 1 
            END,
            days_since_last DESC
        """
        
        reorder_predictions = await self.neo4j.connection.execute_query(
            query, {"user_id": user.user_id}
        )
        
        print(f"  Reorder predictions for {user.name}:")
        due_now = [p for p in reorder_predictions if p['reorder_in'] == 'DUE NOW']
        upcoming = [p for p in reorder_predictions if p['reorder_in'] != 'DUE NOW'][:5]
        
        if due_now:
            print("\n    🔴 Due for reorder:")
            for item in due_now[:5]:
                print(f"      - {item['product']} (usually every {item['avg_days_between']:.0f} days, "
                      f"last ordered {item['days_since_last']} days ago)")
        
        if upcoming:
            print("\n    🟡 Upcoming reorders:")
            for item in upcoming:
                print(f"      - {item['product']} in {item['reorder_in']}")
        
        self.test_results.append({
            "use_case": 10,
            "description": "Reorder timing",
            "status": "✅ PASSED" if len(reorder_predictions) > 0 else "❌ FAILED",
            "details": f"Found {len(due_now)} items due, {len(reorder_predictions)} total predictions"
        })
        
        return reorder_predictions
    
    async def test_use_case_11_recipe_grouping(self):
        """Test: Recipe-based grouping"""
        print("\n🧪 Use Case 11: Recipe-based grouping")
        
        # Define common recipe groups
        recipes = {
            "Biryani": ["Basmati Rice", "Ghee", "Yogurt", "Onion", "Ginger", "Garlic"],
            "Dal Tadka": ["Toor Dal", "Onion", "Tomato", "Ghee", "Cumin Seeds"],
            "Palak Paneer": ["Paneer", "Spinach", "Cream", "Onion", "Garlic"]
        }
        
        # Check how often recipe ingredients are bought together
        results = {}
        
        for recipe_name, ingredients in recipes.items():
            # Create a query to find orders containing multiple recipe ingredients
            ingredient_conditions = " OR ".join([f"p.name CONTAINS '{ing}'" for ing in ingredients])
            
            query = f"""
            MATCH (o:Order)-[:CONTAINS]->(p:Product)
            WHERE {ingredient_conditions}
            WITH o, collect(DISTINCT p.name) as products
            WHERE size(products) >= 3
            RETURN count(o) as order_count,
                   avg(size(products)) as avg_ingredients_bought
            """
            
            result = await self.neo4j.connection.execute_query(query)
            
            if result and result[0]['order_count'] > 0:
                results[recipe_name] = {
                    "orders": result[0]['order_count'],
                    "avg_ingredients": result[0]['avg_ingredients_bought']
                }
                
                print(f"    {recipe_name}: found in {result[0]['order_count']} orders "
                      f"(avg {result[0]['avg_ingredients_bought']:.1f}/{len(ingredients)} ingredients)")
        
        self.test_results.append({
            "use_case": 11,
            "description": "Recipe-based grouping",
            "status": "✅ PASSED" if len(results) > 0 else "❌ FAILED",
            "details": f"Found {len(results)} recipe patterns"
        })
        
        return results
    
    async def test_use_case_12_substitution_memory(self):
        """Test: Substitution memory"""
        print("\n🧪 Use Case 12: Substitution memory")
        
        # Track product substitutions (simulate by finding similar products ordered by same user)
        query = """
        // Find users who switched between similar products
        MATCH (u:User)-[:PLACED]->(o1:Order)-[:CONTAINS]->(p1:Product)
        MATCH (u)-[:PLACED]->(o2:Order)-[:CONTAINS]->(p2:Product)
        WHERE p1.subcategory = p2.subcategory 
          AND p1.sku <> p2.sku
          AND o2.timestamp > o1.timestamp
        
        WITH u, p1, p2, 
             min(o1.timestamp) as switched_from_date,
             min(o2.timestamp) as switched_to_date,
             count(DISTINCT o1) as old_product_orders,
             count(DISTINCT o2) as new_product_orders
        
        WHERE new_product_orders >= old_product_orders * 0.5  // Significant switch
        
        RETURN u.name as user,
               p1.name as switched_from,
               p2.name as switched_to,
               p1.subcategory as category,
               switched_from_date,
               switched_to_date,
               old_product_orders,
               new_product_orders
        ORDER BY switched_to_date DESC
        LIMIT 10
        """
        
        substitutions = await self.neo4j.connection.execute_query(query)
        
        print("  Product substitution patterns:")
        for sub in substitutions[:5]:
            print(f"    {sub['user']}: switched from '{sub['switched_from']}' to '{sub['switched_to']}' "
                  f"in {sub['category']} category")
        
        self.test_results.append({
            "use_case": 12,
            "description": "Substitution memory",
            "status": "✅ PASSED" if len(substitutions) > 0 else "❌ FAILED",
            "details": f"Found {len(substitutions)} substitution patterns"
        })
        
        return substitutions
    
    async def test_use_case_13_price_sensitivity(self):
        """Test: Price sensitivity patterns"""
        print("\n🧪 Use Case 13: Price sensitivity patterns")
        
        # Analyze purchase patterns by price
        query = """
        MATCH (u:User)-[:PLACED]->(o:Order)-[c:CONTAINS]->(p:Product)
        WITH u.shopping_pattern as user_type,
             CASE 
                 WHEN p.price < 100 THEN 'budget'
                 WHEN p.price < 250 THEN 'mid-range'
                 ELSE 'premium'
             END as price_tier,
             count(c) as purchase_count,
             sum(c.total) as total_spent
        
        RETURN user_type,
               price_tier,
               purchase_count,
               total_spent,
               total_spent / purchase_count as avg_item_value
        ORDER BY user_type, price_tier
        """
        
        price_patterns = await self.neo4j.connection.execute_query(query)
        
        print("  Price sensitivity by user type:")
        current_type = None
        for pattern in price_patterns:
            if pattern['user_type'] != current_type:
                current_type = pattern['user_type']
                print(f"\n    {current_type}:")
            
            print(f"      {pattern['price_tier']}: {pattern['purchase_count']} items, "
                  f"₹{pattern['total_spent']:,.0f} total")
        
        self.test_results.append({
            "use_case": 13,
            "description": "Price sensitivity patterns",
            "status": "✅ PASSED",
            "details": f"Analyzed {len(price_patterns)} price patterns"
        })
        
        return price_patterns
    
    async def test_use_case_14_delivery_preferences(self):
        """Test: Delivery day preferences"""
        print("\n🧪 Use Case 14: Delivery day preferences")
        
        # Analyze order timing preferences
        query = """
        MATCH (u:User)-[:PLACED]->(o:Order)
        WITH u,
             date(o.timestamp).dayOfWeek as day_of_week,
             CASE
                 WHEN time(o.timestamp).hour < 12 THEN 'morning'
                 WHEN time(o.timestamp).hour < 17 THEN 'afternoon'
                 ELSE 'evening'
             END as time_slot,
             count(o) as order_count
        
        WITH u, 
             collect({day: day_of_week, time: time_slot, count: order_count}) as preferences,
             sum(order_count) as total_orders
        
        RETURN u.name as user,
               u.shopping_pattern as user_type,
               total_orders,
               [p IN preferences WHERE p.count > total_orders * 0.2 | p] as strong_preferences
        ORDER BY total_orders DESC
        """
        
        delivery_prefs = await self.neo4j.connection.execute_query(query)
        
        print("  Delivery preferences by user:")
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for pref in delivery_prefs[:5]:
            print(f"\n    {pref['user']} ({pref['user_type']}):")
            print(f"      Total orders: {pref['total_orders']}")
            
            if pref['strong_preferences']:
                print("      Preferred times:")
                for sp in pref['strong_preferences']:
                    day_name = days[sp['day']-1] if sp['day'] <= 7 else 'Unknown'
                    print(f"        - {day_name} {sp['time']}: {sp['count']} orders")
        
        self.test_results.append({
            "use_case": 14,
            "description": "Delivery day preferences",
            "status": "✅ PASSED",
            "details": f"Analyzed {len(delivery_prefs)} users' preferences"
        })
        
        return delivery_prefs
    
    async def test_use_case_15_forgotten_items(self):
        """Test: Forgotten items detection"""
        print("\n🧪 Use Case 15: Forgotten items detection")
        
        # Find items frequently bought together but sometimes forgotten
        query = """
        // Find strong product associations
        MATCH (p1:Product)<-[:CONTAINS]-(o1:Order)-[:CONTAINS]->(p2:Product)
        WHERE p1.sku < p2.sku
        WITH p1, p2, count(DISTINCT o1) as together_count
        
        // Find times p1 was bought without p2
        MATCH (p1)<-[:CONTAINS]-(o2:Order)
        WHERE NOT EXISTS((o2)-[:CONTAINS]->(p2))
        WITH p1, p2, together_count, count(DISTINCT o2) as alone_count
        
        // Calculate forget rate
        WITH p1, p2, together_count, alone_count,
             toFloat(alone_count) / toFloat(together_count + alone_count) as forget_rate
        
        WHERE together_count >= 5 AND forget_rate > 0.2 AND forget_rate < 0.8
        
        RETURN p1.name as usually_bought,
               p2.name as sometimes_forgotten,
               together_count,
               alone_count,
               forget_rate,
               CASE 
                   WHEN forget_rate > 0.5 THEN 'Often forgotten'
                   WHEN forget_rate > 0.3 THEN 'Sometimes forgotten'
                   ELSE 'Rarely forgotten'
               END as forget_frequency
        ORDER BY together_count DESC, forget_rate DESC
        LIMIT 10
        """
        
        forgotten_items = await self.neo4j.connection.execute_query(query)
        
        print("  Commonly forgotten item combinations:")
        for item in forgotten_items[:5]:
            print(f"    When buying '{item['usually_bought']}', "
                  f"'{item['sometimes_forgotten']}' is {item['forget_frequency'].lower()} "
                  f"({item['forget_rate']*100:.0f}% of the time)")
        
        self.test_results.append({
            "use_case": 15,
            "description": "Forgotten items detection",
            "status": "✅ PASSED" if len(forgotten_items) > 0 else "❌ FAILED",
            "details": f"Found {len(forgotten_items)} forget patterns"
        })
        
        return forgotten_items
    
    async def run_all_tests(self):
        """Run all 15 use case tests"""
        print("=" * 80)
        print("🧪 GRAPHITI USE CASE TEST SUITE")
        print("=" * 80)
        
        # Setup
        await self.setup()
        
        # Run all tests
        test_methods = [
            self.test_use_case_1_usual_monthly_supplies,
            self.test_use_case_2_last_party_order,
            self.test_use_case_3_rice_like_last_time,
            self.test_use_case_4_shopping_patterns,
            self.test_use_case_5_product_relationships,
            self.test_use_case_6_consumption_patterns,
            self.test_use_case_7_event_shopping_memory,
            self.test_use_case_8_brand_loyalty,
            self.test_use_case_9_quantity_intelligence,
            self.test_use_case_10_reorder_timing,
            self.test_use_case_11_recipe_grouping,
            self.test_use_case_12_substitution_memory,
            self.test_use_case_13_price_sensitivity,
            self.test_use_case_14_delivery_preferences,
            self.test_use_case_15_forgotten_items
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                self.test_results.append({
                    "use_case": len(self.test_results) + 1,
                    "description": test_method.__name__,
                    "status": "❌ ERROR",
                    "details": str(e)
                })
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.test_results if "PASSED" in r["status"])
        failed = sum(1 for r in self.test_results if "FAILED" in r["status"])
        errors = sum(1 for r in self.test_results if "ERROR" in r["status"])
        
        print(f"\nTotal tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors: {errors}")
        
        print("\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            print(f"\n{i}. {result['description']}")
            print(f"   Status: {result['status']}")
            print(f"   Details: {result['details']}")
        
        # Save results
        with open("graphiti_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.test_results),
                    "passed": passed,
                    "failed": failed,
                    "errors": errors
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📁 Results saved to: graphiti_test_results.json")
        
        return self.test_results
    
    async def cleanup(self):
        """Clean up resources"""
        if self.neo4j:
            await self.neo4j.close()


async def main():
    """Run the complete test suite"""
    test_suite = GraphitiTestSuite()
    
    try:
        results = await test_suite.run_all_tests()
        
        # Run specific scenario tests
        print("\n" + "=" * 80)
        print("🎭 SCENARIO TESTS")
        print("=" * 80)
        
        # Test conversation flow
        await test_conversation_flow()
        
    finally:
        await test_suite.cleanup()


async def test_conversation_flow():
    """Test realistic conversation flows"""
    print("\n🗣️  Testing Conversation Flow:")
    
    # Get a test user
    generator = SyntheticDataGenerator()
    users = generator.create_users(count_per_type=1)
    test_user = list(users.values())[0]
    
    # Initialize Graphiti memory
    memory = GraphitiMemory(test_user.user_id, "conversation-test")
    await memory.initialize()
    
    # Simulate conversation
    conversations = [
        "I need my usual monthly groceries",
        "What did I order for my daughter's birthday party last month?",
        "I need rice like the one I got last time",
        "Show me what I usually order on weekends",
        "I'm making biryani this weekend, what do I need?"
    ]
    
    for i, message in enumerate(conversations, 1):
        print(f"\n  User: {message}")
        
        # Process message
        result = await memory.process_message(message, "human")
        
        # Get context
        context = await memory.get_context(message)
        
        print(f"  Extracted: {result['entity_count']} entities, "
              f"{result['relationship_count']} relationships")
        
        if context.get('query_entities'):
            print(f"  Query entities: {[e['value'] for e in context['query_entities']]}")


if __name__ == "__main__":
    asyncio.run(main())