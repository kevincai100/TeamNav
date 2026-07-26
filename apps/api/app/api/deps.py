from fastapi import Request

from app.core.config import Settings
from app.db import Database


def settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def database_from_request(request: Request) -> Database:
    return request.app.state.database
