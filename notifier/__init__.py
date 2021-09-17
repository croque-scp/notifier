import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

# boto emits too many logs on DEBUG
logging.getLogger("botocore").setLevel("INFO")
