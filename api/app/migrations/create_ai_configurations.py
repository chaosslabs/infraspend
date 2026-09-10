"""Add AI billing sources without altering existing configurations."""

from app.helpers.database import engine
from app.models import AI_CONFIG_MODELS


def upgrade():
    with engine.begin() as connection:
        for model in AI_CONFIG_MODELS.values():
            model.__table__.create(bind=connection, checkfirst=True)
