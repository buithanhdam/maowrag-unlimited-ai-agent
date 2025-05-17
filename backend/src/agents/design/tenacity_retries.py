import json
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_chain, wait_fixed, before_sleep_log
import logging
from src.logger import get_formatted_logger
def retry_on_error():
    wait_strategy = wait_chain(
        wait_fixed(1),
        wait_fixed(2),
        wait_fixed(5)
    )
    return retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_strategy,
        before_sleep=before_sleep_log(get_formatted_logger(__file__), logging.WARNING),
        reraise=True
    )
def retry_on_json_parse_error():
    wait_strategy = wait_chain(
        wait_fixed(1),
        wait_fixed(2),
        wait_fixed(5)
    )
    return retry(
        retry=retry_if_exception_type(json.JSONDecodeError),
        stop=stop_after_attempt(3),
        wait=wait_strategy,
        before_sleep=before_sleep_log(get_formatted_logger(__file__), logging.WARNING),
        reraise=True
    )