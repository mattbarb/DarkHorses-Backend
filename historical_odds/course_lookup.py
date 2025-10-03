#!/usr/bin/env python3
"""
Course Lookup Module
Maps course names from Racing API to course_ids in ra_courses table
"""

import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

logger = logging.getLogger(__name__)


class CourseLookup:
    """Handles mapping of course names to course_ids"""

    def __init__(self):
        """Initialize with Supabase connection"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

        self.client = create_client(self.url, self.key)
        self.course_cache = {}  # Cache to avoid repeated lookups
        self._load_all_courses()

    def _load_all_courses(self):
        """Load all courses into cache for fast lookups"""
        try:
            response = self.client.table('ra_courses').select('course_id,name').execute()

            if response.data:
                for course in response.data:
                    name = course.get('name', '').strip()
                    course_id = course.get('course_id')

                    if name and course_id:
                        # Store multiple variations for matching
                        self.course_cache[name.lower()] = course_id
                        self.course_cache[name.upper()] = course_id
                        self.course_cache[name] = course_id

                        # Also store without spaces
                        name_no_space = name.replace(' ', '').lower()
                        self.course_cache[name_no_space] = course_id

                logger.info(f"Loaded {len(response.data)} courses into cache")
        except Exception as e:
            logger.error(f"Error loading courses: {e}")

    def get_course_id(self, course_name: str) -> Optional[str]:
        """
        Get course_id for a given course name from Racing API

        Args:
            course_name: Course name from Racing API (e.g., "Chelmsford (AW)")

        Returns:
            course_id from ra_courses table or None if not found
        """
        if not course_name:
            return None

        # Clean the course name
        clean_name = course_name.strip()

        # Remove common suffixes like (AW) for All Weather
        if '(' in clean_name:
            base_name = clean_name.split('(')[0].strip()
        else:
            base_name = clean_name

        # Try various matching strategies
        # 1. Direct match with original
        if clean_name in self.course_cache:
            return self.course_cache[clean_name]

        # 2. Direct match with base name
        if base_name in self.course_cache:
            return self.course_cache[base_name]

        # 3. Lowercase match
        if base_name.lower() in self.course_cache:
            return self.course_cache[base_name.lower()]

        # 4. Try without spaces
        no_space = base_name.replace(' ', '').lower()
        if no_space in self.course_cache:
            return self.course_cache[no_space]

        # 5. Try to find in database (in case cache is stale)
        try:
            # Search for similar name
            response = self.client.table('ra_courses').select('course_id,name').ilike('name', f'%{base_name}%').execute()

            if response.data and len(response.data) > 0:
                course_id = response.data[0].get('course_id')
                name = response.data[0].get('name')

                # Add to cache for future use
                if name and course_id:
                    self.course_cache[name.lower()] = course_id
                    self.course_cache[base_name.lower()] = course_id

                logger.debug(f"Found course_id for '{course_name}': {course_id}")
                return course_id
        except Exception as e:
            logger.error(f"Error searching for course {course_name}: {e}")

        logger.warning(f"No course_id found for '{course_name}'")
        return None

    def get_course_id_or_generate(self, course_name: str) -> str:
        """
        Get course_id or generate a placeholder if not found

        Args:
            course_name: Course name from Racing API

        Returns:
            course_id from ra_courses or generated placeholder
        """
        course_id = self.get_course_id(course_name)

        if course_id:
            return course_id

        # Generate a consistent placeholder ID
        # Format: crs_{clean_name}
        if not course_name:
            return 'crs_unknown'

        # Clean the name for ID generation
        clean = course_name.strip()
        if '(' in clean:
            clean = clean.split('(')[0].strip()

        # Convert to lowercase and replace spaces with underscores
        clean = clean.lower().replace(' ', '_').replace('-', '_')

        # Remove any non-alphanumeric characters
        clean = ''.join(c if c.isalnum() or c == '_' else '' for c in clean)

        generated_id = f'crs_{clean}'
        logger.info(f"Generated placeholder course_id for '{course_name}': {generated_id}")

        return generated_id


# Module-level instance for convenience
_course_lookup = None


def get_course_lookup() -> CourseLookup:
    """Get or create the global course lookup instance"""
    global _course_lookup
    if _course_lookup is None:
        _course_lookup = CourseLookup()
    return _course_lookup


def get_course_id(course_name: str) -> Optional[str]:
    """
    Convenience function to get course_id

    Args:
        course_name: Course name from Racing API

    Returns:
        course_id or None if not found
    """
    lookup = get_course_lookup()
    return lookup.get_course_id(course_name)