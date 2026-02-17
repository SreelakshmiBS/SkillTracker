from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    # path('dashboard/', views.dashboard, name='dashboard'),
    path('login_view/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('profile/', views.profile, name='profile'),
]
