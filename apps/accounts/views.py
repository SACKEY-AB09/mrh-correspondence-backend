#from django.shortcuts import render
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import MyTokenObtainPairSerializer, UserSerializer
# Create your views here.

class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user