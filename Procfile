web: gunicorn correspondence_gh.wsgi --log-file -
worker: celery -A correspondence_gh worker -l info
beat: celery -A correspondence_gh beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler