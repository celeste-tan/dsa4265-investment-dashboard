# backend/__init__.py
from app import app
from database import db

__all__ = ['app', 'db']
