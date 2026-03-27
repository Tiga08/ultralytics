import argparse
import uvicorn
from config.loader import ConfigLoader
from core.engine import TvpEngine
from utils.logger import configure_logging


def main():
    parser = argparse.ArgumentParser(description="Tiga Vision Platform")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--log-level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], default=None)
    args = parser.parse_args()

    config = ConfigLoader.load(args.config)
    if args.port:
        config.server.port = args.port
    if args.log_level:
        config.logging.level = args.log_level

    configure_logging(config.logging.level, config.logging.format)

    import detector   # noqa: F401 — 触发插件注册
    import output     # noqa: F401

    engine = TvpEngine()
    engine.start(config)

    from api.app import create_app
    app = create_app()
    uvicorn.run(app, host=config.server.host, port=config.server.port)


if __name__ == "__main__":
    main()
