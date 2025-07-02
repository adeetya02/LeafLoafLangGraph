"""
Pattern Synchronizer Service

Synchronizes extracted patterns from BigQuery to Graphiti/Spanner.
This completes the feedback loop by making learned patterns available
to agents in real-time.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types

from src.services.pattern_extractor import ExtractedPattern, PatternType
from src.memory.memory_registry import MemoryRegistry
from src.memory.memory_interfaces import MemoryBackend

logger = structlog.get_logger()


@dataclass
class SyncResult:
    """Result of a pattern sync operation"""
    total_patterns: int
    synced_count: int
    updated_count: int
    failed_count: int
    duration_ms: float
    errors: List[str]


class PatternSynchronizer:
    """Synchronizes patterns from BigQuery to Graphiti"""
    
    def __init__(self, 
                 spanner_instance_id: str = "leafloaf-graphiti",
                 spanner_database_id: str = "graphiti-memory",
                 project_id: str = "leafloafai"):
        
        self.project_id = project_id
        self.instance_id = spanner_instance_id
        self.database_id = spanner_database_id
        
        # Initialize Spanner client
        self.spanner_client = spanner.Client(project=project_id)
        self.instance = self.spanner_client.instance(spanner_instance_id)
        self.database = self.instance.database(spanner_database_id)
        
        # Batch size for sync operations
        self.batch_size = 500
        
        # Track sync metrics
        self.last_sync_time = {}
        self.sync_counts = {}
    
    async def sync_patterns(self, patterns: List[ExtractedPattern]) -> SyncResult:
        """Sync a list of patterns to Graphiti"""
        
        start_time = datetime.utcnow()
        result = SyncResult(
            total_patterns=len(patterns),
            synced_count=0,
            updated_count=0,
            failed_count=0,
            duration_ms=0,
            errors=[]
        )
        
        if not patterns:
            logger.info("No patterns to sync")
            return result
        
        logger.info(f"Starting sync of {len(patterns)} patterns")
        
        # Group patterns by type for batch processing
        patterns_by_type = self._group_patterns_by_type(patterns)
        
        # Process each pattern type
        for pattern_type, type_patterns in patterns_by_type.items():
            logger.info(f"Syncing {len(type_patterns)} {pattern_type.value} patterns")
            
            # Process in batches
            for i in range(0, len(type_patterns), self.batch_size):
                batch = type_patterns[i:i + self.batch_size]
                
                try:
                    batch_result = await self._sync_batch(batch)
                    result.synced_count += batch_result["created"]
                    result.updated_count += batch_result["updated"]
                    
                except Exception as e:
                    logger.error(f"Failed to sync batch: {e}")
                    result.failed_count += len(batch)
                    result.errors.append(str(e))
        
        # Calculate duration
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log summary
        logger.info(
            "Pattern sync completed",
            total=result.total_patterns,
            synced=result.synced_count,
            updated=result.updated_count,
            failed=result.failed_count,
            duration_ms=result.duration_ms
        )
        
        return result
    
    def _group_patterns_by_type(self, patterns: List[ExtractedPattern]) -> Dict[PatternType, List[ExtractedPattern]]:
        """Group patterns by type for efficient processing"""
        grouped = {}
        
        for pattern in patterns:
            if pattern.pattern_type not in grouped:
                grouped[pattern.pattern_type] = []
            grouped[pattern.pattern_type].append(pattern)
        
        return grouped
    
    async def _sync_batch(self, patterns: List[ExtractedPattern]) -> Dict[str, int]:
        """Sync a batch of patterns to Spanner"""
        
        created_count = 0
        updated_count = 0
        
        def sync_transaction(transaction):
            nonlocal created_count, updated_count
            
            for pattern in patterns:
                # Check if edge exists
                existing = self._get_existing_edge(transaction, pattern)
                
                if existing:
                    # Update existing edge
                    self._update_edge(transaction, existing, pattern)
                    updated_count += 1
                else:
                    # Create new edge
                    self._create_edge(transaction, pattern)
                    created_count += 1
        
        # Execute transaction
        self.database.run_in_transaction(sync_transaction)
        
        return {
            "created": created_count,
            "updated": updated_count
        }
    
    def _get_existing_edge(self, transaction, pattern: ExtractedPattern) -> Optional[Dict]:
        """Check if an edge already exists"""
        
        # Query for existing edge
        results = transaction.execute_sql(
            """
            SELECT edge_id, confidence, properties, last_updated
            FROM graphiti_edges
            WHERE source_node_id = @source_node_id
              AND target_node_id = @target_node_id
              AND edge_type = @edge_type
            LIMIT 1
            """,
            params={
                "source_node_id": pattern.source_node_id,
                "target_node_id": pattern.target_node_id,
                "edge_type": pattern.edge_type
            },
            param_types={
                "source_node_id": param_types.STRING,
                "target_node_id": param_types.STRING,
                "edge_type": param_types.STRING
            }
        )
        
        rows = list(results)
        if rows:
            row = rows[0]
            return {
                "edge_id": row[0],
                "confidence": row[1],
                "properties": row[2],
                "last_updated": row[3]
            }
        
        return None
    
    def _create_edge(self, transaction, pattern: ExtractedPattern):
        """Create a new edge in Graphiti"""
        
        # Ensure nodes exist
        self._ensure_node_exists(transaction, pattern.source_node_id)
        self._ensure_node_exists(transaction, pattern.target_node_id)
        
        # Generate edge ID
        import uuid
        edge_id = str(uuid.uuid4())
        
        # Insert edge
        transaction.insert(
            table="graphiti_edges",
            columns=[
                "edge_id",
                "source_node_id", 
                "target_node_id",
                "edge_type",
                "confidence",
                "properties",
                "created_at",
                "last_updated"
            ],
            values=[
                [
                    edge_id,
                    pattern.source_node_id,
                    pattern.target_node_id,
                    pattern.edge_type,
                    pattern.confidence,
                    spanner.JsonObject(pattern.properties),
                    spanner.COMMIT_TIMESTAMP,
                    spanner.COMMIT_TIMESTAMP
                ]
            ]
        )
        
        logger.debug(f"Created edge: {pattern.edge_type} from {pattern.source_node_id} to {pattern.target_node_id}")
    
    def _update_edge(self, transaction, existing: Dict, pattern: ExtractedPattern):
        """Update an existing edge with new pattern data"""
        
        # Merge properties
        merged_properties = existing.get("properties", {})
        merged_properties.update(pattern.properties)
        
        # Update confidence (weighted average with recency bias)
        days_old = (datetime.utcnow() - existing["last_updated"]).days
        recency_weight = max(0.3, 1.0 - (days_old / 30.0))  # Decay over 30 days
        
        new_confidence = (
            existing["confidence"] * recency_weight + 
            pattern.confidence * (1 - recency_weight)
        )
        
        # Update edge
        transaction.update(
            table="graphiti_edges",
            columns=[
                "edge_id",
                "confidence",
                "properties",
                "last_updated"
            ],
            values=[
                [
                    existing["edge_id"],
                    new_confidence,
                    spanner.JsonObject(merged_properties),
                    spanner.COMMIT_TIMESTAMP
                ]
            ]
        )
        
        logger.debug(f"Updated edge {existing['edge_id']} with new confidence {new_confidence}")
    
    def _ensure_node_exists(self, transaction, node_id: str):
        """Ensure a node exists in Graphiti"""
        
        # Determine node type from ID format
        node_type = self._determine_node_type(node_id)
        
        # Check if node exists
        results = transaction.execute_sql(
            """
            SELECT node_id FROM graphiti_nodes
            WHERE node_id = @node_id
            LIMIT 1
            """,
            params={"node_id": node_id},
            param_types={"node_id": param_types.STRING}
        )
        
        if not list(results):
            # Create node
            transaction.insert(
                table="graphiti_nodes",
                columns=[
                    "node_id",
                    "node_type",
                    "properties",
                    "created_at",
                    "last_updated"
                ],
                values=[
                    [
                        node_id,
                        node_type,
                        spanner.JsonObject({"auto_created": True}),
                        spanner.COMMIT_TIMESTAMP,
                        spanner.COMMIT_TIMESTAMP
                    ]
                ]
            )
            logger.debug(f"Created node: {node_id} of type {node_type}")
    
    def _determine_node_type(self, node_id: str) -> str:
        """Determine node type from ID format"""
        
        if node_id.startswith("brand:"):
            return "brand"
        elif node_id.startswith("category:"):
            return "category"
        elif node_id.startswith("product:"):
            return "product"
        elif node_id.startswith("behavior:"):
            return "behavior"
        elif node_id.startswith("session:"):
            return "session"
        elif "@" in node_id or len(node_id) == 36:  # Email or UUID
            return "user"
        else:
            return "unknown"
    
    async def sync_user_patterns(self, user_id: str, patterns: List[ExtractedPattern]) -> SyncResult:
        """Sync patterns for a specific user"""
        
        # Filter patterns for this user
        user_patterns = [p for p in patterns if p.source_node_id == user_id]
        
        logger.info(f"Syncing {len(user_patterns)} patterns for user {user_id}")
        return await self.sync_patterns(user_patterns)
    
    async def cleanup_stale_patterns(self, older_than_days: int = 90):
        """Remove patterns that haven't been updated recently"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        def cleanup_transaction(transaction):
            # Delete stale edges
            transaction.execute_update(
                """
                DELETE FROM graphiti_edges
                WHERE last_updated < @cutoff_date
                  AND edge_type IN ('ACTIVE_SESSION', 'SESSION_CONTEXT')
                """,
                params={"cutoff_date": cutoff_date},
                param_types={"cutoff_date": param_types.TIMESTAMP}
            )
            
            # Reduce confidence of old patterns
            transaction.execute_update(
                """
                UPDATE graphiti_edges
                SET confidence = confidence * 0.9
                WHERE last_updated < @decay_date
                  AND confidence > 0.3
                """,
                params={"decay_date": datetime.utcnow() - timedelta(days=30)},
                param_types={"decay_date": param_types.TIMESTAMP}
            )
        
        self.database.run_in_transaction(cleanup_transaction)
        logger.info(f"Cleaned up patterns older than {older_than_days} days")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and metrics"""
        
        with self.database.snapshot() as snapshot:
            # Count patterns by type
            results = snapshot.execute_sql(
                """
                SELECT 
                    edge_type,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    MAX(last_updated) as latest_update
                FROM graphiti_edges
                GROUP BY edge_type
                """
            )
            
            pattern_stats = []
            for row in results:
                pattern_stats.append({
                    "edge_type": row[0],
                    "count": row[1],
                    "avg_confidence": row[2],
                    "latest_update": row[3].isoformat() if row[3] else None
                })
        
        return {
            "pattern_statistics": pattern_stats,
            "last_sync_times": self.last_sync_time,
            "total_synced": sum(self.sync_counts.values())
        }


# Global instance
pattern_synchronizer = PatternSynchronizer()