import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'update-course-statistics-every-hour': {
        'task': 'lms.tasks.update_course_statistics',
        'schedule': crontab(minute=0, hour='*'),
    },
}
