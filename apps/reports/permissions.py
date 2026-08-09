from rest_framework.exceptions import PermissionDenied, ValidationError


def resolve_supervisor_office(request):
    if "office" in request.query_params or "office" in request.data:
        raise ValidationError({"office": "This parameter is not accepted. The report office is always your own assigned office."})

    if request.user.role != request.user.Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can access formal office reports.")

    office = request.user.office
    if office is None:
        raise ValidationError({"detail": "You are not assigned to an office and cannot access formal reports."})

    return office