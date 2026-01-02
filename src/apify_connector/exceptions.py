"""
Custom Exceptions for Apify Connector
======================================
"""


class ApifyError(Exception):
    """Base exception for Apify-related errors"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ActorRunError(ApifyError):
    """Error during Actor execution"""
    
    def __init__(self, actor_id: str, message: str, run_id: str = None):
        super().__init__(f"Actor '{actor_id}' failed: {message}")
        self.actor_id = actor_id
        self.run_id = run_id


class RateLimitError(ApifyError):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: int = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message)
        self.retry_after = retry_after


class InvalidInputError(ApifyError):
    """Invalid input parameters"""
    
    def __init__(self, param: str, message: str):
        super().__init__(f"Invalid parameter '{param}': {message}")
        self.param = param


class AuthenticationError(ApifyError):
    """API token invalid or missing"""
    
    def __init__(self):
        super().__init__("Invalid or missing Apify API token")


class DataParsingError(ApifyError):
    """Error parsing Actor output"""
    
    def __init__(self, actor_id: str, message: str, raw_data: dict = None):
        super().__init__(f"Failed to parse output from '{actor_id}': {message}")
        self.actor_id = actor_id
        self.raw_data = raw_data


class ListingNotFoundError(ApifyError):
    """Listing not found"""
    
    def __init__(self, listing_id: str):
        super().__init__(f"Listing '{listing_id}' not found")
        self.listing_id = listing_id


class NoResultsError(ApifyError):
    """Search returned no results"""
    
    def __init__(self, search_params: dict):
        super().__init__("Search returned no results")
        self.search_params = search_params
