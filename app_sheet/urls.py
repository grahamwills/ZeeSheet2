from django.contrib import admin
from django.urls import path, include

from . import views

admin.autodiscover()

urlpatterns = [
    path('', views.home, name='home'),
    path('contact', views.contact, name='contact'),
    path('about', views.about, name='about'),
    path('sheet/<int:sheet_id>', views.show_sheet, name='sheet'),
    path('sheet/<int:sheet_id>/action', views.action_dispatcher, name='action_dispatcher'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
