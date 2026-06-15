from pathlib import Path

from alembic import command
from alembic.config import Config

from expense_App.logger import get_logger


logger = get_logger(__name__)


def init_db() -> None:
    backend_dir = Path(__file__).resolve().parent
    config = Config(str(backend_dir / "alembic.ini"))
    logger.info("Applying database migrations to head")
    command.upgrade(config, "head")
    logger.info("Database migrations are up to date")


if __name__ == "__main__":
    init_db()
