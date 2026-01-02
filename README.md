# 🔌 Apify Connector

**Legal Airbnb data access via Apify - No credentials required**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 🔒 **100% Legal** - Uses only publicly available data (no login required)
- 🚫 **No Airbnb credentials** - Hosts never share their passwords
- ⚡ **Fast** - Async/await support for parallel requests
- 📊 **Complete data** - Listings, calendar, pricing, reviews, competitors
- 🎯 **Type-safe** - Full type hints and dataclasses

## 🚀 Quick Start

### Installation

```bash
pip install git+https://github.com/rabi3laser/apify-connector.git
```

### Usage

```python
from apify_connector import ApifyConnector

async with ApifyConnector(api_token="apify_api_xxx") as connector:
    # Get listing details
    listing = await connector.get_listing("12345678")
    print(f"Name: {listing.name}")
    print(f"Price: {listing.price_per_night}€/night")
    
    # Search competitors
    competitors = await connector.search_by_location(
        latitude=48.8566,
        longitude=2.3522,
        radius_km=2
    )
    print(f"Found {competitors.total_count} competitors")
    
    # Get calendar (365 days)
    calendar = await connector.get_calendar("12345678")
    print(f"Occupancy rate: {calendar.occupancy_rate:.1f}%")
    
    # Get reviews
    reviews = await connector.get_reviews("12345678", limit=50)
```

## ⚖️ Legal Compliance

- ✅ Scrapes **publicly visible data only** (no login required)
- ✅ No Airbnb credentials used
- ✅ Compliant with hiQ v. LinkedIn (2022) precedent
- ✅ GDPR: Legitimate interest basis

## 🔧 Apify Actors Used

| Actor | Purpose | Pricing |
|-------|---------|---------|
| `tri_angle/airbnb-scraper` | Detailed listings | $1.25/1K |
| `tri_angle/new-fast-airbnb-scraper` | Fast search | $0.50/1K |
| `rigelbytes/airbnb-availability-calendar` | Calendar | $10/month |
| `tri_angle/airbnb-reviews-scraper` | Reviews | Free tier |

## 📄 License

MIT License

---

**Made with ❤️ by Rbie - AZUZ Project**
