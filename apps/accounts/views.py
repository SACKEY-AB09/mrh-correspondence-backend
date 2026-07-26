from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Office, User
from .serializers import MyTokenObtainPairSerializer, UserSerializer, OfficeSerializer
from . import services


class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class CreateOfficeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Admin access required.")

        name = request.data.get("name")
        code = request.data.get("code")
        if not name or not code:
            raise ValidationError({"detail": "name and code are required."})

        office = Office.objects.create(name=name, code=code)
        return Response(OfficeSerializer(office).data, status=201)

class CreateUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Admin access required.")

        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        role = request.data.get("role", User.Role.OFFICE_USER)
        office_id = request.data.get("office")

        if not all([first_name, last_name, office_id]):
            raise ValidationError({"detail": "first_name, last_name, and office are required."})

        try:
            office = Office.objects.get(pk=office_id)
        except Office.DoesNotExist:
            raise ValidationError({"office": "Office not found."})

        user, raw_password = services.create_user(
            first_name=first_name, last_name=last_name, role=role, office=office, created_by=request.user
        )
        return Response({
            "user": UserSerializer(user).data,
            "generated_password": raw_password,
        }, status=201)

class RegenerateUserPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Admin access required.")

        user = generics.get_object_or_404(User, pk=pk)
        raw_password = services.regenerate_user_password(user=user, changed_by=request.user)
        return Response({"detail": f"Password reset for {user.email}.", "generated_password": raw_password})