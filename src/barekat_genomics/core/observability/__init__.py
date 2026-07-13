"""راه‌اندازی observability برای production."""

from barekat_genomics.core.observability.logging_config import configure_logging
from barekat_genomics.core.observability.sentry_setup import init_sentry


def setup_observability() -> None:
    configure_logging()
    init_sentry()
