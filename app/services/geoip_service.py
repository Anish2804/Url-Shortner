"""GeoIP resolution service with in-memory caching and emoji flag mapping."""

import ipaddress
import urllib.request
import json
from collections import OrderedDict
from typing import Optional, Tuple
from app.core.logging import get_logger

logger = get_logger("geoip_service")


def country_code_to_flag(country_code: Optional[str]) -> str:
    """Convert ISO 3166-1 alpha-2 country code to Unicode emoji flag."""
    if not country_code or len(country_code) != 2:
        return "🌐"
    try:
        return "".join(chr(ord(c.upper()) + 127397) for c in country_code)
    except Exception:
        return "🌐"


class GeoIPService:
    """Fast, cached IP geolocation resolver with graceful offline fallback."""

    def __init__(self, cache_size: int = 5000):
        self._cache: OrderedDict[str, Tuple[Optional[str], Optional[str]]] = OrderedDict()
        self._cache_size = cache_size

    def resolve(self, ip_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Resolve IP address to (country_code, city). Returns ('IN', 'Local') for local testing."""
        if not ip_str:
            return None, None

        clean_ip = ip_str.strip()

        # Check LRU cache
        if clean_ip in self._cache:
            self._cache.move_to_end(clean_ip)
            return self._cache[clean_ip]

        # Check private or loopback IP
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
            if ip_obj.is_private or ip_obj.is_loopback:
                # Local environment fallback for realistic dashboard visualization
                result = ("IN", "Local Network")
                self._store_cache(clean_ip, result)
                return result
        except ValueError:
            return None, None

        # Public IP lookup via lightweight GeoIP API
        try:
            url = f"http://ip-api.com/json/{clean_ip}?fields=status,countryCode,city"
            req = urllib.request.Request(url, headers={"User-Agent": "LinkScale-GeoIP/1.0"})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    result = (data.get("countryCode"), data.get("city"))
                    self._store_cache(clean_ip, result)
                    return result
        except Exception as e:
            logger.debug("GeoIP remote lookup failed for %s: %s", clean_ip, str(e))

        result = (None, None)
        self._store_cache(clean_ip, result)
        return result

    def _store_cache(self, ip: str, result: Tuple[Optional[str], Optional[str]]) -> None:
        self._cache[ip] = result
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)


geoip_service = GeoIPService()
