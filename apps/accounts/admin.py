from django import forms
from django.contrib import admin, messages
from .models import Office, User, UserPreference
from . import services


class OfficeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status", "password_last_rotated", "id"]
    readonly_fields = ["shared_password_hash", "password_last_rotated"]
    actions = ["regenerate_password"]

    def save_model(self, request, obj, form, change):
        is_new = obj._state.adding
        super().save_model(request, obj, form, change)
        if is_new:
            raw_password = services.generate_office_password()
            services.set_office_password(office=obj, raw_password=raw_password, changed_by=request.user)
            self.message_user(
                request,
                f"Office password generated: {raw_password} — copy this now, it cannot be shown again.",
                level=messages.WARNING,
            )
    @admin.action(description="Regenerate password for selected office(s)")
    def regenerate_password(self, request, queryset):
        for office in queryset:
            raw_password = services.generate_office_password()
            services.set_office_password(office=office, raw_password=raw_password, changed_by=request.user)
            self.message_user(
                request,
                f"{office.name}: new password is {raw_password} — copy this now, it cannot be shown again.",
                level=messages.WARNING,
            )
    

admin.site.register(Office, OfficeAdmin)


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "office", "is_active"]
        # email, username, password intentionally excluded — generated automatically on save


class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ["email", "first_name", "last_name", "role", "office", "is_active"]
    readonly_fields = []

    def save_model(self, request, obj, form, change):
        is_new = obj._state.adding
        if is_new:
            if not obj.office:
                self.message_user(request, "A user must be assigned to an office.", level=messages.ERROR)
                return
            if not obj.office.shared_password_hash:
                self.message_user(
                    request,
                    f"{obj.office.name} has no password set yet — create/edit that office first.",
                    level=messages.ERROR,
                )
                return

            user = services.create_user(
                first_name=obj.first_name, last_name=obj.last_name,
                role=obj.role, office=obj.office, created_by=request.user,
            )
            self.message_user(
                request,
                f"User created with generated email: {user.email}",
                level=messages.SUCCESS,
            )
        else:
            super().save_model(request, obj, form, change)



admin.site.register(User, UserAdmin)
admin.site.register(UserPreference)