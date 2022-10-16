from django.conf import settings
from django.conf.urls.static import static
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
                  path('display/<str:file_name>', views.show_file, name='display'),

                  path('accounts/', include('django.contrib.auth.urls')),
                  path("register", views.register_request, name="register"),
                  path('sheet/<int:pk>/update/', views.SheetUpdate.as_view(), name='sheet-update'),
                  path('sheet/<int:pk>/delete/', views.SheetDelete.as_view(), name='sheet-delete'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
