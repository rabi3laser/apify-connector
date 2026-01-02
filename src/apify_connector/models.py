"""
Data Models for Apify Connector
================================

These models are designed to be compatible with the existing
airbnb-scraper package models (ListingBasic, ListingDetails).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class RoomType(str, Enum):
    """Airbnb room types"""
    ENTIRE_HOME = "Entire home/apt"
    PRIVATE_ROOM = "Private room"
    SHARED_ROOM = "Shared room"
    HOTEL_ROOM = "Hotel room"


@dataclass
class Location:
    """Geographic location"""
    latitude: float
    longitude: float
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Host:
    """Host information (public data only)"""
    id: str
    name: str
    is_superhost: bool = False
    profile_pic_url: Optional[str] = None
    hosting_since: Optional[int] = None
    response_rate: Optional[int] = None
    response_time: Optional[str] = None
    total_listings: Optional[int] = None


@dataclass
class Rating:
    """Rating breakdown"""
    overall: float
    accuracy: Optional[float] = None
    cleanliness: Optional[float] = None
    checkin: Optional[float] = None
    communication: Optional[float] = None
    location: Optional[float] = None
    value: Optional[float] = None
    
    @property
    def is_guest_favorite_eligible(self) -> bool:
        return self.overall >= 4.9


@dataclass
class Review:
    """Single review"""
    id: str
    reviewer_name: str
    reviewer_id: Optional[str] = None
    date: Optional[datetime] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    language: Optional[str] = None
    response: Optional[str] = None


@dataclass
class CalendarDay:
    """Single day in calendar"""
    date: date
    available: bool
    price: Optional[float] = None
    min_nights: Optional[int] = None
    
    @property
    def is_blocked(self) -> bool:
        return not self.available


@dataclass
class Calendar:
    """Calendar with pricing for a listing"""
    listing_id: str
    days: List[CalendarDay] = field(default_factory=list)
    currency: str = "EUR"
    
    @property
    def occupancy_rate(self) -> float:
        if not self.days:
            return 0.0
        blocked = sum(1 for d in self.days if d.is_blocked)
        return (blocked / len(self.days)) * 100
    
    @property
    def average_price(self) -> Optional[float]:
        prices = [d.price for d in self.days if d.price is not None]
        return sum(prices) / len(prices) if prices else None
    
    @property
    def price_range(self) -> tuple:
        prices = [d.price for d in self.days if d.price is not None]
        if not prices:
            return None, None
        return min(prices), max(prices)
    
    def get_available_dates(self) -> List[date]:
        return [d.date for d in self.days if d.available]
    
    def get_blocked_dates(self) -> List[date]:
        return [d.date for d in self.days if d.is_blocked]


@dataclass
class ListingBasic:
    """Basic listing info - from search results"""
    id: str
    name: str
    url: str
    price_per_night: Optional[float] = None
    currency: str = "EUR"
    location: Optional[Location] = None
    room_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    beds: Optional[int] = None
    guests: Optional[int] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    is_superhost: bool = False
    instant_bookable: bool = False
    thumbnail_url: Optional[str] = None
    
    @property
    def airbnb_url(self) -> str:
        return f"https://www.airbnb.com/rooms/{self.id}"


@dataclass
class ListingDetails(ListingBasic):
    """Full listing details - from individual listing page"""
    description: Optional[str] = None
    space: Optional[str] = None
    neighborhood_overview: Optional[str] = None
    host: Optional[Host] = None
    rating_details: Optional[Rating] = None
    amenities: List[str] = field(default_factory=list)
    amenities_by_category: Dict[str, List[str]] = field(default_factory=dict)
    house_rules: List[str] = field(default_factory=list)
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    images: List[str] = field(default_factory=list)
    cancellation_policy: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    is_guest_favorite: bool = False
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    
    def has_amenity(self, amenity: str) -> bool:
        amenity_lower = amenity.lower()
        return any(amenity_lower in a.lower() for a in self.amenities)
    
    def get_amenities_by_category(self, category: str) -> List[str]:
        return self.amenities_by_category.get(category, [])
    
    @property
    def photo_count(self) -> int:
        return len(self.images)
    
    @property
    def description_length(self) -> int:
        return len(self.description) if self.description else 0


@dataclass
class SearchResult:
    """Result from location search"""
    listings: List[ListingBasic]
    total_count: int
    location: Location
    search_radius_km: float
    currency: str = "EUR"
    
    @property
    def average_price(self) -> Optional[float]:
        prices = [l.price_per_night for l in self.listings if l.price_per_night]
        return sum(prices) / len(prices) if prices else None
    
    @property
    def average_rating(self) -> Optional[float]:
        ratings = [l.rating for l in self.listings if l.rating]
        return sum(ratings) / len(ratings) if ratings else None
    
    @property
    def superhost_percentage(self) -> float:
        if not self.listings:
            return 0.0
        superhosts = sum(1 for l in self.listings if l.is_superhost)
        return (superhosts / len(self.listings)) * 100
