import os 

def is_dev() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "development"