# Response Compiler Implementation Examples

## 🎯 When to Use vs Skip Response Compiler

Based on our analysis, the Response Compiler adds minimal overhead (0.25ms) but should still be skipped when unnecessary.

---

## ✅ Examples: When to USE Response Compiler

### 1. Natural Language Query with Multiple Intents
```json
// User Input
{
  "message": "I need rice and dal for 20 people, add to cart"
}

// Supervisor Output
{
  "intent": "search_and_add_to_cart",
  "required_agents": ["search", "cart"],
  "search_query": "rice dal",
  "quantity_context": "for 20 people"
}

// Response Compiler Input
{
  "intent": {
    "type": "search_and_add_to_cart",
    "confidence": 0.92
  },
  "agentOutputs": {
    "search": {
      "products": [...15 products...],
      "query": "rice dal"
    },
    "cart": null  // Not executed yet
  },
  "session": {
    "userType": "restaurant"
  }
}

// Response Compiler Output
{
  "message": "I found 8 rice and 7 dal varieties. For 20 people, I recommend 2 bags of Laxmi Basmati Rice (10lb each) and 1 bag of Toor Dal (4lb). Would you like me to add these to your cart?",
  "products": [...filtered/ranked products...],
  "suggestions": [
    {
      "type": "add_to_cart",
      "text": "Add recommended items",
      "action": {
        "items": [
          {"sku": "LX_RICE_001", "quantity": 2},
          {"sku": "LX_DAL_001", "quantity": 1}
        ]
      }
    }
  ]
}
```

### 2. Complex Order with Issues
```json
// User Input
{
  "message": "Complete my order for tomorrow morning"
}

// Multiple Agent Outputs Need Synthesis
{
  "order_validation": {
    "issues": [
      {"type": "stock", "product": "LX_RICE_001", "available": 5, "requested": 10},
      {"type": "delivery", "date": "2025-06-27", "reason": "No slots"}
    ]
  },
  "alternatives": {
    "products": [...],
    "delivery_dates": ["2025-06-28", "2025-06-29"]
  }
}

// Response Compiler Creates Natural Language
{
  "message": "I notice two issues: We only have 5 bags of rice (you need 10) and tomorrow's delivery is full. Would you like 5 bags delivered June 28th instead?",
  "suggestions": [...]
}
```

### 3. Conversational Context
```json
// User has been shopping for Indian groceries
{
  "message": "What else do I need?"
}

// Response Compiler uses session history
{
  "message": "Based on your Indian groceries, you might also need ghee, paneer, and spices for a complete meal. Here are some recommendations:",
  "recommendations": {
    "reason": "Complete your Indian cooking essentials",
    "products": [...]
  }
}
```

---

## ❌ Examples: When to SKIP Response Compiler

### 1. Simple Product Search
```json
// User Input
{
  "query": "rice",
  "filters": {"suppliers": ["Laxmi"]}
}

// Direct Weaviate Response (Skip Everything)
{
  "products": [...],
  "facets": {...},
  "pagination": {...}
}
// No natural language needed, no synthesis required
```

### 2. Cart Operations
```json
// User Input
{
  "action": "add",
  "productId": "uuid-123",
  "quantity": 2
}

// Direct Cart Service Response
{
  "cart": {
    "items": [...],
    "subtotal": 70.00
  },
  "added": [{"sku": "LX_RICE_001", "quantity": 2}]
}
// Simple CRUD, no compilation needed
```

### 3. Price Calculation
```json
// User Input
{
  "items": [{"productId": "uuid-123", "quantity": 10}],
  "userContext": {"tier": "gold"}
}

// Direct Pricing Service Response
{
  "pricing": {
    "items": [...],
    "summary": {"total": 271.19}
  }
}
// Pure calculation, no natural language
```

---

## 🏗️ Response Compiler Implementation

```python
# src/agents/response_compiler_enhanced.py
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

class EnhancedResponseCompiler:
    def __init__(self):
        self.templates = self._load_templates()
        self.llm = None  # Only initialize if needed
        
    async def compile(
        self,
        intent: Dict,
        agent_outputs: Dict,
        session: Dict,
        options: Dict
    ) -> Dict:
        """
        Compile agent outputs into user-facing response
        Only use LLM for complex natural language generation
        """
        start_time = datetime.now()
        
        # Determine compilation strategy
        strategy = self._determine_strategy(intent, agent_outputs, options)
        
        if strategy == "template":
            # Use pre-built templates (fast)
            result = await self._compile_with_templates(
                intent, agent_outputs, session
            )
        elif strategy == "simple_merge":
            # Just merge data (fastest)
            result = self._simple_merge(agent_outputs)
        else:
            # Complex case - use LLM
            result = await self._compile_with_llm(
                intent, agent_outputs, session, options
            )
        
        # Add compilation metadata
        result["compilation"] = {
            "agentsUsed": list(agent_outputs.keys()),
            "dataSourcesMerged": len(agent_outputs),
            "confidenceScore": intent.get("confidence", 1.0),
            "strategy": strategy,
            "timeMs": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        return result
    
    def _determine_strategy(
        self, 
        intent: Dict, 
        agent_outputs: Dict,
        options: Dict
    ) -> str:
        """Determine compilation strategy"""
        
        # No natural language needed
        if not options.get("generateNaturalLanguage"):
            return "simple_merge"
        
        # Single agent, simple intent
        if len(agent_outputs) == 1 and intent["type"] in self.templates:
            return "template"
        
        # Complex multi-agent or unknown intent
        return "llm"
    
    async def _compile_with_templates(
        self,
        intent: Dict,
        agent_outputs: Dict,
        session: Dict
    ) -> Dict:
        """Fast template-based compilation"""
        
        template_key = f"{intent['type']}_{session.get('userType', 'retail')}"
        template = self.templates.get(
            template_key,
            self.templates.get(intent['type'])
        )
        
        if not template:
            # Fallback to LLM
            return await self._compile_with_llm(
                intent, agent_outputs, session, {"generateNaturalLanguage": True}
            )
        
        # Extract values for template
        values = self._extract_template_values(intent, agent_outputs, session)
        
        # Generate message
        message = template.format(**values)
        
        # Build response
        response = {
            "message": message
        }
        
        # Add structured data
        if search_results := agent_outputs.get("search"):
            response["products"] = self._filter_products(
                search_results.get("products", []),
                intent,
                session
            )
        
        if cart_result := agent_outputs.get("cart"):
            response["cart"] = cart_result.get("cart")
        
        # Generate suggestions
        response["suggestions"] = self._generate_suggestions(
            intent, agent_outputs, session
        )
        
        return response
    
    def _simple_merge(self, agent_outputs: Dict) -> Dict:
        """Simple data merge without natural language"""
        
        result = {}
        
        # Merge all agent outputs
        for agent, output in agent_outputs.items():
            if agent == "search" and "products" in output:
                result["products"] = output["products"]
            elif agent == "cart" and "cart" in output:
                result["cart"] = output["cart"]
            elif agent == "recommendations":
                result["recommendations"] = output
            elif agent == "order":
                result["order"] = output
        
        return result
    
    async def _compile_with_llm(
        self,
        intent: Dict,
        agent_outputs: Dict,
        session: Dict,
        options: Dict
    ) -> Dict:
        """Complex compilation using LLM"""
        
        # Initialize LLM if needed
        if not self.llm:
            self.llm = await self._initialize_llm()
        
        # Build prompt
        prompt = self._build_llm_prompt(intent, agent_outputs, session)
        
        # Generate response
        llm_response = await self.llm.generate(prompt)
        
        # Parse and structure response
        return self._parse_llm_response(llm_response, agent_outputs)
    
    def _filter_products(
        self,
        products: List[Dict],
        intent: Dict,
        session: Dict
    ) -> List[Dict]:
        """Filter and rank products based on context"""
        
        # Apply user preferences
        if preferences := session.get("preferences"):
            if dietary := preferences.get("dietary"):
                products = [
                    p for p in products
                    if all(p.get("attributes", {}).get(d) for d in dietary)
                ]
        
        # Sort by relevance and user type
        if session.get("userType") == "restaurant":
            # Prioritize bulk sizes
            products.sort(
                key=lambda p: (
                    -p.get("searchScore", 0),
                    -p.get("packaging", {}).get("unitsPerCase", 1)
                )
            )
        else:
            # Prioritize smaller sizes
            products.sort(
                key=lambda p: (
                    -p.get("searchScore", 0),
                    p.get("packaging", {}).get("unitsPerCase", 999)
                )
            )
        
        # Limit results
        return products[:20]
    
    def _generate_suggestions(
        self,
        intent: Dict,
        agent_outputs: Dict,
        session: Dict
    ) -> List[Dict]:
        """Generate actionable suggestions"""
        
        suggestions = []
        
        # Cart suggestions
        if search_results := agent_outputs.get("search"):
            if products := search_results.get("products"):
                # Suggest adding top products
                if intent.get("type") == "product_search":
                    top_products = products[:3]
                    suggestions.append({
                        "type": "add_to_cart",
                        "text": "Add top results to cart",
                        "action": {
                            "items": [
                                {"sku": p["sku"], "quantity": 1}
                                for p in top_products
                            ]
                        },
                        "priority": 1
                    })
                
                # Suggest filtering
                categories = list(set(p["category"] for p in products))
                if len(categories) > 1:
                    suggestions.append({
                        "type": "search",
                        "text": f"Show only {categories[0]}",
                        "action": {
                            "query": intent.get("search_query"),
                            "filters": {"categories": [categories[0]]}
                        },
                        "priority": 2
                    })
        
        # Order suggestions
        if cart := agent_outputs.get("cart", {}).get("cart"):
            if cart.get("itemCount", 0) > 0:
                suggestions.append({
                    "type": "checkout",
                    "text": "Proceed to checkout",
                    "action": {"cartId": cart["id"]},
                    "priority": 1
                })
        
        return sorted(suggestions, key=lambda s: s["priority"])
    
    def _load_templates(self) -> Dict[str, str]:
        """Load message templates"""
        return {
            "product_search": "I found {count} products matching '{query}'.",
            "product_search_restaurant": "I found {count} products for your restaurant. I've prioritized bulk sizes.",
            "search_and_add": "I found {count} {product_type}. Would you like me to add the recommended items to your cart?",
            "cart_add_success": "I've added {items} to your cart. Your total is now ${total}.",
            "order_issue": "There's an issue with your order: {issue}. {suggestion}",
            "empty_search": "I couldn't find any products matching '{query}'. Try searching for {alternative}.",
        }
    
    def _extract_template_values(
        self,
        intent: Dict,
        agent_outputs: Dict,
        session: Dict
    ) -> Dict[str, Any]:
        """Extract values for template substitution"""
        
        values = {
            "query": intent.get("search_query", ""),
            "user_type": session.get("userType", "customer")
        }
        
        if search_results := agent_outputs.get("search"):
            products = search_results.get("products", [])
            values["count"] = len(products)
            
            # Determine product type
            if products:
                categories = [p.get("category") for p in products[:5]]
                most_common = max(set(categories), key=categories.count)
                values["product_type"] = most_common.lower()
        
        if cart := agent_outputs.get("cart", {}).get("cart"):
            values["total"] = cart.get("subtotal", 0)
            values["items"] = cart.get("itemCount", 0)
        
        return values

# Usage in main API
async def should_use_response_compiler(
    intent: Dict,
    agent_outputs: Dict,
    endpoint: str
) -> bool:
    """Determine if response compiler is needed"""
    
    # Never use for these endpoints
    if endpoint in ["/products/search", "/cart", "/pricing"]:
        return False
    
    # Always use for chat endpoint
    if endpoint == "/chat":
        return True
    
    # Use for complex multi-agent responses
    if len(agent_outputs) > 1:
        return True
    
    # Use if natural language is expected
    if intent.get("requires_natural_language"):
        return True
    
    return False
```

---

## 📊 Performance Impact Analysis

### Current State (Everything through Response Compiler):
```
User → API → Supervisor (150ms) → Agents (500ms) → Response Compiler (0.25ms) → User
Total: ~650ms
```

### Optimized State:
```
Simple Search: User → API → Weaviate (150ms) → User
Cart Op: User → API → Cart Service (50ms) → User  
Complex Chat: User → API → Supervisor → Agents → Response Compiler → User (500ms)
```

### Key Insights:
1. **Response Compiler overhead is minimal** (0.25ms)
2. **Main bottleneck is Supervisor + Agent execution** (650ms)
3. **Skipping Supervisor saves 150ms**
4. **Direct operations save 600ms+**

---

## 🎯 Implementation Priority

1. **Create direct endpoints** (biggest impact)
2. **Add caching layer** (reduce Weaviate calls)
3. **Optimize Response Compiler** (use templates)
4. **Parallelize agent execution** (when multiple needed)