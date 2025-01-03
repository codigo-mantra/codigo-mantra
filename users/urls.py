from django.urls import path
from .views import (
    RegisterAPIView,
    LoginAPIView,
    UserView,
    LogoutView,
    TokenRefreshAPIView,
    TokenValidationView
)

urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
    path('login/', LoginAPIView.as_view()),
    path('user/', UserView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('refresh-token/', TokenRefreshAPIView.as_view()),
    path('validate-token/', TokenValidationView.as_view()),

]