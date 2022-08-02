from datetime import datetime

from django.urls import path, include
from django.contrib import admin

from . import views, forms

admin.autodiscover()

urlpatterns = [
    path('', views.home, name='home'),
    path('contact', views.contact, name='contact'),
    path('about', views.about, name='about'),
    path('sheet/<int:sheet_id>', views.show_sheet, name='sheet'),
    path('accounts/', include('django.contrib.auth.urls')),
]