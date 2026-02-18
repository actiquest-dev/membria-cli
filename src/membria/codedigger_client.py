"""CodeDigger API client for antipattern detection and evidence."""

import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Antipattern severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Pattern:
    """Antipattern definition from CodeDigger."""
    pattern_id: str
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    category: str  # e.g., "security", "performance", "maintainability"
    removal_rate: float  # 0.0 to 1.0, e.g., 0.89 means 89% of repos removed it
    repos_affected: int  # Number of repos with this pattern
    keywords: List[str]  # Search keywords: ["custom jwt", "jwt auth", "authentication"]
    regex_pattern: Optional[str]  # Regex for Stage 1 detection
    examples: List[str]  # Code examples showing the antipattern


@dataclass
class Occurrence:
    """Single occurrence of an antipattern in a repo."""
    occurrence_id: str
    pattern_id: str
    repo_name: str  # e.g., "user-service"
    file_path: str
    match_text: str  # The actual code that matched
    confidence: float  # 0.0 to 1.0
    last_seen: str  # ISO datetime


@dataclass
class CodeDiggerStats:
    """Statistics from CodeDigger."""
    total_repos_analyzed: int
    total_antipatterns_detected: int
    patterns_count: int
    last_update: str  # ISO datetime


class CodeDiggerClient:
    """Client for CodeDigger API.

    Provides access to:
    - Antipattern patterns (GET /api/patterns)
    - Evidence from GitHub (GET /api/occurrences)
    - Statistics (GET /api/stats)
    - Health check (GET /health)
    """

    def __init__(
        self,
        base_url: str = "https://codedigger.membria.ai:4000",
        cache_ttl_hours: int = 24,
        timeout: int = 10,
    ):
        """Initialize CodeDigger client.

        Args:
            base_url: CodeDigger API endpoint
            cache_ttl_hours: Cache TTL for patterns (24 hours default)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        # In-memory cache
        self.patterns_cache: Optional[List[Pattern]] = None
        self.patterns_cache_time: Optional[datetime] = None
        self.stats_cache: Optional[CodeDiggerStats] = None
        self.stats_cache_time: Optional[datetime] = None

    async def health_check(self) -> bool:
        """Check if CodeDigger is alive.

        Returns:
            True if CodeDigger is accessible, False otherwise
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        logger.info("✓ CodeDigger health check passed")
                        return True
                    else:
                        logger.warning(f"CodeDigger health check failed: {resp.status}")
                        return False
        except Exception as e:
            logger.warning(f"CodeDigger unreachable: {str(e)}")
            return False

    async def get_patterns(self, force_refresh: bool = False) -> Optional[List[Pattern]]:
        """Fetch all 25+ antipattern patterns from CodeDigger.

        Caches results for 24 hours by default.

        Args:
            force_refresh: Force refresh even if cached

        Returns:
            List of Pattern objects, or None if request fails
        """
        # Check cache
        if not force_refresh and self.patterns_cache is not None:
            if self.patterns_cache_time and datetime.now() - self.patterns_cache_time < self.cache_ttl:
                logger.debug(f"Using cached patterns ({len(self.patterns_cache)} patterns)")
                return self.patterns_cache

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/patterns") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        patterns = [Pattern(**p) for p in data.get("patterns", [])]
                        self.patterns_cache = patterns
                        self.patterns_cache_time = datetime.now()
                        logger.info(f"✓ Fetched {len(patterns)} patterns from CodeDigger")
                        return patterns
                    else:
                        logger.error(f"CodeDigger /api/patterns failed: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to fetch patterns: {str(e)}")
            return None

    async def get_occurrences(
        self,
        pattern_id: str,
        limit: int = 5,
    ) -> Optional[List[Occurrence]]:
        """Fetch occurrences of a specific pattern from GitHub.

        Shows real-world examples of where this antipattern appears.

        Args:
            pattern_id: Pattern ID to fetch occurrences for
            limit: Maximum number of occurrences to return

        Returns:
            List of Occurrence objects, or None if request fails
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                params = {"pattern_id": pattern_id, "limit": limit}
                async with session.get(
                    f"{self.base_url}/api/occurrences", params=params
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        occurrences = [
                            Occurrence(**o) for o in data.get("occurrences", [])
                        ]
                        logger.debug(f"✓ Fetched {len(occurrences)} occurrences for {pattern_id}")
                        return occurrences
                    else:
                        logger.error(
                            f"CodeDigger /api/occurrences failed: {resp.status}"
                        )
                        return None
        except Exception as e:
            logger.error(f"Failed to fetch occurrences: {str(e)}")
            return None

    async def get_pattern_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """Get a specific pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern object, or None if not found
        """
        patterns = await self.get_patterns()
        if not patterns:
            return None

        for pattern in patterns:
            if pattern.pattern_id == pattern_id:
                return pattern

        logger.warning(f"Pattern {pattern_id} not found")
        return None

    async def get_stats(self, force_refresh: bool = False) -> Optional[CodeDiggerStats]:
        """Get CodeDigger statistics.

        Args:
            force_refresh: Force refresh even if cached

        Returns:
            CodeDiggerStats object, or None if request fails
        """
        # Check cache
        if not force_refresh and self.stats_cache is not None:
            if self.stats_cache_time and datetime.now() - self.stats_cache_time < self.cache_ttl:
                logger.debug("Using cached stats")
                return self.stats_cache

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/stats") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        stats = CodeDiggerStats(**data)
                        self.stats_cache = stats
                        self.stats_cache_time = datetime.now()
                        logger.info(f"✓ Fetched stats: {stats.patterns_count} patterns")
                        return stats
                    else:
                        logger.error(f"CodeDigger /api/stats failed: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to fetch stats: {str(e)}")
            return None

    async def search_patterns(
        self,
        keyword: str,
    ) -> Optional[List[Pattern]]:
        """Search patterns by keyword.

        Args:
            keyword: Keyword to search for

        Returns:
            List of matching Pattern objects
        """
        patterns = await self.get_patterns()
        if not patterns:
            return None

        # Case-insensitive search in keywords and name
        keyword_lower = keyword.lower()
        matches = [
            p for p in patterns
            if keyword_lower in p.name.lower()
            or any(keyword_lower in kw.lower() for kw in p.keywords)
        ]

        logger.debug(f"Found {len(matches)} patterns matching '{keyword}'")
        return matches


# Synchronous wrapper for CLI usage
class CodeDiggerClientSync:
    """Synchronous wrapper around CodeDiggerClient for CLI usage."""

    def __init__(
        self,
        base_url: str = "https://codedigger.membria.ai:4000",
        cache_ttl_hours: int = 24,
    ):
        """Initialize sync client."""
        self.client = CodeDiggerClient(base_url, cache_ttl_hours)

    def health_check(self) -> bool:
        """Check if CodeDigger is alive."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Handle case where event loop is already running
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.client.health_check()).result()
        return asyncio.run(self.client.health_check())

    def get_patterns(self, force_refresh: bool = False) -> Optional[List[Pattern]]:
        """Fetch all patterns."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.client.get_patterns(force_refresh)
                ).result()
        return asyncio.run(self.client.get_patterns(force_refresh))

    def get_occurrences(
        self,
        pattern_id: str,
        limit: int = 5,
    ) -> Optional[List[Occurrence]]:
        """Fetch occurrences for a pattern."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.client.get_occurrences(pattern_id, limit)
                ).result()
        return asyncio.run(self.client.get_occurrences(pattern_id, limit))

    def get_pattern_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """Get a specific pattern."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.client.get_pattern_by_id(pattern_id)
                ).result()
        return asyncio.run(self.client.get_pattern_by_id(pattern_id))

    def get_stats(self, force_refresh: bool = False) -> Optional[CodeDiggerStats]:
        """Get CodeDigger statistics."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.client.get_stats(force_refresh)
                ).result()
        return asyncio.run(self.client.get_stats(force_refresh))

    def search_patterns(self, keyword: str) -> Optional[List[Pattern]]:
        """Search patterns by keyword."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.client.search_patterns(keyword)
                ).result()
        return asyncio.run(self.client.search_patterns(keyword))
