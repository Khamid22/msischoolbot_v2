from shared.academics import dates, schools, subjects, text
from shared.academics.dates import *  # noqa: F401,F403
from shared.academics.schools import *  # noqa: F401,F403
from shared.academics.subjects import *  # noqa: F401,F403
from shared.academics.text import *  # noqa: F401,F403

__all__ = [
    *text.__all__,
    *schools.__all__,
    *subjects.__all__,
    *dates.__all__,
]
