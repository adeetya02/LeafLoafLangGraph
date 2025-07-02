"""
Search Results Tracking System
Monitors search quality over time and tracks performance metrics
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
import structlog

logger = structlog.get_logger()

class SearchResultsTracker:
    """Track and analyze search results over time"""
    
    def __init__(self, data_dir: str = "search_metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.current_session = None
        
    def start_session(self, session_name: str = None):
        """Start a new tracking session"""
        if not session_name:
            session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = {
            "name": session_name,
            "start_time": datetime.now().isoformat(),
            "searches": [],
            "metrics": {}
        }
        
        logger.info(f"Started tracking session: {session_name}")
        
    def track_search(self, 
                    query: str,
                    alpha: float,
                    results: List[Dict],
                    metadata: Dict[str, Any]):
        """Track a single search result"""
        
        if not self.current_session:
            self.start_session()
        
        search_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "alpha": alpha,
            "result_count": len(results),
            "top_results": results[:5],  # Store top 5
            "search_type": metadata.get("search_type", "hybrid"),
            "latency_ms": metadata.get("latency_ms", 0),
            "user_feedback": None,  # To be filled later
            "clicked_position": None,  # Track which result user clicked
            "query_category": self._categorize_query(query)
        }
        
        self.current_session["searches"].append(search_entry)
        
    def _categorize_query(self, query: str) -> str:
        """Categorize query type based on content"""
        query_lower = query.lower()
        
        # Brand specific
        brands = ["oatly", "horizon", "nature's path", "kirkland"]
        if any(brand in query_lower for brand in brands):
            return "brand_specific"
        
        # Category search
        categories = ["vegetables", "fruits", "dairy", "grains", "herbs"]
        if any(cat in query_lower for cat in categories):
            return "category"
        
        # Attribute search
        attributes = ["organic", "gluten free", "vegan", "low fat", "fresh"]
        if any(attr in query_lower for attr in attributes):
            return "attribute"
        
        # Exploratory
        exploratory = ["healthy", "ideas", "suggestions", "options", "best"]
        if any(exp in query_lower for exp in exploratory):
            return "exploratory"
        
        return "general"
    
    def track_user_interaction(self, 
                              search_index: int,
                              clicked_position: Optional[int] = None,
                              feedback: Optional[str] = None):
        """Track user interaction with search results"""
        
        if self.current_session and 0 <= search_index < len(self.current_session["searches"]):
            if clicked_position is not None:
                self.current_session["searches"][search_index]["clicked_position"] = clicked_position
            if feedback:
                self.current_session["searches"][search_index]["user_feedback"] = feedback
    
    def calculate_metrics(self):
        """Calculate session metrics"""
        
        if not self.current_session or not self.current_session["searches"]:
            return
        
        searches = self.current_session["searches"]
        
        # Basic metrics
        metrics = {
            "total_searches": len(searches),
            "avg_results_per_search": sum(s["result_count"] for s in searches) / len(searches),
            "avg_latency_ms": sum(s["latency_ms"] for s in searches) / len(searches),
            "zero_result_rate": sum(1 for s in searches if s["result_count"] == 0) / len(searches),
        }
        
        # Alpha performance
        alpha_performance = {}
        for search in searches:
            alpha = search["alpha"]
            if alpha not in alpha_performance:
                alpha_performance[alpha] = {
                    "count": 0,
                    "total_results": 0,
                    "clicked_searches": 0
                }
            alpha_performance[alpha]["count"] += 1
            alpha_performance[alpha]["total_results"] += search["result_count"]
            if search["clicked_position"] is not None:
                alpha_performance[alpha]["clicked_searches"] += 1
        
        # Calculate CTR by alpha
        for alpha, data in alpha_performance.items():
            data["avg_results"] = data["total_results"] / data["count"] if data["count"] > 0 else 0
            data["ctr"] = data["clicked_searches"] / data["count"] if data["count"] > 0 else 0
        
        metrics["alpha_performance"] = alpha_performance
        
        # Query category breakdown
        category_counts = {}
        for search in searches:
            cat = search["query_category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        metrics["query_categories"] = category_counts
        
        self.current_session["metrics"] = metrics
        
        return metrics
    
    def save_session(self):
        """Save current session to disk"""
        
        if not self.current_session:
            return
        
        # Calculate final metrics
        self.calculate_metrics()
        
        # Add end time
        self.current_session["end_time"] = datetime.now().isoformat()
        
        # Save to file
        filename = self.data_dir / f"{self.current_session['name']}.json"
        with open(filename, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        logger.info(f"Saved session to: {filename}")
        
        # Reset current session
        self.current_session = None
    
    def load_session(self, session_name: str) -> Dict:
        """Load a previous session"""
        filename = self.data_dir / f"{session_name}.json"
        
        if filename.exists():
            with open(filename, 'r') as f:
                return json.load(f)
        else:
            raise FileNotFoundError(f"Session not found: {session_name}")
    
    def generate_report(self, session_names: List[str] = None) -> pd.DataFrame:
        """Generate report across multiple sessions"""
        
        if not session_names:
            # Load all sessions
            session_names = [f.stem for f in self.data_dir.glob("*.json")]
        
        all_data = []
        
        for session_name in session_names:
            try:
                session = self.load_session(session_name)
                
                for search in session["searches"]:
                    all_data.append({
                        "session": session_name,
                        "timestamp": search["timestamp"],
                        "query": search["query"],
                        "alpha": search["alpha"],
                        "result_count": search["result_count"],
                        "latency_ms": search["latency_ms"],
                        "query_category": search["query_category"],
                        "clicked": search["clicked_position"] is not None,
                        "clicked_position": search["clicked_position"],
                        "feedback": search["user_feedback"]
                    })
            except Exception as e:
                logger.error(f"Error loading session {session_name}: {e}")
        
        df = pd.DataFrame(all_data)
        
        # Generate summary statistics
        if not df.empty:
            print("\n=== Search Performance Report ===")
            print(f"\nTotal Searches: {len(df)}")
            print(f"Average Results: {df['result_count'].mean():.1f}")
            print(f"Average Latency: {df['latency_ms'].mean():.0f}ms")
            print(f"Zero Result Rate: {(df['result_count'] == 0).mean():.1%}")
            
            print("\n--- Performance by Alpha ---")
            alpha_stats = df.groupby('alpha').agg({
                'result_count': ['count', 'mean'],
                'clicked': 'mean',
                'latency_ms': 'mean'
            }).round(2)
            print(alpha_stats)
            
            print("\n--- Query Categories ---")
            print(df['query_category'].value_counts())
        
        return df

# Integration with search API
class SearchMetricsMiddleware:
    """Middleware to automatically track search metrics"""
    
    def __init__(self, tracker: SearchResultsTracker):
        self.tracker = tracker
        
    async def track_search_request(self, request_data: Dict, response_data: Dict):
        """Track search request and response"""
        
        query = request_data.get("query", "")
        alpha = request_data.get("alpha", 0.75)
        
        products = response_data.get("products", [])
        metadata = {
            "search_type": response_data.get("metadata", {}).get("search_config", {}).get("search_type", "hybrid"),
            "latency_ms": response_data.get("execution", {}).get("total_time_ms", 0)
        }
        
        self.tracker.track_search(query, alpha, products, metadata)

# Usage example
if __name__ == "__main__":
    # Create tracker
    tracker = SearchResultsTracker()
    
    # Start session
    tracker.start_session("test_session")
    
    # Track some searches
    tracker.track_search(
        query="organic spinach",
        alpha=0.5,
        results=[{"name": "Organic Baby Spinach"}, {"name": "Organic Spinach Bunch"}],
        metadata={"latency_ms": 150, "search_type": "hybrid"}
    )
    
    tracker.track_search(
        query="healthy breakfast",
        alpha=0.85,
        results=[{"name": "Granola"}, {"name": "Greek Yogurt"}],
        metadata={"latency_ms": 200, "search_type": "hybrid"}
    )
    
    # Simulate user interaction
    tracker.track_user_interaction(0, clicked_position=1)
    
    # Save session
    tracker.save_session()
    
    # Generate report
    df = tracker.generate_report()
    print(df)