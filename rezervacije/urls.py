from django.urls import path
from . import views

urlpatterns = [
    path('', views.grid, name='grid'),
    path('rezerviraj/<int:igrisca_id>/<str:datum>/<str:ura>/', views.rezerviraj, name='rezerviraj'),
    path('preklic/<int:rezervacija_id>/', views.preklic, name='preklic'),
    path('moje/', views.moje_rezervacije, name='moje_rezervacije'),
    path('prijava/', views.prijava, name='prijava'),
    path('odjava/', views.odjava, name='odjava'),
    path('registracija/', views.registracija, name='registracija'),
    path('trener/', views.trener_panel, name='trener_panel'),
    path('trener/potrdi/<int:rezervacija_id>/', views.potrdi_trening, name='potrdi'),
    path('trener/zavrni/<int:rezervacija_id>/', views.zavrni_trening, name='zavrni'),
    path('cenik/', views.cenik, name='cenik'),
]
