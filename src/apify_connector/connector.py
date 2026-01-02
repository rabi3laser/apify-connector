"""
Apify Connector - Main Class
=============================

Legal access to Airbnb public data via Apify Actors.
"""

import asyncio
import logging
import re
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union
from dataclasses import asdict

import httpx

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
    AuthenticationError,
    DataParsingError,
    ListingNotFoundError,
    NoResultsError,
)

logger = logging.getLogger(__name__)


class ApifyActors:
    """Apify Actor IDs for Airbnb scraping"""
    LISTING_SCRAPER = "tri_angle/airbnb-scraper"
    FAST_SCRAPER = "tri_angle/new-fast-airbnb-scraper"
    CALENDAR_SCRAPER = "rigelbytes/airbnb-availability-calendar"
    REVIEWS_SCRAPER = "tri_angle/airbnb-reviews-scraper"
    URL_SCRAPER = "tri_angle/airbnb-rooms-urls-scraper"


class ApifyConnector:
    """
    Apify Connector for legal Airbnb data access.
    
    Uses Apify Actors to scrape publicly available data only.
    No Airbnb credentials required.
    
    Usage:
    ------
    ```python
    async with ApifyConnector(api_token="your_token") as connector:
        listing = await connector.get_listing("12345678")
        competitors = await connector.search_by_location(48.8566, 2.3522)
    ```
    """
    
    BASE_URL = "https://api.apify.com/v2"
    DEFAULT_TIMEOUT = 300
    
    def __init__(
        self,
        api_token: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        if not api_token or not api_token.startswith("apify_api_"):
            raise AuthenticationError()
        
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "ApifyConnector":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Connector not initialized. Use 'async with' context manager.")
        return self._client
    
    async def _run_actor(
        self,
        actor_id: str,
        input_data: Dict[str, Any],
        wait_for_finish: bool = True,
    ) -> List[Dict[str, Any]]:
        """Run an Apify Actor and get results."""
        url = f"{self.BASE_URL}/acts/{actor_id}/runs"
        
        logger.info(f"Running Actor: {actor_id}")
        logger.debug(f"Input: {input_data}")
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    url,
                    json=input_data,
                    params={"waitForFinish": self.timeout if wait_for_finish else 0},
                )
                
                if response.status_code == 401:
                    raise AuthenticationError()
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(retry_after=retry_after)
                
                if response.status_code >= 400:
                    raise ActorRunError(
                        actor_id=actor_id,
                        message=f"HTTP {response.status_code}: {response.text}"
                    )
                
                run_data = response.json()["data"]
                run_id = run_data["id"]
                status = run_data["status"]
                
                logger.info(f"Actor run started: {run_id}, status: {status}")
                
                if status == "SUCCEEDED":
                    return await self._get_dataset_items(run_data["defaultDatasetId"])
                
                elif status == "FAILED":
                    raise ActorRunError(actor_id=actor_id, message="Actor run failed", run_id=run_id)
                
                elif status == "RUNNING" and wait_for_finish:
                    return await self._wait_for_run(actor_id, run_id)
                
                return []
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise ActorRunError(actor_id=actor_id, message=str(e))
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    async def _wait_for_run(
        self,
        actor_id: str,
        run_id: str,
        poll_interval: int = 5,
    ) -> List[Dict[str, Any]]:
        """Wait for Actor run to complete and return results"""
        url = f"{self.BASE_URL}/actor-runs/{run_id}"
        
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < self.timeout:
            response = await self.client.get(url)
            run_data = response.json()["data"]
            status = run_data["status"]
            
            if status == "SUCCEEDED":
                return await self._get_dataset_items(run_data["defaultDatasetId"])
            
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise ActorRunError(actor_id=actor_id, message=f"Actor run {status.lower()}", run_id=run_id)
            
            await asyncio.sleep(poll_interval)
        
        raise ActorRunError(actor_id=actor_id, message="Actor run timed out", run_id=run_id)
    
    async def _get_dataset_items(self, dataset_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get items from Actor dataset"""
        url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        response = await self.client.get(url, params={"limit": limit})
        
        if response.status_code >= 400:
            raise ApifyError(f"Failed to get dataset: {response.text}")
        
        return response.json()
    
    # =========================================================================
    # PUBLIC METHODS - LISTINGS
    # =========================================================================
    
    async def get_listing(self, listing_id: str) -> ListingDetails:
        """Get detailed information for a single listing."""
        listing_id = self._extract_listing_id(listing_id)
        logger.info(f"Fetching listing: {listing_id}")
        
        results = await self._run_actor(
            ApifyActors.LISTING_SCRAPER,
            {"listingIds": [listing_id], "maxListings": 1, "includeReviews": False, "includeCalendar": False}
        )
        
        if not results:
            raise ListingNotFoundError(listing_id)
        
        return self._parse_listing_details(results[0])
    
    async def get_listings(self, listing_ids: List[str]) -> List[ListingDetails]:
        """Get detailed information for multiple listings."""
        ids = [self._extract_listing_id(lid) for lid in listing_ids]
        logger.info(f"Fetching {len(ids)} listings")
        
        results = await self._run_actor(
            ApifyActors.LISTING_SCRAPER,
            {"listingIds": ids, "maxListings": len(ids), "includeReviews": False, "includeCalendar": False}
        )
        
        return [self._parse_listing_details(r) for r in results]
    
    # =========================================================================
    # PUBLIC METHODS - SEARCH
    # =========================================================================
    
    async def search_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 2.0,
        max_results: int = 50,
        room_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        currency: str = "EUR",
    ) -> SearchResult:
        """Search for listings near a location."""
        logger.info(f"Searching listings at ({latitude}, {longitude}), radius={radius_km}km")
        
        input_data = {
            "locationQuery": f"{latitude},{longitude}",
            "maxListings": max_results,
            "currency": currency,
            "simple": True,
        }
        
        if room_type:
            input_data["roomType"] = room_type
        if min_price is not None:
            input_data["minPrice"] = int(min_price)
        if max_price is not None:
            input_data["maxPrice"] = int(max_price)
        if min_bedrooms is not None:
            input_data["minBedrooms"] = min_bedrooms
        
        results = await self._run_actor(ApifyActors.FAST_SCRAPER, input_data)
        
        listings = []
        for r in results:
            listing = self._parse_listing_basic(r)
            if listing.location:
                distance = self._haversine_distance(
                    latitude, longitude,
                    listing.location.latitude, listing.location.longitude
                )
                if distance <= radius_km:
                    listings.append(listing)
            else:
                listings.append(listing)
        
        return SearchResult(
            listings=listings[:max_results],
            total_count=len(listings),
            location=Location(latitude=latitude, longitude=longitude),
            search_radius_km=radius_km,
            currency=currency,
        )
    
    async def search_by_address(
        self,
        address: str,
        radius_km: float = 2.0,
        max_results: int = 50,
        **kwargs,
    ) -> SearchResult:
        """Search for listings near an address."""
        logger.info(f"Searching listings near: {address}")
        
        input_data = {"locationQuery": address, "maxListings": max_results, "simple": True, **kwargs}
        results = await self._run_actor(ApifyActors.FAST_SCRAPER, input_data)
        
        if not results:
            raise NoResultsError({"address": address})
        
        listings = [self._parse_listing_basic(r) for r in results]
        center = listings[0].location if listings and listings[0].location else Location(0, 0)
        
        return SearchResult(
            listings=listings[:max_results],
            total_count=len(listings),
            location=center,
            search_radius_km=radius_km,
            currency=kwargs.get("currency", "EUR"),
        )
    
    # =========================================================================
    # PUBLIC METHODS - CALENDAR
    # =========================================================================
    
    async def get_calendar(self, listing_id: str, days: int = 365) -> Calendar:
        """Get calendar and pricing for a listing."""
        listing_id = self._extract_listing_id(listing_id)
        logger.info(f"Fetching calendar for listing: {listing_id}")
        
        results = await self._run_actor(
            ApifyActors.CALENDAR_SCRAPER,
            {"listingIds": [listing_id], "months": min(12, (days + 29) // 30)}
        )
        
        if not results:
            return Calendar(listing_id=listing_id, days=[])
        
        return self._parse_calendar(listing_id, results)
    
    # =========================================================================
    # PUBLIC METHODS - REVIEWS
    # =========================================================================
    
    async def get_reviews(self, listing_id: str, limit: int = 100) -> List[Review]:
        """Get reviews for a listing."""
        listing_id = self._extract_listing_id(listing_id)
        logger.info(f"Fetching reviews for listing: {listing_id}")
        
        results = await self._run_actor(
            ApifyActors.REVIEWS_SCRAPER,
            {"listingUrls": [f"https://www.airbnb.com/rooms/{listing_id}"], "maxReviews": limit}
        )
        
        return [self._parse_review(r) for r in results]
    
    # =========================================================================
    # PARSING METHODS
    # =========================================================================
    
    def _parse_listing_details(self, data: Dict[str, Any]) -> ListingDetails:
        """Parse raw Actor output to ListingDetails"""
        try:
            location = None
            if data.get("lat") and data.get("lng"):
                location = Location(
                    latitude=data["lat"],
                    longitude=data["lng"],
                    city=data.get("city"),
                    neighborhood=data.get("neighborhood"),
                    country=data.get("country"),
                )
            
            host = None
            host_data = data.get("host", {})
            if host_data:
                host = Host(
                    id=str(host_data.get("id", "")),
                    name=host_data.get("name", ""),
                    is_superhost=host_data.get("isSuperhost", False),
                    profile_pic_url=host_data.get("profilePicUrl"),
                    response_rate=host_data.get("responseRate"),
                    response_time=host_data.get("responseTime"),
                )
            
            rating_details = None
            if data.get("rating"):
                rating_details = Rating(
                    overall=data.get("rating", 0),
                    accuracy=data.get("ratingAccuracy"),
                    cleanliness=data.get("ratingCleanliness"),
                    checkin=data.get("ratingCheckin"),
                    communication=data.get("ratingCommunication"),
                    location=data.get("ratingLocation"),
                    value=data.get("ratingValue"),
                )
            
            return ListingDetails(
                id=str(data.get("id", data.get("listingId", ""))),
                name=data.get("name", data.get("title", "")),
                url=data.get("url", f"https://www.airbnb.com/rooms/{data.get('id', '')}"),
                price_per_night=data.get("price", data.get("pricePerNight")),
                currency=data.get("currency", "EUR"),
                location=location,
                room_type=data.get("roomType"),
                bedrooms=data.get("bedrooms"),
                bathrooms=data.get("bathrooms"),
                beds=data.get("beds"),
                guests=data.get("personCapacity", data.get("guests")),
                rating=data.get("rating"),
                reviews_count=data.get("reviewsCount", data.get("numberOfReviews", 0)),
                rating_details=rating_details,
                host=host,
                is_superhost=data.get("isSuperhost", host.is_superhost if host else False),
                description=data.get("description"),
                space=data.get("space"),
                neighborhood_overview=data.get("neighborhoodOverview"),
                amenities=data.get("amenities", []),
                amenities_by_category=data.get("amenitiesByCategory", {}),
                house_rules=data.get("houseRules", []),
                check_in_time=data.get("checkIn"),
                check_out_time=data.get("checkOut"),
                images=data.get("images", data.get("photos", [])),
                thumbnail_url=data.get("thumbnail", data.get("mainImage")),
                instant_bookable=data.get("isInstantBook", data.get("instantBookable", False)),
                is_guest_favorite=data.get("isGuestFavorite", False),
                cancellation_policy=data.get("cancellationPolicy"),
                highlights=data.get("highlights", []),
            )
            
        except Exception as e:
            raise DataParsingError(actor_id=ApifyActors.LISTING_SCRAPER, message=str(e), raw_data=data)
    
    def _parse_listing_basic(self, data: Dict[str, Any]) -> ListingBasic:
        """Parse raw Actor output to ListingBasic"""
        location = None
        if data.get("lat") and data.get("lng"):
            location = Location(
                latitude=data["lat"],
                longitude=data["lng"],
                city=data.get("city"),
                neighborhood=data.get("neighborhood"),
            )
        
        return ListingBasic(
            id=str(data.get("id", data.get("listingId", ""))),
            name=data.get("name", data.get("title", "")),
            url=data.get("url", f"https://www.airbnb.com/rooms/{data.get('id', '')}"),
            price_per_night=data.get("price", data.get("pricePerNight")),
            currency=data.get("currency", "EUR"),
            location=location,
            room_type=data.get("roomType"),
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            beds=data.get("beds"),
            guests=data.get("personCapacity", data.get("guests")),
            rating=data.get("rating"),
            reviews_count=data.get("reviewsCount", data.get("numberOfReviews", 0)),
            is_superhost=data.get("isSuperhost", False),
            instant_bookable=data.get("isInstantBook", False),
            thumbnail_url=data.get("thumbnail", data.get("mainImage")),
        )
    
    def _parse_calendar(self, listing_id: str, results: List[Dict[str, Any]]) -> Calendar:
        """Parse calendar data"""
        days = []
        
        for item in results:
            calendar_data = item.get("calendar", item.get("days", []))
            
            if isinstance(calendar_data, list):
                for day_data in calendar_data:
                    try:
                        day_date = day_data.get("date")
                        if isinstance(day_date, str):
                            day_date = datetime.strptime(day_date[:10], "%Y-%m-%d").date()
                        
                        days.append(CalendarDay(
                            date=day_date,
                            available=day_data.get("available", day_data.get("isAvailable", True)),
                            price=day_data.get("price", day_data.get("pricePerNight")),
                            min_nights=day_data.get("minNights"),
                        ))
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse calendar day: {e}")
                        continue
        
        days.sort(key=lambda d: d.date)
        
        return Calendar(
            listing_id=listing_id,
            days=days,
            currency=results[0].get("currency", "EUR") if results else "EUR",
        )
    
    def _parse_review(self, data: Dict[str, Any]) -> Review:
        """Parse review data"""
        review_date = None
        if data.get("date") or data.get("createdAt"):
            date_str = data.get("date", data.get("createdAt"))
            try:
                if isinstance(date_str, str):
                    review_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        return Review(
            id=str(data.get("id", "")),
            reviewer_name=data.get("reviewer", {}).get("name", data.get("reviewerName", "")),
            reviewer_id=data.get("reviewer", {}).get("id"),
            date=review_date,
            rating=data.get("rating"),
            comment=data.get("comments", data.get("text", "")),
            language=data.get("language"),
            response=data.get("response"),
        )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _extract_listing_id(self, listing_input: str) -> str:
        """Extract listing ID from URL or return as-is if already an ID"""
        listing_input = str(listing_input).strip()
        
        if listing_input.isdigit():
            return listing_input
        
        patterns = [
            r"airbnb\.[a-z.]+/rooms/(\d+)",
            r"airbnb\.[a-z.]+/h/([a-zA-Z0-9-]+)",
            r"/rooms/(\d+)",
            r"listing[_-]?id[=:]?\s*(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, listing_input, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return listing_input
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
