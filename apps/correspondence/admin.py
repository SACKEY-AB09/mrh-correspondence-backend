from django.contrib import admin

# Register your models here.
from .models import Correspondence, CorrespondenceMovement, Attachment, Note

admin.site.register(Correspondence)
admin.site.register(CorrespondenceMovement)
admin.site.register(Attachment)
admin.site.register(Note)