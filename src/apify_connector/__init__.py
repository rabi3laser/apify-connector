"""
Apify Connector - Legal Airbnb Data Access
==========================================

Provides legal access to Airbnb public data via Apify Actors.
No Airbnb credentials required - scrapes only publicly visible data.

Usage:
------
```python
from apify_connector import ApifyConnector

async with ApifyConnector(api_token="your_token") as connector:
    listing = await connector.get_listing("12345678")
    competitors = await connector.search_by_location(48.8566, 2.3522)
    calendar = await connector.get_calendar("12345678")
    reviews = await connector.get_reviews("12345678")
```
"""

__version__ = "1.0.0"
__author__ = "Rbie - AZUZ Project"

from .connector import ApifyConnector
from .models import (
    ListingDetails,
    ListingBasic,
    CalendarDay,
    Calendar,
    Review,
    SearchResult,
    Host,
    Location,
    Rating,
)
from .exceptions import (
    ApifyError,
    ActorRunError,
    RateLimitError,
    InvalidInputError,
)

__all__ = [
    "ApifyConnector",
    "ListingDetails",
    "ListingBasic",
    "CalendarDay",
    "Calendar",
    "Review",
    "SearchResult",
    "Host",
    "Location",
    "Rating",
    "ApifyError",
    "ActorRunError",
    "RateLimitError",
    "InvalidInputError",
]
