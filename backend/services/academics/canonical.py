from backend.services.academics import dates
from backend.services.academics import schools
from backend.services.academics import subjects
from backend.services.academics import text
from backend.services.academics.dates import *  # noqa: F401,F403
from backend.services.academics.schools import *  # noqa: F401,F403
from backend.services.academics.subjects import *  # noqa: F401,F403
from backend.services.academics.text import *  # noqa: F401,F403

__all__ = [
    *text.__all__,
    *schools.__all__,
    *subjects.__all__,
    *dates.__all__,
]
