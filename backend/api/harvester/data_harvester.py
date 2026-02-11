"""
Data Harvester - ABC + Scheduler for external data sources.

Pulls public API data (weather, electricity prices, solar times, market prices,
tourism indices) on configurable schedules and stores alongside sensor data.

Follows the same ABC pattern as NotificationChannel in notification_service.py.

Author: AgriTech Hydroponics
License: MIT
"""

import json
import logging
import threading
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger('data-harvester')


class DataSource(ABC):
    """Abstract base for external data sources (weather, electricity, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name."""
        ...

    @property
    @abstractmethod
    def interval_seconds(self) -> int:
        """How often to fetch data, in seconds."""
        ...

    @abstractmethod
    def fetch(self) -> Dict[str, Any]:
        """Fetch data from external API. Returns parsed data dict."""
        ...

    @abstractmethod
    def store(self, data: Dict[str, Any]) -> None:
        """Store fetched data to InfluxDB or SQLite."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is configured and reachable."""
        ...

    def harvest(self) -> Dict[str, Any]:
        """Fetch + store. Returns status dict."""
        started = time.time()
        try:
            data = self.fetch()
            self.store(data)
            elapsed = round(time.time() - started, 2)
            logger.info(f"[{self.name}] Harvested successfully in {elapsed}s")
            return {
                'source': self.name,
                'status': 'ok',
                'elapsed_seconds': elapsed,
                'timestamp': datetime.utcnow().isoformat(),
                'records': len(data) if isinstance(data, (list, dict)) else 1,
            }
        except Exception as e:
            elapsed = round(time.time() - started, 2)
            logger.error(f"[{self.name}] Harvest failed: {e}")
            return {
                'source': self.name,
                'status': 'error',
                'error': str(e),
                'elapsed_seconds': elapsed,
                'timestamp': datetime.utcnow().isoformat(),
            }

    # ── Convenience HTTP helper ────────────────────────────────

    @staticmethod
    def _http_get_json(url: str, timeout: int = 15) -> Any:
        """GET a URL and parse JSON response using urllib.request."""
        req = urllib.request.Request(url, headers={
            'User-Agent': 'AgriTech-DataHarvester/1.0',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    @staticmethod
    def _http_get_text(url: str, timeout: int = 15) -> str:
        """GET a URL and return raw text using urllib.request."""
        req = urllib.request.Request(url, headers={
            'User-Agent': 'AgriTech-DataHarvester/1.0',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8')


class HarvestScheduler:
    """Manages scheduled harvesting of all registered DataSources using daemon threads."""

    def __init__(self):
        self._sources: Dict[str, DataSource] = {}
        self._timers: Dict[str, threading.Timer] = {}
        self._status: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._lock = threading.Lock()

    def register(self, source: DataSource) -> None:
        """Register a data source for scheduled harvesting."""
        with self._lock:
            self._sources[source.name] = source
            self._status[source.name] = {
                'registered': True,
                'available': source.is_available(),
                'last_harvest': None,
                'last_status': None,
                'interval_seconds': source.interval_seconds,
            }
        logger.info(f"Registered source: {source.name} (interval: {source.interval_seconds}s)")

    def start(self) -> None:
        """Start scheduled harvesting for all registered sources."""
        with self._lock:
            self._running = True
            for name, source in self._sources.items():
                if source.is_available():
                    self._schedule_source(name, source)
        logger.info(f"HarvestScheduler started with {len(self._sources)} sources")

    def stop(self) -> None:
        """Stop all scheduled harvesting."""
        with self._lock:
            self._running = False
            for name, timer in self._timers.items():
                timer.cancel()
            self._timers.clear()
        logger.info("HarvestScheduler stopped")

    def harvest_now(self, source_name: str = None) -> List[Dict[str, Any]]:
        """Manually trigger harvest for one or all sources."""
        results = []
        with self._lock:
            sources = {source_name: self._sources[source_name]} if source_name else self._sources
        for name, source in sources.items():
            result = source.harvest()
            with self._lock:
                self._status[name]['last_harvest'] = result.get('timestamp')
                self._status[name]['last_status'] = result.get('status')
            results.append(result)
        return results

    def get_status(self) -> Dict[str, Any]:
        """Return status of all registered sources."""
        with self._lock:
            return {
                'running': self._running,
                'sources': dict(self._status),
                'source_count': len(self._sources),
            }

    def get_source(self, name: str) -> Optional[DataSource]:
        """Get a registered source by name."""
        return self._sources.get(name)

    def _schedule_source(self, name: str, source: DataSource) -> None:
        """Schedule the next harvest for a source (called inside lock or from timer thread)."""
        def _run():
            result = source.harvest()
            with self._lock:
                self._status[name]['last_harvest'] = result.get('timestamp')
                self._status[name]['last_status'] = result.get('status')
                if self._running:
                    self._schedule_source(name, source)

        timer = threading.Timer(source.interval_seconds, _run)
        timer.daemon = True
        timer.start()
        self._timers[name] = timer
