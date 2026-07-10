from backend.modules.academics import dates, schools, subjects, text
from backend.modules.academics.dates import *  # noqa: F401,F403
from backend.modules.academics.schools import *  # noqa: F401,F403
from backend.modules.academics.subjects import *  # noqa: F401,F403
from backend.modules.academics.text import *  # noqa: F401,F403

__all__ = [
    *text.__all__,
    *schools.__all__,
    *subjects.__all__,
    *dates.__all__,
]
