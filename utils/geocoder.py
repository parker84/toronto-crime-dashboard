from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import GoogleV3
from decouple import config

STRINGS_TO_REPLACE = [
    ' st',
    ' st.',
    ' av',
    ' ave',
    ' rd',
    ' cres',
    ' blvd',
    ' dr',
    ' crt',
    # long
    ' street',
    ' avenue',
    ' road',
    ' boulevard',
    ' crescent',
    ' drive',
    ' court',
    # direction
    ' n',
    ' w',
    ' e',
    ' s'
]

class GeoCoder():

    def __init__(self) -> None:
        self.nomatim_geolocator = Nominatim(user_agent="toronto_crime_app")
        self.google_geolocator = GoogleV3(api_key=config("GOOGLE_API_KEY"))
        self.nomatim_geocoder = RateLimiter(self.nomatim_geolocator.geocode, min_delay_seconds=1)
        self.google_geocoder = RateLimiter(self.google_geolocator.geocode, min_delay_seconds=1)

    def geocode(self, address):
        location = self.nomatim_geocoder(address)
        if location is None:
            clean_address = self._clean_address(address)
            location = self.nomatim_geocoder(clean_address)
            if location is None and sum([s in address.lower() for s in STRINGS_TO_REPLACE]) > 0: # we add this 2nd check bc the google maps api seems to find an address for anything
                location = self.google_geocoder(clean_address)
        if location is None: # => wasn't fixed by any attempts above
            location = "Could Not Geocode Address"
        return location


    def _clean_address(self, address):
        if '+' in address or ' and ' in address.lower() or '&' in address:
            return self._clean_intersection(address) + ', Canada'
        else:
            return address + ', Canada'
    
    def _clean_intersection(self, address):
        clean_address = address.lower()
        for str_ in STRINGS_TO_REPLACE:
            clean_address = clean_address.replace(str_ + ' ', ' ')
            clean_address = clean_address.replace(str_ + ',', ',')
        return clean_address