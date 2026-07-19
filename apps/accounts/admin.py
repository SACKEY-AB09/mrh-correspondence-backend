from django.contrib import admin

# Register your models here.
from .models import Office, User, UserPreference

admin.site.register(Office)
admin.site.register(User)
admin.site.register(UserPreference)