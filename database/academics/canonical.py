from database.academics import dates, schools, subjects, text
from database.academics.dates import *  # noqa: F401,F403
from database.academics.schools import *  # noqa: F401,F403
from database.academics.subjects import *  # noqa: F401,F403
from database.academics.text import *  # noqa: F401,F403

__all__ = [
    *text.__all__,
    *schools.__all__,
    *subjects.__all__,
    *dates.__all__,
]
