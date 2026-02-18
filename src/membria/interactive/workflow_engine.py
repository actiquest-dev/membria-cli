"""Double Diamond Workflow Engine for Membria Council."""

import asyncio
from typing import List, Dict, Any, Optional

class DoubleDiamondEngine:
    """Manages the Discover -> Define -> Develop -> Deliver state machine."""
    
    def __init__(self, executor):
        self.executor = executor
        self.states = ["DISCOVER", "DEFINE", "DEVELOP", "DELIVER"]
        self.current_state = "DISCOVER"

    async def run(self, task: str) -> str:
        """Execute the full Double Diamond process."""
        results = {}
        
        # 1. DISCOVER: Divergent thinking (Exploration)
        self.executor._log_event("L1", "💎 Double Diamond [Phase 1/4]: DISCOVER (Exploration)")
        explore_prompt = f"Act as a Strategic Analyst. Explore all possible requirements, edge cases, and stakeholders for: {task}"
        results["discover"] = await self.executor.run_task(explore_prompt, role="analyst")
        
        # 2. DEFINE: Convergent thinking (Selection)
        self.executor._log_event("L1", "💎 Double Diamond [Phase 2/4]: DEFINE (Problem Statement)")
        define_prompt = f"Act as an Architect. Based on these findings, define the core problem and high-level requirements:\n{results['discover']}"
        results["define"] = await self.executor.run_task(define_prompt, role="architect")
        
        # 3. DEVELOP: Divergent thinking (Prototyping)
        self.executor._log_event("L1", "💎 Double Diamond [Phase 3/4]: DEVELOP (Implementation Plan)")
        develop_prompt = f"Act as a Senior Engineer. Develop a detailed implementation plan for this definition:\n{results['define']}"
        results["develop"] = await self.executor.run_task(develop_prompt, role="implementer")
        
        # 4. DELIVER: Convergent thinking (Finalization)
        self.executor._log_event("L1", "💎 Double Diamond [Phase 4/4]: DELIVER (Code/Artifacts)")
        deliver_prompt = f"Act as an SRE and Reviewer. Synthesize the final solution, ensuring quality and reliability:\nPLAN: {results['develop']}"
        results["deliver"] = await self.executor.run_task(deliver_prompt, role="reviewer")
        
        return f"""### 💎 DOUBLE DIAMOND FINAL DELIVERY
{results['deliver']}

---
### 🔍 PROCESS TRACE
- **Discover**: {results['discover'][:150]}...
- **Define**: {results['define'][:150]}...
- **Develop**: {results['develop'][:150]}...
"""
