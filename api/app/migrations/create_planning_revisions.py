from app.helpers.database import engine
from app.models import PlanningRevision


def upgrade():
    PlanningRevision.__table__.create(bind=engine, checkfirst=True)
