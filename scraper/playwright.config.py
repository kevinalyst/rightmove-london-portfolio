import os

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "45")) * 1000

config = {
    "use": {
        "headless": HEADLESS,
        "timeout": REQUEST_TIMEOUT,
    }
}

