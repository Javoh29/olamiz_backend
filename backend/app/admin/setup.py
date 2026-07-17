"""Подключение SQLAdmin поверх тех же моделей.

Views (Suppliers, Listings, Bookings, Disputes, …) добавляются по мере
появления моделей — backend.md §8.
"""

from fastapi import FastAPI
from sqladmin import Admin

from app.core.db import engine


def init_admin(app: FastAPI) -> Admin:
    return Admin(app, engine, base_url="/admin")
