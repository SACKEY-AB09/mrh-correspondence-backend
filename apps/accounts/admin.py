from django import forms
from django.contrib import admin, messages
from .models import Office, User, UserPreference
from . import services


class OfficeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status", "id"]
    

admin.site.register(Office, OfficeAdmin)


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "office", "is_active"]
        # email, username, password intentionally excluded — generated automatically on save


class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ["email", "first_name", "last_name", "role", "office", "is_active"]
    actions = ["regenerate_password"]

    def save_model(self, request, obj, form, change):
        if obj._state.adding:
            if not obj.office:
                self.message_user(request, "A user must be assigned to an office.", level=messages.ERROR)
                return
            user, raw_password = services.create_user(
                first_name=obj.first_name, last_name=obj.last_name,
                role=obj.role, office=obj.office, created_by=request.user,
            )
            self.message_user(
                request,
                f"User created — email: {user.email}, password: {raw_password} (copy now, shown once)",
                level=messages.WARNING,
            )
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description="Regenerate password for selected user(s)")
    def regenerate_password(self, request, queryset):
        for user in queryset:
            raw_password = services.regenerate_user_password(user=user, changed_by=request.user)
            self.message_user(
                request,
                f"{user.email}: new password is {raw_password} — copy this now.",
                level=messages.WARNING,
            )


admin.site.register(User, UserAdmin)
admin.site.register(UserPreference)