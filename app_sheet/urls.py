from datetime import datetime

from django.urls import path
from django.contrib import admin
import django.contrib.auth.views

from . import views, forms

admin.autodiscover()

urlpatterns = [
    path('', views.home, name='home'),
    path('contact', views.contact, name='contact'),
    path('about', views.about, name='about'),
    path('markdown', views.markdown_view, name='markdown'),
    path('sheet/<int:sheet_id>$', views.sheet_edit, name='sheet'),
    path('login/$',
        django.contrib.auth.views.LoginView.as_view,
        {
            'template_name': 'login.html',
            'authentication_form': forms.BootstrapAuthenticationForm,
            'extra_context':
                {
                    'title': 'Log in',
                    'year': datetime.now().year,
                }
        },
        name='login'),
    path('^logout$',
        django.contrib.auth.views.LogoutView.as_view,
        {
            'next_page': '/',
        },
        name='logout'),
]