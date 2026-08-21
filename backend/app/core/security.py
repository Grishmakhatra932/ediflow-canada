import os

from fastapi import Header, HTTPException, status
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("API_KEY")


def verify_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    if not API_KEY:
        raise RuntimeError(
            "API_KEY environment variable is not configured"
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )