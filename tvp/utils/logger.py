import sys
import structlog


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    renderer = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), level.upper(), 20)
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
    )


logger = structlog.get_logger()
