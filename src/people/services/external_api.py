import requests
from django.core.cache import cache
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class BaseAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def make_request(self, params: dict, cache_key: str) -> dict | None:
        try:
            return self._make_request(params, cache_key)
        except RetryError:
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1),
        retry=retry_if_exception_type((requests.RequestException, ValueError)),
    )
    def _make_request(self, params: dict, cache_key: str) -> dict:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
        except requests.RequestException:
            raise

        try:
            data = response.json()
        except ValueError:
            raise
        else:
            cache.set(cache_key, data)
            return data


class GenderizeClient(BaseAPIClient):
    def get_data(self, name: str) -> str | None:
        cache_key = f'gender:{name.lower()}'
        params = {'name': name}
        data = self.make_request(params, cache_key)
        return data.get('gender') if data is not None else None


class AgifyClient(BaseAPIClient):
    def get_data(self, name: str) -> int | None:
        cache_key = f'age:{name.lower()}'
        params = {'name': name}
        data = self.make_request(params, cache_key)
        return data.get('age') if data is not None else None


class NationalizeClient(BaseAPIClient):
    def get_data(self, name: str) -> str | None:
        cache_key = f'nationality:{name.lower()}'
        params = {'name': name}
        data = self.make_request(params, cache_key)
        if data is None:
            return None
        country_info = data.get('country', [])
        if not country_info:
            return None
        top_country = max(country_info, key=lambda c: c.get('probability', 0))
        return top_country.get('country_id') if data is not None else None


class NameInfoClient:
    def __init__(self):
        self.gender_client = GenderizeClient('https://api.genderize.io')
        self.age_client = AgifyClient('https://api.agify.io')
        self.nationalize_client = NationalizeClient(
            'https://api.nationalize.io'
        )

    def get_gender(self, name: str) -> str | None:
        return self.gender_client.get_data(name)

    def get_age(self, name: str) -> int | None:
        return self.age_client.get_data(name)

    def get_nationality(self, name: str) -> str | None:
        return self.nationalize_client.get_data(name)
