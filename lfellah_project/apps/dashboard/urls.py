from django.urls import path
from . import views

app_name = 'dashboard'

# NOTE: Le dashboard IoT capteurs est servi publiquement par core.urls (sensor_dashboard).
# Cette route est retiree pour eviter un conflit d'URL qui forcait la connexion
# (@login_required) et empechait l'affichage des donnees capteurs en temps reel.
urlpatterns = [
    # path('dashboard-iot/', views.dashboard_page, name='dashboard-page'),
]