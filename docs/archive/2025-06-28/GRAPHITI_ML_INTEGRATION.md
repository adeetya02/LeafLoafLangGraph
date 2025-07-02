# Graphiti + ML Full Integration for LeafLoaf

## 🚀 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interaction Layer                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Voice (11Labs) → Text → Images → Natural Language          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    LangGraph Orchestration                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Supervisor → Product Search → Order → Response Compiler    │
│      ↓              ↓            ↓            ↓              │
│  ┌────────────────────────────────────────────────┐         │
│  │          Graphiti Knowledge Graph + ML         │         │
│  │                                                │         │
│  │  • Temporal Patterns                           │         │
│  │  • Relationship Learning                       │         │
│  │  • Predictive Models                          │         │
│  │  • Consumption Analytics                      │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
│  Weaviate (Products) | BigQuery (Analytics) | Redis (Cache) │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 Full Integration Implementation

### 1. Enhanced Memory System

```python
from graphiti import Graphiti
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime, timedelta

class LeafLoafKnowledgeGraph:
    def __init__(self):
        self.graphiti = Graphiti(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        self.ml_models = MLModels()
        
    async def initialize(self):
        """Initialize graph with ML-enhanced embeddings"""
        await self.graphiti.build_indices()
        await self.load_ml_models()
    
    async def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        data: Dict
    ):
        """Record every user interaction with rich context"""
        
        # Extract entities and relationships
        entities = await self.extract_entities(data)
        
        # Create episode with ML-enhanced metadata
        episode = await self.graphiti.add_episode(
            name=f"{interaction_type}_{datetime.now().isoformat()}",
            content=self.format_interaction_content(data),
            metadata={
                "user_id": user_id,
                "interaction_type": interaction_type,
                "timestamp": datetime.now().isoformat(),
                "entities": entities,
                "ml_features": await self.extract_ml_features(data),
                "context_embedding": await self.generate_context_embedding(data)
            }
        )
        
        # ML: Learn patterns from this interaction
        await self.ml_models.learn_from_interaction(episode)
        
        return episode
    
    async def get_intelligent_context(
        self,
        user_id: str,
        query: str,
        context_type: str = "shopping"
    ) -> Dict:
        """Get ML-enhanced context for current query"""
        
        # 1. Graphiti search for relevant memories
        memories = await self.graphiti.search(
            query=f"{user_id} {query}",
            num_results=20,
            time_range=timedelta(days=180)
        )
        
        # 2. ML: Analyze patterns
        patterns = await self.ml_models.analyze_patterns(memories)
        
        # 3. ML: Predict needs
        predictions = await self.ml_models.predict_needs(
            user_id=user_id,
            current_query=query,
            historical_context=memories,
            patterns=patterns
        )
        
        # 4. ML: Generate recommendations
        recommendations = await self.ml_models.generate_recommendations(
            user_id=user_id,
            context=memories,
            predictions=predictions
        )
        
        return {
            "memories": memories,
            "patterns": patterns,
            "predictions": predictions,
            "recommendations": recommendations,
            "confidence_scores": self.calculate_confidence(memories, patterns)
        }
```

### 2. ML Models Integration

```python
class MLModels:
    def __init__(self):
        self.consumption_model = ConsumptionPredictor()
        self.pattern_recognizer = PatternRecognizer()
        self.recommendation_engine = RecommendationEngine()
        self.anomaly_detector = AnomalyDetector()
        
    async def analyze_patterns(self, memories: List[Dict]) -> Dict:
        """Detect shopping patterns using ML"""
        
        # Extract time series data
        time_series = self.extract_time_series(memories)
        
        # Detect patterns
        patterns = {
            "seasonal": await self.detect_seasonal_patterns(time_series),
            "weekly": await self.detect_weekly_patterns(time_series),
            "event_based": await self.detect_event_patterns(memories),
            "consumption_rate": await self.calculate_consumption_rates(memories),
            "brand_loyalty": await self.analyze_brand_preferences(memories),
            "price_sensitivity": await self.analyze_price_patterns(memories)
        }
        
        # ML: Cluster similar shopping behaviors
        behavior_clusters = await self.cluster_shopping_behaviors(memories)
        patterns["behavior_clusters"] = behavior_clusters
        
        return patterns
    
    async def predict_needs(
        self,
        user_id: str,
        current_query: str,
        historical_context: List[Dict],
        patterns: Dict
    ) -> Dict:
        """ML-powered need prediction"""
        
        predictions = {
            "immediate_needs": [],
            "upcoming_needs": [],
            "reorder_predictions": [],
            "quantity_predictions": {}
        }
        
        # 1. Consumption-based predictions
        for product in self.get_regular_products(historical_context):
            consumption_rate = patterns["consumption_rate"].get(product["sku"])
            if consumption_rate:
                days_until_reorder = await self.consumption_model.predict_reorder_time(
                    product=product,
                    consumption_rate=consumption_rate,
                    user_patterns=patterns
                )
                
                if days_until_reorder <= 7:
                    predictions["immediate_needs"].append({
                        "product": product,
                        "days_until_needed": days_until_reorder,
                        "confidence": 0.85,
                        "reason": "consumption_pattern"
                    })
        
        # 2. Event-based predictions
        upcoming_events = await self.predict_upcoming_events(patterns)
        for event in upcoming_events:
            event_items = await self.predict_event_items(
                event_type=event["type"],
                historical_events=patterns["event_based"],
                user_preferences=patterns["brand_loyalty"]
            )
            predictions["upcoming_needs"].extend(event_items)
        
        # 3. Quantity predictions using ML
        if current_query:
            extracted_items = await self.extract_items_from_query(current_query)
            for item in extracted_items:
                predicted_qty = await self.predict_quantity(
                    item=item,
                    user_patterns=patterns,
                    context=historical_context
                )
                predictions["quantity_predictions"][item] = predicted_qty
        
        # 4. Anomaly detection
        predictions["anomalies"] = await self.anomaly_detector.detect(
            current_query=current_query,
            patterns=patterns
        )
        
        return predictions
```

### 3. Integration with LangGraph Agents

```python
# Enhanced Supervisor Agent with Graphiti
class EnhancedSupervisor:
    def __init__(self):
        self.knowledge_graph = LeafLoafKnowledgeGraph()
        self.llm = ChatVertexAI(model_name="gemini-1.5-flash")
        
    async def analyze_intent(
        self,
        message: str,
        user_id: str,
        session_id: str
    ):
        # Get intelligent context from Graphiti + ML
        context = await self.knowledge_graph.get_intelligent_context(
            user_id=user_id,
            query=message
        )
        
        # Enhanced prompt with ML insights
        enhanced_prompt = f"""
        Analyze this user query with their shopping context:
        
        Query: {message}
        
        ML-Detected Patterns:
        - Shopping frequency: {context['patterns']['weekly']}
        - Regular items: {context['patterns']['consumption_rate']}
        - Upcoming needs: {context['predictions']['immediate_needs']}
        
        Historical Context:
        {self.format_relevant_memories(context['memories'])}
        
        Determine:
        1. Primary intent
        2. Required agents
        3. Suggested quantities based on patterns
        4. Any anomalies to clarify
        """
        
        response = await self.llm.ainvoke(enhanced_prompt)
        
        # Record this interaction
        await self.knowledge_graph.record_interaction(
            user_id=user_id,
            interaction_type="intent_analysis",
            data={
                "query": message,
                "intent": response.intent,
                "context_used": context
            }
        )
        
        return response
```

### 4. Enhanced Product Search with ML

```python
class MLEnhancedProductSearch:
    def __init__(self):
        self.weaviate = WeaviateClient()
        self.knowledge_graph = LeafLoafKnowledgeGraph()
        
    async def search_products(
        self,
        query: str,
        user_id: str,
        filters: Dict = None
    ):
        # Get ML context
        context = await self.knowledge_graph.get_intelligent_context(
            user_id=user_id,
            query=query
        )
        
        # ML: Personalized query expansion
        expanded_query = await self.expand_query_with_ml(
            query=query,
            user_preferences=context['patterns']['brand_loyalty'],
            past_searches=context['memories']
        )
        
        # Search with ML-enhanced parameters
        alpha = await self.calculate_dynamic_alpha(
            query=expanded_query,
            user_behavior=context['patterns']
        )
        
        results = await self.weaviate.hybrid_search(
            query=expanded_query,
            alpha=alpha,
            filters=self.build_ml_filters(context, filters)
        )
        
        # ML: Re-rank results
        ranked_results = await self.ml_rerank_results(
            results=results,
            user_context=context,
            predictions=context['predictions']
        )
        
        # Record search behavior
        await self.knowledge_graph.record_interaction(
            user_id=user_id,
            interaction_type="product_search",
            data={
                "query": query,
                "expanded_query": expanded_query,
                "results_shown": [r['sku'] for r in ranked_results[:10]],
                "ml_features_used": {
                    "alpha": alpha,
                    "personalization_score": context['confidence_scores']
                }
            }
        )
        
        return ranked_results
    
    async def ml_rerank_results(
        self,
        results: List[Dict],
        user_context: Dict,
        predictions: Dict
    ):
        """ML-powered result re-ranking"""
        
        scored_results = []
        for result in results:
            score = result['search_score']
            
            # Boost score based on ML factors
            if result['sku'] in user_context['patterns']['brand_loyalty']:
                score *= 1.3  # Brand preference boost
            
            if any(p['product']['sku'] == result['sku'] 
                   for p in predictions['immediate_needs']):
                score *= 1.5  # Predicted need boost
            
            # Consumption pattern matching
            if result['sku'] in user_context['patterns']['consumption_rate']:
                rate = user_context['patterns']['consumption_rate'][result['sku']]
                if rate['regularity'] > 0.7:
                    score *= 1.2  # Regular item boost
            
            # Event correlation
            if predictions.get('upcoming_events'):
                event_score = await self.calculate_event_relevance(
                    product=result,
                    events=predictions['upcoming_events']
                )
                score *= (1 + event_score)
            
            scored_results.append({
                **result,
                'ml_score': score,
                'ranking_factors': {
                    'original_score': result['search_score'],
                    'brand_boost': score / result['search_score'],
                    'ml_confidence': user_context['confidence_scores']['overall']
                }
            })
        
        return sorted(scored_results, key=lambda x: x['ml_score'], reverse=True)
```

### 5. Predictive Cart & Order Management

```python
class PredictiveOrderAgent:
    def __init__(self):
        self.knowledge_graph = LeafLoafKnowledgeGraph()
        self.ml_models = MLModels()
        
    async def process_cart_action(
        self,
        action: str,
        items: List[Dict],
        user_id: str
    ):
        # Get ML predictions
        context = await self.knowledge_graph.get_intelligent_context(
            user_id=user_id,
            query=f"cart action {action}"
        )
        
        # ML: Validate quantities
        quantity_suggestions = {}
        for item in items:
            suggested_qty = context['predictions']['quantity_predictions'].get(
                item['sku'],
                await self.ml_models.predict_optimal_quantity(
                    item=item,
                    user_patterns=context['patterns'],
                    consumption_rate=context['patterns']['consumption_rate'].get(item['sku'])
                )
            )
            
            if suggested_qty != item['quantity']:
                quantity_suggestions[item['sku']] = {
                    "requested": item['quantity'],
                    "suggested": suggested_qty,
                    "reason": "Based on your consumption pattern",
                    "confidence": 0.85
                }
        
        # ML: Predict complementary items
        complementary = await self.ml_models.predict_complementary_items(
            cart_items=items,
            user_history=context['memories'],
            patterns=context['patterns']
        )
        
        # ML: Predict next order date
        next_order_prediction = await self.ml_models.predict_next_order(
            current_items=items,
            consumption_patterns=context['patterns']['consumption_rate']
        )
        
        # Process cart with ML insights
        result = await self.process_cart_with_ml_insights(
            action=action,
            items=items,
            quantity_suggestions=quantity_suggestions,
            complementary_items=complementary
        )
        
        # Record order pattern
        await self.knowledge_graph.record_interaction(
            user_id=user_id,
            interaction_type="cart_action",
            data={
                "action": action,
                "items": items,
                "ml_suggestions": {
                    "quantity_adjustments": quantity_suggestions,
                    "complementary_items": complementary,
                    "next_order_date": next_order_prediction
                }
            }
        )
        
        return result
```

### 6. Real-time Learning Pipeline

```python
class RealTimeLearningPipeline:
    def __init__(self):
        self.knowledge_graph = LeafLoafKnowledgeGraph()
        self.bigquery = BigQueryClient()
        
    async def process_event_stream(self):
        """Process events and update ML models in real-time"""
        
        async for event in self.get_event_stream():
            # Update Graphiti
            await self.knowledge_graph.record_interaction(
                user_id=event['user_id'],
                interaction_type=event['type'],
                data=event['data']
            )
            
            # Trigger ML updates
            if event['type'] in ['order_completed', 'item_viewed', 'search_performed']:
                await self.update_ml_models(event)
            
            # Stream to BigQuery for batch ML training
            await self.bigquery.stream_insert(
                table='ml_training_events',
                rows=[{
                    'event_id': event['id'],
                    'user_id': event['user_id'],
                    'event_type': event['type'],
                    'ml_features': await self.extract_ml_features(event),
                    'timestamp': event['timestamp']
                }]
            )
    
    async def update_ml_models(self, event: Dict):
        """Update ML models based on new events"""
        
        if event['type'] == 'order_completed':
            # Update consumption model
            await self.ml_models.consumption_model.update_from_order(
                user_id=event['user_id'],
                items=event['data']['items']
            )
            
            # Update pattern recognition
            await self.ml_models.pattern_recognizer.learn_from_order(
                order_data=event['data'],
                user_context=await self.knowledge_graph.get_user_context(event['user_id'])
            )
```

### 7. Advanced ML Features

```python
class AdvancedMLFeatures:
    
    async def predict_churn_risk(self, user_id: str) -> Dict:
        """Predict if user might stop ordering"""
        context = await self.knowledge_graph.get_intelligent_context(user_id, "")
        
        features = {
            "days_since_last_order": self.calculate_days_since_last_order(context),
            "order_frequency_trend": self.calculate_frequency_trend(context),
            "average_order_value_trend": self.calculate_aov_trend(context),
            "product_diversity": self.calculate_product_diversity(context)
        }
        
        churn_risk = await self.churn_model.predict(features)
        
        return {
            "risk_score": churn_risk,
            "risk_level": "high" if churn_risk > 0.7 else "medium" if churn_risk > 0.4 else "low",
            "intervention_suggestions": self.get_retention_strategies(churn_risk, context)
        }
    
    async def predict_lifetime_value(self, user_id: str) -> Dict:
        """Predict customer lifetime value"""
        context = await self.knowledge_graph.get_intelligent_context(user_id, "")
        
        ltv = await self.ltv_model.predict(
            order_history=context['memories'],
            patterns=context['patterns'],
            churn_risk=await self.predict_churn_risk(user_id)
        )
        
        return {
            "predicted_ltv": ltv,
            "confidence_interval": self.calculate_confidence_interval(ltv),
            "key_drivers": self.identify_ltv_drivers(context)
        }
    
    async def detect_dietary_changes(self, user_id: str) -> Dict:
        """Detect changes in dietary preferences"""
        context = await self.knowledge_graph.get_intelligent_context(user_id, "dietary patterns")
        
        changes = await self.dietary_model.detect_changes(
            historical_purchases=context['memories'],
            time_window=90  # days
        )
        
        return {
            "detected_changes": changes,
            "new_preferences": self.infer_preferences(changes),
            "product_suggestions": await self.suggest_products_for_diet(changes)
        }
```

## 🚀 Benefits of Full Integration

### 1. **Hyper-Personalization**
- Every search is personalized based on complete history
- Quantities are predicted, not just products
- Timing suggestions ("You'll need this by Friday")

### 2. **Predictive Commerce**
- "Your monthly order is ready" - pre-built carts
- Weather-based predictions (BBQ items before weekend)
- Event detection (Diwali shopping patterns)

### 3. **Intelligent Conversations**
```
User: "I need groceries"
System: "Based on your patterns, you're low on rice (usually lasts 2 weeks), 
         dal (running out in 3 days), and it's been a month since you 
         ordered ghee. Should I prepare your regular monthly order?"
```

### 4. **Business Intelligence**
- Churn prevention
- LTV optimization
- Demand forecasting
- Inventory optimization

### 5. **Continuous Learning**
- Every interaction improves the system
- Patterns evolve with user behavior
- Seasonal adjustments automatic

## 🔧 Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. Set up Graphiti + Neo4j
2. Import historical data
3. Basic pattern detection

### Phase 2: ML Integration (Week 3-4)
1. Consumption prediction model
2. Pattern recognition
3. Quantity prediction

### Phase 3: Advanced Features (Week 5-6)
1. Event detection
2. Churn prediction
3. Real-time learning

### Phase 4: Production (Week 7-8)
1. A/B testing framework
2. Performance optimization
3. Monitoring & alerts

## 📊 Expected Results

- **Search Relevance**: +40% improvement
- **Cart Abandonment**: -25% reduction
- **Average Order Value**: +30% increase
- **Customer Retention**: +20% improvement
- **Operational Efficiency**: 50% less customer service queries

This full integration makes LeafLoaf not just a grocery app, but an intelligent shopping assistant that truly understands each customer!