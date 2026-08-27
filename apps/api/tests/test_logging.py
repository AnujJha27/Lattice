import logging


def test_uvicorn_logging_does_not_duplicate_through_root_handler():
    from app.core.logging import setup_logging

    setup_logging()

    assert logging.getLogger("uvicorn").propagate is False
    assert logging.getLogger("uvicorn.error").propagate is False
