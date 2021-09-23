from corsheaders.middleware import CorsMiddleware

from pik.core.cache import cachedmethod

from .models import Cors


class CachedCorsMiddleware(CorsMiddleware):
    @cachedmethod("cors_{url.netloc}")
    def origin_found_in_white_lists(self, origin, url):
        return (super().origin_found_in_white_lists(origin, url)
                or Cors.objects.filter(cors=url.netloc.lower()).exists())
