from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    # path('registro/', views.registro_view, name='registro'), # Comentado temporalmente y despues recordar que temporalmente coloque un # en la ruta del documento index en las lineas 35-36- Duvan Timote
]