"""
Track and display model usage limits and quotas.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ModelUsage:
    """Track usage for a specific model."""
    provider: str
    model: str
    model_type: str = "paid"  # "free", "paid", "enterprise"
    requests_today: int = 0
    tokens_used: int = 0
    requests_limit: Optional[int] = None  # None = unlimited
    tokens_limit: Optional[int] = None    # None = unlimited
    last_reset: datetime = field(default_factory=datetime.now)
    
    def get_requests_percent(self) -> float:
        """Get percentage of requests used."""
        if self.requests_limit is None or self.requests_limit == 0:
            return 0.0
        return min(100.0, (self.requests_today / self.requests_limit) * 100)
    
    def get_tokens_percent(self) -> float:
        """Get percentage of tokens used."""
        if self.tokens_limit is None or self.tokens_limit == 0:
            return 0.0
        return min(100.0, (self.tokens_used / self.tokens_limit) * 100)
    
    def should_warn(self) -> bool:
        """Return True if usage is above 80%."""
        return (self.get_requests_percent() > 80 or 
                self.get_tokens_percent() > 80)
    
    def should_block(self) -> bool:
        """Return True if limit reached."""
        if self.requests_limit is None and self.tokens_limit is None:
            return False  # No limits = never block
        
        req_blocked = self.requests_limit and self.requests_today >= self.requests_limit
        tok_blocked = self.tokens_limit and self.tokens_used >= self.tokens_limit
        
        return req_blocked or tok_blocked
    
    def reset_if_needed(self) -> None:
        """Reset daily counters if 24h have passed."""
        if datetime.now() - self.last_reset > timedelta(hours=24):
            self.requests_today = 0
            self.tokens_used = 0
            self.last_reset = datetime.now()
    
    def get_display_status(self) -> tuple[str, str]:
        """Return (icon, color) for UI display.
        
        For free models: show absolute numbers
        For paid models: show percentage
        """
        if self.model_type == "free":
            # For free models, show token count instead of percentage
            return ("📊", "#5AA5FF")
        else:
            # For paid models, show percentage
            pct = self.get_tokens_percent()
            if pct >= 80:
                return ("🚫", "#FF6B6B")
            elif pct >= 50:
                return ("⚠️", "#FFB84D")
            else:
                return ("✓", "#21C93A")


class UsageTracker:
    """Track usage across all providers and models."""
    
    def __init__(self):
        self.usage: Dict[str, ModelUsage] = {}
    
    def register_model(
        self, 
        provider: str, 
        model: str,
        requests_limit: int = 1000,
        tokens_limit: int = 1000000
    ) -> None:
        """Register a model for tracking."""
        key = f"{provider}:{model}"
        self.usage[key] = ModelUsage(
            provider=provider,
            model=model,
            requests_limit=requests_limit,
            tokens_limit=tokens_limit
        )
    
    def record_request(
        self,
        provider: str,
        model: str,
        tokens_used: int
    ) -> Dict[str, bool]:
        """Record a request and return warning/block status."""
        key = f"{provider}:{model}"
        
        if key not in self.usage:
            self.register_model(provider, model)
        
        usage = self.usage[key]
        usage.reset_if_needed()
        usage.requests_today += 1
        usage.tokens_used += tokens_used
        
        return {
            "warn": usage.should_warn(),
            "block": usage.should_block()
        }
    
    def get_usage_report(self, provider: Optional[str] = None) -> str:
        """Get formatted usage report for all or specific provider."""
        from rich.text import Text
        
        lines = []
        lines.append("[#5AA5FF][bold]📊 Model Usage Report[/bold][/#5AA5FF]\n")
        
        filtered = {
            k: v for k, v in self.usage.items() 
            if provider is None or v.provider.lower() == provider.lower()
        }
        
        if not filtered:
            return "[yellow]No usage data available[/yellow]"
        
        for key, usage in sorted(filtered.items()):
            usage.reset_if_needed()
            
            req_pct = usage.get_requests_percent()
            tok_pct = usage.get_tokens_percent()
            
            # Color based on usage level
            req_color = "#21C93A" if req_pct < 50 else "#FFB84D" if req_pct < 80 else "#FF6B6B"
            tok_color = "#21C93A" if tok_pct < 50 else "#FFB84D" if tok_pct < 80 else "#FF6B6B"
            
            lines.append(f"[#5AA5FF]{usage.provider:12}[/#5AA5FF] | [bold]{usage.model}[/bold]")
            lines.append(
                f"  Requests: {req_color}{req_pct:5.1f}%[/{req_color}] "
                f"({usage.requests_today}/{usage.requests_limit})"
            )
            lines.append(
                f"  Tokens:   {tok_color}{tok_pct:5.1f}%[/{tok_color}] "
                f"({usage.tokens_used:,}/{usage.tokens_limit:,})"
            )
            
            if usage.should_warn():
                lines.append(f"  [#FFB84D]⚠️  High usage detected[/#FFB84D]")
            if usage.should_block():
                lines.append(f"  [#FF6B6B]🚫 LIMIT REACHED[/#FF6B6B]")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_status_bar_text(self) -> str:
        """Get compact status for status footer."""
        total_requests = sum(u.requests_today for u in self.usage.values())
        total_tokens = sum(u.tokens_used for u in self.usage.values())
        
        warnings = sum(1 for u in self.usage.values() if u.should_warn())
        blocked = sum(1 for u in self.usage.values() if u.should_block())
        
        text = f"[#FFB84D]📊 {total_tokens:,} tokens[/#FFB84D]"
        
        if warnings > 0:
            text += f" [#FFB84D]⚠️ {warnings} warning[/#FFB84D]"
        if blocked > 0:
            text += f" [#FF6B6B]🚫 {blocked} at limit[/#FF6B6B]"
        
        return text
