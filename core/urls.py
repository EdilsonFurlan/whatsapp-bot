
from django.contrib import admin
from django.urls import path
from whatsapp_server.views import webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path("webhook", webhook),  # URL pública para o WhatsApp
    path("webhook/", webhook),
]
