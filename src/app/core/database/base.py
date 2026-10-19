"""Declarative base shared by domain-owned SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all domain-owned ORM models."""
