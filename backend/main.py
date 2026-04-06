from fastapi import FastAPI, Query, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from database import init_db, get_posts, get_popular_tags, create_post, get_post_by_id
from models import Post
from typing import Optional
from auth_routes import router as auth_router
from security import get_current_user
from logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Tag-Based Content Discovery",
    description="Discover and publish content organised by tags.",
    version="1.0.0",
)


origins = [
    "http://localhost:5173",  # Vite React dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a clean 422 response with field-level error details."""
    errors = exc.errors()
    logger.warning(
        "Validation error on %s %s | errors=%s",
        request.method, request.url.path, errors,
    )
    # Flatten into a readable message list
    messages = []
    for err in errors:
        loc = " → ".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = err.get("msg", "Invalid value")
        messages.append(f"{loc}: {msg}" if loc else msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": messages},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Log all HTTP exceptions at appropriate levels."""
    if exc.status_code >= 500:
        logger.error(
            "HTTPException %d on %s %s | %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    else:
        logger.warning(
            "HTTPException %d on %s %s | %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — never leak tracebacks to clients."""
    logger.critical(
        "Unhandled exception on %s %s | %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_db_client():
    logger.info("Application starting up…")
    await init_db()
    logger.info("Application ready.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
def read_root():
    return {"message": "Tag-Based Content Discovery API is running."}


@app.get("/posts", tags=["posts"])
async def fetch_posts(
    tags: Optional[str] = Query(None, description="Comma-separated tag list"),
    match: Optional[str] = Query("any", description="Match mode: 'any' or 'all'"),
):
    if match not in ("any", "all"):
        logger.warning("fetch_posts | invalid match mode: %s", match)
        raise HTTPException(status_code=400, detail="match must be 'any' or 'all'.")

    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else None
    logger.info("fetch_posts | tags=%s match=%s", tag_list, match)

    try:
        posts = await get_posts(tags=tag_list, match_mode=match)
        return posts
    except Exception as exc:
        logger.error("fetch_posts | error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch posts.")


@app.get("/tags/popular", tags=["tags"])
async def fetch_popular_tags():
    logger.info("fetch_popular_tags | request received")
    try:
        tags = await get_popular_tags()
        return tags
    except Exception as exc:
        logger.error("fetch_popular_tags | error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch popular tags.")


@app.post("/posts", tags=["posts"], status_code=status.HTTP_201_CREATED)
async def add_post(post: Post, current_user: dict = Depends(get_current_user)):
    logger.info("add_post | user=%s tags=%s", current_user["username"], post.tags)
    try:
        post_dict = post.model_dump()
        post_dict["author"] = current_user["username"]
        created_post = await create_post(post_dict)
        return created_post
    except Exception as exc:
        logger.error("add_post | error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create post.")


@app.get("/posts/{post_id}", tags=["posts"])
async def fetch_post(post_id: str):
    logger.info("fetch_post | id=%s", post_id)
    try:
        post = await get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found.")
        return post
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("fetch_post | error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching specific post.")

