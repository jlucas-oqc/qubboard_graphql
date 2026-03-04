#!/usr/bin/env python
"""
Entry point for running the qupboard_graphql service with Uvicorn.

Usage::

    python -m qupboard_graphql.main
    # or, if installed as a script:
    qupboard-graphql
"""

import uvicorn

from qupboard_graphql.api.app import get_app


def main():
    """Create the FastAPI application and serve it with Uvicorn on port 8000."""
    app = get_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
