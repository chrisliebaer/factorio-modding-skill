import logging


class LoggingConfigurator:
    """Configure application-wide logging."""

    @staticmethod
    def configure(debug: bool) -> None:
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            level=logging.DEBUG if debug else logging.INFO,
        )
