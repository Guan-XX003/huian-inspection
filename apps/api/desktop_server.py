import os

import uvicorn


def main() -> None:
    os.environ.setdefault("HUIAN_DESKTOP", "1")
    os.environ.setdefault("HUIAN_API_HOST", "127.0.0.1")
    os.environ.setdefault("HUIAN_API_PORT", "8000")
    uvicorn.run(
        "app.main:app",
        host=os.environ["HUIAN_API_HOST"],
        port=int(os.environ["HUIAN_API_PORT"]),
        log_level=os.environ.get("HUIAN_LOG_LEVEL", "warning"),
    )


if __name__ == "__main__":
    main()
