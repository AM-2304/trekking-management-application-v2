"""Celery entry point.

Start the worker and the scheduler together with:

    celery -A celery_worker.celery worker --beat --loglevel=info

The worker runs in its own process, so it builds its own Flask application and hands
it to init_celery(), which wraps every task in an application context.
"""

from app import create_app
from app.tasks import celery, init_celery

app = create_app()
init_celery(app)
