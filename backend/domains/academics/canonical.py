from backend.domains.academics import dates, schools, subjects, text
from backend.domains.academics.dates import *  # noqa: F401,F403
from backend.domains.academics.schools import *  # noqa: F401,F403
from backend.domains.academics.subjects import *  # noqa: F401,F403
from backend.domains.academics.text import *  # noqa: F401,F403

__all__ = [
    *text.__all__,
    *schools.__all__,
    *subjects.__all__,
    *dates.__all__,
]
