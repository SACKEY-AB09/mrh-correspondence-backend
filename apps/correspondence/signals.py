import django.dispatch

correspondence_registered = django.dispatch.Signal()
correspondence_forwarded = django.dispatch.Signal()
correspondence_stage_updated = django.dispatch.Signal()
correspondence_completed = django.dispatch.Signal()
correspondence_filed = django.dispatch.Signal()