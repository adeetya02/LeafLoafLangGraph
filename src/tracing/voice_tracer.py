"""
Voice Metadata Tracing System
Comprehensive logging and analysis of voice interactions
"""
import json
import time
import structlog
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio

logger = structlog.get_logger()

class VoiceTracer:
    """Traces voice metadata and processing through the entire system"""
    
    def __init__(self):
        self.trace_file = Path("voice_traces.jsonl")
        self.session_traces = {}
        
    def start_trace(self, session_id: str, user_id: str, query: str, voice_metadata: Dict[str, Any]) -> str:
        """Start a new voice trace"""
        trace_id = f"voice_{session_id}_{int(time.time())}"
        
        trace_data = {
            "trace_id": trace_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "voice_metadata": voice_metadata,
            "processing_steps": [],
            "timings": {},
            "agent_decisions": {},
            "search_parameters": {},
            "final_results": {}
        }
        
        self.session_traces[trace_id] = trace_data
        
        logger.info(
            "🎙️ Voice trace started",
            trace_id=trace_id,
            query=query,
            voice_metadata=voice_metadata
        )
        
        return trace_id
    
    def log_supervisor_analysis(self, trace_id: str, analysis: Dict[str, Any]):
        """Log supervisor's analysis of voice metadata"""
        if trace_id not in self.session_traces:
            return
            
        self.session_traces[trace_id]["processing_steps"].append({
            "step": "supervisor_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": analysis
        })
        
        logger.info(
            "🧠 Supervisor analysis",
            trace_id=trace_id,
            intent=analysis.get("intent"),
            routing=analysis.get("routing_decision"),
            voice_influence=analysis.get("voice_influence", {})
        )
    
    def log_search_parameters(self, trace_id: str, params: Dict[str, Any]):
        """Log how voice metadata influenced search parameters"""
        if trace_id not in self.session_traces:
            return
            
        self.session_traces[trace_id]["search_parameters"] = params
        self.session_traces[trace_id]["processing_steps"].append({
            "step": "search_parameter_calculation",
            "timestamp": datetime.now().isoformat(),
            "data": params
        })
        
        logger.info(
            "🔍 Search parameters calculated",
            trace_id=trace_id,
            alpha=params.get("alpha"),
            limit=params.get("limit"),
            voice_influenced=params.get("voice_influenced", False)
        )
    
    def log_agent_processing(self, trace_id: str, agent_name: str, timing_ms: float, metadata: Dict[str, Any]):
        """Log individual agent processing"""
        if trace_id not in self.session_traces:
            return
            
        self.session_traces[trace_id]["timings"][agent_name] = timing_ms
        self.session_traces[trace_id]["agent_decisions"][agent_name] = metadata
        
        self.session_traces[trace_id]["processing_steps"].append({
            "step": f"{agent_name}_processing",
            "timestamp": datetime.now().isoformat(),
            "timing_ms": timing_ms,
            "data": metadata
        })
        
        logger.info(
            f"🤖 {agent_name} processed",
            trace_id=trace_id,
            timing_ms=timing_ms,
            **metadata
        )
    
    def log_voice_influence_analysis(self, trace_id: str, original_alpha: float, voice_adjusted_alpha: float, reasoning: str):
        """Log how voice metadata influenced search alpha"""
        if trace_id not in self.session_traces:
            return
            
        influence_data = {
            "original_alpha": original_alpha,
            "voice_adjusted_alpha": voice_adjusted_alpha,
            "adjustment": voice_adjusted_alpha - original_alpha,
            "reasoning": reasoning
        }
        
        self.session_traces[trace_id]["processing_steps"].append({
            "step": "voice_influence_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": influence_data
        })
        
        logger.info(
            "🎵 Voice influence on search",
            trace_id=trace_id,
            alpha_change=f"{original_alpha:.2f} → {voice_adjusted_alpha:.2f}",
            reasoning=reasoning
        )
    
    def log_final_results(self, trace_id: str, results: Dict[str, Any], total_time_ms: float):
        """Log final results and complete the trace"""
        if trace_id not in self.session_traces:
            return
            
        self.session_traces[trace_id]["final_results"] = {
            "products_found": len(results.get("products", [])),
            "search_metadata": results.get("metadata", {}),
            "total_time_ms": total_time_ms,
            "completion_timestamp": datetime.now().isoformat()
        }
        
        # Write complete trace to file
        self._write_trace_to_file(trace_id)
        
        logger.info(
            "🎯 Voice trace complete",
            trace_id=trace_id,
            total_time_ms=total_time_ms,
            products_found=len(results.get("products", [])),
            voice_processing_successful=True
        )
    
    def _write_trace_to_file(self, trace_id: str):
        """Write trace data to JSONL file for analysis"""
        if trace_id not in self.session_traces:
            return
            
        try:
            with open(self.trace_file, "a") as f:
                json.dump(self.session_traces[trace_id], f)
                f.write("\n")
        except Exception as e:
            logger.error("Failed to write trace to file", error=str(e))
    
    def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a completed trace"""
        if trace_id not in self.session_traces:
            return None
            
        trace = self.session_traces[trace_id]
        
        return {
            "trace_id": trace_id,
            "query": trace["query"],
            "voice_metadata": trace["voice_metadata"],
            "total_steps": len(trace["processing_steps"]),
            "agent_timings": trace["timings"],
            "search_alpha": trace.get("search_parameters", {}).get("alpha"),
            "products_found": trace.get("final_results", {}).get("products_found", 0),
            "total_time_ms": trace.get("final_results", {}).get("total_time_ms", 0)
        }

# Global tracer instance
voice_tracer = VoiceTracer()

def trace_voice_request(session_id: str, user_id: str, query: str, voice_metadata: Dict[str, Any]) -> str:
    """Convenience function to start voice tracing"""
    return voice_tracer.start_trace(session_id, user_id, query, voice_metadata)

def trace_supervisor_analysis(trace_id: str, analysis: Dict[str, Any]):
    """Convenience function for supervisor analysis tracing"""
    voice_tracer.log_supervisor_analysis(trace_id, analysis)

def trace_search_parameters(trace_id: str, params: Dict[str, Any]):
    """Convenience function for search parameter tracing"""
    voice_tracer.log_search_parameters(trace_id, params)

def trace_agent_processing(trace_id: str, agent_name: str, timing_ms: float, metadata: Dict[str, Any]):
    """Convenience function for agent processing tracing"""
    voice_tracer.log_agent_processing(trace_id, agent_name, timing_ms, metadata)

def trace_voice_influence(trace_id: str, original_alpha: float, voice_adjusted_alpha: float, reasoning: str):
    """Convenience function for voice influence tracing"""
    voice_tracer.log_voice_influence_analysis(trace_id, original_alpha, voice_adjusted_alpha, reasoning)

def trace_final_results(trace_id: str, results: Dict[str, Any], total_time_ms: float):
    """Convenience function for final results tracing"""
    voice_tracer.log_final_results(trace_id, results, total_time_ms)

def get_trace_summary(trace_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get trace summary"""
    return voice_tracer.get_trace_summary(trace_id)