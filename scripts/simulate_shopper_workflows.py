#!/usr/bin/env python3
"""
Shopper Workflow Simulation with Latency Tracking
Tests all agent interactions: search, add, update, delete, reorder
"""

import asyncio
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from colorama import init, Fore, Style

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.graph import app
from src.core.state import GraphState
from src.memory.in_memory import InMemoryStore

init(autoreset=True)

@dataclass
class LatencyMetric:
    step: str
    agent: str
    duration_ms: float
    input_size: int
    output_size: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class WorkflowResult:
    workflow_name: str
    total_duration_ms: float
    steps: List[LatencyMetric]
    success: bool
    final_state: Dict[str, Any]
    
class ShopperSimulator:
    def __init__(self):
        self.memory = InMemoryStore()
        self.session_id = f"sim_{int(time.time())}"
        self.metrics: List[WorkflowResult] = []
        
    def print_header(self, workflow: str):
        print(f"\n{'='*70}")
        print(f"{Fore.CYAN}Workflow: {workflow}")
        print(f"Session: {self.session_id}")
        print(f"Started: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print('='*70)
        
    def print_step(self, step: str, agent: str, latency: float):
        print(f"{Fore.YELLOW}[{agent:<15}] {step:<30} {latency:>8.2f}ms")
        
    def print_message(self, role: str, content: str):
        icon = "👤" if role == "user" else "🤖"
        color = Fore.GREEN if role == "user" else Fore.BLUE
        print(f"\n{icon} {color}{role.upper()}:")
        print(f"   {content[:100]}{'...' if len(content) > 100 else ''}")
        
    async def run_workflow(self, workflow_name: str, messages: List[Dict[str, str]]) -> WorkflowResult:
        """Run a complete workflow and track metrics"""
        self.print_header(workflow_name)
        
        workflow_start = time.time()
        steps: List[LatencyMetric] = []
        
        try:
            for msg in messages:
                self.print_message(msg["role"], msg["content"])
                
                if msg["role"] == "user":
                    # Create state
                    state = GraphState(
                        messages=[msg],
                        session_id=self.session_id,
                        memory=self.memory.get_session_context(self.session_id)
                    )
                    
                    # Track each agent step
                    step_start = time.time()
                    input_size = len(json.dumps(state.dict()))
                    
                    # Run through graph
                    async for event in app.astream(state):
                        for node, output in event.items():
                            step_duration = (time.time() - step_start) * 1000
                            output_size = len(json.dumps(output))
                            
                            metric = LatencyMetric(
                                step=f"Process: {msg['content'][:30]}...",
                                agent=node,
                                duration_ms=step_duration,
                                input_size=input_size,
                                output_size=output_size
                            )
                            steps.append(metric)
                            self.print_step(metric.step, metric.agent, metric.duration_ms)
                            
                            # Update for next iteration
                            step_start = time.time()
                            input_size = output_size
                            
                    # Get final response
                    if state.messages and len(state.messages) > 1:
                        self.print_message("assistant", state.messages[-1]["content"])
                        
            workflow_duration = (time.time() - workflow_start) * 1000
            
            result = WorkflowResult(
                workflow_name=workflow_name,
                total_duration_ms=workflow_duration,
                steps=steps,
                success=True,
                final_state=state.dict() if 'state' in locals() else {}
            )
            
            print(f"\n{Fore.GREEN}✅ Workflow completed in {workflow_duration:.2f}ms")
            
        except Exception as e:
            workflow_duration = (time.time() - workflow_start) * 1000
            print(f"\n{Fore.RED}❌ Workflow failed: {str(e)}")
            
            result = WorkflowResult(
                workflow_name=workflow_name,
                total_duration_ms=workflow_duration,
                steps=steps,
                success=False,
                final_state={}
            )
            
        self.metrics.append(result)
        return result
        
    async def simulate_all_workflows(self):
        """Run all shopper workflows"""
        
        workflows = [
            # 1. Simple Product Search
            ("Simple Search", [
                {"role": "user", "content": "I need oat milk"}
            ]),
            
            # 2. Specific Brand Search
            ("Brand Search", [
                {"role": "user", "content": "Do you have Oatly barista edition?"}
            ]),
            
            # 3. Add to Cart Flow
            ("Add to Cart", [
                {"role": "user", "content": "I want to buy bananas"},
                {"role": "user", "content": "Add 2 bunches to my cart"}
            ]),
            
            # 4. Update Quantity
            ("Update Quantity", [
                {"role": "user", "content": "Add apples to my cart"},
                {"role": "user", "content": "Actually, make that 3 bags of apples"}
            ]),
            
            # 5. Remove from Cart
            ("Remove Item", [
                {"role": "user", "content": "Add milk and bread"},
                {"role": "user", "content": "Remove the bread from my cart"}
            ]),
            
            # 6. Reorder Previous Items
            ("Reorder Flow", [
                {"role": "user", "content": "What did I order last time?"},
                {"role": "user", "content": "Add my usual items"}
            ]),
            
            # 7. Complex Multi-Step
            ("Complex Shopping", [
                {"role": "user", "content": "I'm making pasta tonight"},
                {"role": "user", "content": "Add pasta, tomato sauce, and parmesan"},
                {"role": "user", "content": "Also add a salad kit"},
                {"role": "user", "content": "Show me my cart"},
                {"role": "user", "content": "Change pasta quantity to 2 boxes"}
            ]),
            
            # 8. Voice-Like Natural Flow
            ("Natural Conversation", [
                {"role": "user", "content": "Hey, I need to do my weekly shopping"},
                {"role": "user", "content": "Start with fruits - apples, bananas, maybe some berries"},
                {"role": "user", "content": "Oh and I need that oat milk I usually get"},
                {"role": "user", "content": "The barista one"},
                {"role": "user", "content": "That's it for now, what's in my cart?"}
            ])
        ]
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"SHOPPER WORKFLOW SIMULATION")
        print(f"Total Workflows: {len(workflows)}")
        print('='*70)
        
        for workflow_name, messages in workflows:
            await self.run_workflow(workflow_name, messages)
            await asyncio.sleep(1)  # Brief pause between workflows
            
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate latency and performance report"""
        print(f"\n\n{Fore.CYAN}{'='*70}")
        print("PERFORMANCE REPORT")
        print('='*70)
        
        # Overall metrics
        total_workflows = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        avg_duration = sum(m.total_duration_ms for m in self.metrics) / total_workflows
        
        print(f"\n{Fore.YELLOW}Overall Metrics:")
        print(f"  Total Workflows: {total_workflows}")
        print(f"  Successful: {successful}/{total_workflows}")
        print(f"  Average Duration: {avg_duration:.2f}ms")
        
        # Per-workflow breakdown
        print(f"\n{Fore.YELLOW}Workflow Performance:")
        print(f"{'Workflow':<25} {'Duration (ms)':<15} {'Steps':<10} {'Status':<10}")
        print("-" * 60)
        
        for metric in self.metrics:
            status = "✅ Success" if metric.success else "❌ Failed"
            print(f"{metric.workflow_name:<25} {metric.total_duration_ms:<15.2f} {len(metric.steps):<10} {status}")
            
        # Agent performance
        print(f"\n{Fore.YELLOW}Agent Performance:")
        agent_times: Dict[str, List[float]] = {}
        
        for metric in self.metrics:
            for step in metric.steps:
                if step.agent not in agent_times:
                    agent_times[step.agent] = []
                agent_times[step.agent].append(step.duration_ms)
                
        print(f"{'Agent':<20} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Calls':<10}")
        print("-" * 66)
        
        for agent, times in sorted(agent_times.items()):
            avg_time = sum(times) / len(times)
            print(f"{agent:<20} {avg_time:<12.2f} {min(times):<12.2f} {max(times):<12.2f} {len(times):<10}")
            
        # Save detailed report
        self.save_detailed_report()
        
    def save_detailed_report(self):
        """Save detailed metrics to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workflow_metrics_{timestamp}.json"
        
        report_data = {
            "session_id": self.session_id,
            "timestamp": timestamp,
            "workflows": []
        }
        
        for metric in self.metrics:
            workflow_data = {
                "name": metric.workflow_name,
                "total_duration_ms": metric.total_duration_ms,
                "success": metric.success,
                "steps": [
                    {
                        "step": step.step,
                        "agent": step.agent,
                        "duration_ms": step.duration_ms,
                        "input_size": step.input_size,
                        "output_size": step.output_size,
                        "timestamp": step.timestamp.isoformat()
                    }
                    for step in metric.steps
                ]
            }
            report_data["workflows"].append(workflow_data)
            
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\n{Fore.GREEN}Detailed report saved to: {filename}")

async def main():
    simulator = ShopperSimulator()
    
    # First check if services are healthy
    print(f"{Fore.YELLOW}Checking service health first...")
    os.system("python scripts/rfb_health_check.py")
    
    print(f"\n{Fore.YELLOW}Press Enter to start shopper simulation...")
    input()
    
    await simulator.simulate_all_workflows()

if __name__ == "__main__":
    asyncio.run(main())