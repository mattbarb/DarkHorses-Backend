"""
Regional Filtering Utilities
Provides UK and Ireland filtering for Racing API data
"""

import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


class RegionalFilter:
    """Handles filtering of racing data to UK and Ireland only"""

    # UK and Ireland region codes
    UK_IRELAND_REGIONS = {'gb', 'ire', 'GB', 'IRE', 'uk', 'UK'}
    UK_IRELAND_COUNTRIES = {
        'Great Britain', 'United Kingdom', 'UK', 'England', 'Scotland',
        'Wales', 'Northern Ireland', 'Ireland', 'Irish'
    }

    @staticmethod
    def is_uk_ireland_region(region_code: str) -> bool:
        """
        Check if a region code is UK or Ireland

        Args:
            region_code: Region code (e.g., 'gb', 'ire')

        Returns:
            True if UK/Ireland, False otherwise
        """
        if not region_code:
            return False
        return region_code.lower() in {'gb', 'ire', 'uk'}

    @staticmethod
    def is_uk_ireland_country(country_name: str) -> bool:
        """
        Check if a country name is UK or Ireland

        Args:
            country_name: Country name

        Returns:
            True if UK/Ireland, False otherwise
        """
        if not country_name:
            return False

        country_lower = country_name.lower()
        return any(
            uk_ire.lower() in country_lower
            for uk_ire in RegionalFilter.UK_IRELAND_COUNTRIES
        )

    @staticmethod
    def filter_horses_by_region(horses: List[Dict]) -> List[Dict]:
        """
        Filter horses to UK/Ireland only based on region field

        Args:
            horses: List of horse dictionaries from API

        Returns:
            Filtered list of UK/Ireland horses
        """
        uk_ire_horses = []

        for horse in horses:
            region = horse.get('region', '')
            # Include if region is UK/Ireland or empty (to be safe)
            if RegionalFilter.is_uk_ireland_region(region):
                uk_ire_horses.append(horse)
            elif not region:
                # Keep horses with no region specified (might be UK/IRE)
                uk_ire_horses.append(horse)
                logger.debug(f"Horse {horse.get('name')} has no region, including")

        logger.info(f"Filtered {len(horses)} horses to {len(uk_ire_horses)} UK/Ireland horses")
        return uk_ire_horses

    @staticmethod
    def filter_trainers_by_location(trainers: List[Dict]) -> List[Dict]:
        """
        Filter trainers to UK/Ireland based on location field

        Args:
            trainers: List of trainer dictionaries from API

        Returns:
            Filtered list of UK/Ireland trainers
        """
        uk_ire_trainers = []

        for trainer in trainers:
            location = trainer.get('location', '')

            # Check if location contains UK/Ireland indicators
            if location and RegionalFilter.is_uk_ireland_country(location):
                uk_ire_trainers.append(trainer)
            elif not location:
                # Keep trainers with no location (might be UK/IRE)
                uk_ire_trainers.append(trainer)
                logger.debug(f"Trainer {trainer.get('name')} has no location, including")

        logger.info(f"Filtered {len(trainers)} trainers to {len(uk_ire_trainers)} UK/Ireland trainers")
        return uk_ire_trainers

    @staticmethod
    def get_uk_ireland_course_ids(courses: List[Dict]) -> Set[str]:
        """
        Extract course IDs from UK/Ireland courses

        Args:
            courses: List of course dictionaries

        Returns:
            Set of UK/Ireland course IDs
        """
        course_ids = set()

        for course in courses:
            region = course.get('region_code', '')
            if RegionalFilter.is_uk_ireland_region(region):
                course_id = course.get('id')
                if course_id:
                    course_ids.add(str(course_id))

        logger.info(f"Found {len(course_ids)} UK/Ireland course IDs")
        return course_ids

    @staticmethod
    def filter_by_uk_ireland_activity(
        entities: List[Dict],
        entity_type: str,
        recent_races_threshold: int = None
    ) -> List[Dict]:
        """
        Filter entities (jockeys/owners) based on UK/Ireland racing activity

        Note: This is a placeholder for future enhancement.
        Currently returns all entities as the API doesn't provide
        sufficient region/activity data for jockeys and owners.

        Future enhancement: Could query race results to find which
        jockeys/owners are active in UK/Ireland races.

        Args:
            entities: List of entity dictionaries
            entity_type: Type of entity (jockey/owner)
            recent_races_threshold: Number of recent races to consider

        Returns:
            Filtered list (currently returns all)
        """
        logger.warning(
            f"Direct region filtering not available for {entity_type}. "
            f"Including all {len(entities)} {entity_type}s. "
            "Consider implementing activity-based filtering in future."
        )
        return entities


def get_regional_filter() -> RegionalFilter:
    """Get a RegionalFilter instance"""
    return RegionalFilter()
