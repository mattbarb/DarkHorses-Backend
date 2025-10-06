"""
Racing API Client for Reference Data Fetching
Handles authentication, rate limiting, retries, and error handling
"""

import time
import requests
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RacingAPIClient:
    """Client for Racing API with rate limiting and error handling"""

    def __init__(self, username: str, password: str, base_url: str = "https://api.theracingapi.com/v1",
                 timeout: int = 30, max_retries: int = 5, rate_limit: int = 2):
        """
        Initialize API client

        Args:
            username: API username
            password: API password
            base_url: Base URL for API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per second
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_request_interval = 1.0 / rate_limit
        self.last_request_time = 0

        # Create auth headers
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
            "User-Agent": "RacingAPI-ReferenceFetcher/1.0"
        }

        # Statistics
        self.stats = {
            'requests': 0,
            'errors': 0,
            'retries': 0
        }

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request with retries

        Args:
            endpoint: API endpoint (e.g., /courses)
            params: Query parameters

        Returns:
            Response data or None on failure
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self._rate_limit()

                # Make request
                self.stats['requests'] += 1
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)

                # Check response
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API credentials")
                    return None
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    self.stats['retries'] += 1
                    continue
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}, attempt {attempt + 1}/{self.max_retries}")
                    self.stats['retries'] += 1
                    time.sleep((attempt + 1) * 2)

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout for {url}, attempt {attempt + 1}/{self.max_retries}")
                self.stats['retries'] += 1
                time.sleep((attempt + 1) * 2)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error for {url}: {e}, attempt {attempt + 1}/{self.max_retries}")
                self.stats['retries'] += 1
                time.sleep((attempt + 1) * 2)

        # All retries failed
        self.stats['errors'] += 1
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def get_courses(self, region_codes: Optional[List[str]] = None) -> Optional[Dict]:
        """Get list of courses"""
        params = {}
        if region_codes:
            params['region_codes'] = region_codes
        return self._make_request('/courses', params)

    def get_regions(self) -> Optional[Dict]:
        """Get list of regions"""
        return self._make_request('/courses/regions')

    def search_horses(self, name: Optional[str] = None, limit: int = 500, skip: int = 0) -> Optional[Dict]:
        """Search for horses"""
        params = {'limit': limit, 'skip': skip}
        if name:
            params['name'] = name
        return self._make_request('/horses/search', params)

    def get_horse_details(self, horse_id: str, tier: str = 'standard') -> Optional[Dict]:
        """Get detailed horse information"""
        return self._make_request(f'/horses/{horse_id}/{tier}')

    def search_jockeys(self, name: Optional[str] = None, limit: int = 500, skip: int = 0) -> Optional[Dict]:
        """Search for jockeys"""
        params = {'limit': limit, 'skip': skip}
        if name:
            params['name'] = name
        return self._make_request('/jockeys/search', params)

    def search_trainers(self, name: Optional[str] = None, limit: int = 500, skip: int = 0) -> Optional[Dict]:
        """Search for trainers"""
        params = {'limit': limit, 'skip': skip}
        if name:
            params['name'] = name
        return self._make_request('/trainers/search', params)

    def search_owners(self, name: Optional[str] = None, limit: int = 500, skip: int = 0) -> Optional[Dict]:
        """Search for owners"""
        params = {'limit': limit, 'skip': skip}
        if name:
            params['name'] = name
        return self._make_request('/owners/search', params)

    def get_results(self, date: Optional[str] = None, course_ids: Optional[List[str]] = None,
                    region_codes: Optional[List[str]] = None, limit: int = 50, skip: int = 0) -> Optional[Dict]:
        """Get race results - Note: Max limit is 50"""
        params = {'limit': min(limit, 50), 'skip': skip}
        if date:
            params['date'] = date
        if course_ids:
            params['course_ids'] = course_ids
        if region_codes:
            params['region_codes'] = region_codes
        return self._make_request('/results', params)

    def get_racecards_pro(self, date: Optional[str] = None, course_ids: Optional[List[str]] = None,
                          region_codes: Optional[List[str]] = None) -> Optional[Dict]:
        """Get racecards (pro tier) - Note: This endpoint doesn't support limit/skip parameters"""
        params = {}
        if date:
            params['date'] = date
        if course_ids:
            params['course_ids'] = course_ids
        if region_codes:
            params['region_codes'] = region_codes
        return self._make_request('/racecards/pro', params)

    def get_stats(self) -> Dict:
        """Get client statistics"""
        return self.stats.copy()
