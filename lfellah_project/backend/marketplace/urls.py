from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ─── ROUTEUR API REST (JSON, pour mobile / JS) ───────────────────
router = DefaultRouter()
router.register(r'categories', views.ProductCategoryViewSet, basename='categories')
router.register(r'products', views.ProductViewSet, basename='products')
router.register(r'orders', views.OrderViewSet, basename='orders')
router.register(r'promo-codes', views.PromoCodeViewSet, basename='promo-codes')

urlpatterns = [

    # ═══════════════════════════════════════════════════════════════
    #  ROUTES WEB (HTML Templates — Interface Utilisateur)
    # ═══════════════════════════════════════════════════════════════

    path('', views.marketplace_home, name='marketplace-home'),

    # Dashboard Vendeur (Fellah)
    path('vendeur/dashboard/', views.vendeur_dashboard_page, name='vendeur-dashboard-page'),
    path('vendeur/produits/', views.gestion_produits_page, name='gestion-produits'),
    path('vendeur/produits/ajouter/', views.ajouter_produit_page, name='ajouter-produit'),
    path('vendeur/produits/<int:product_id>/modifier/', views.modifier_produit_page, name='modifier-produit'),

    # Dashboard Marketeur
    path('marketing/', views.marketer_dashboard_page, name='marketer-dashboard-page'),

    # Flux d'achat B2B
    path('acheter/<int:product_id>/', views.acheter_produit_view, name='acheter-produit'),

    # Panier (Cart)
    path('panier/', views.panier_page, name='panier'),
    path('panier/ajouter/<int:product_id>/', views.ajouter_au_panier, name='ajouter-panier'),
    path('panier/supprimer/<int:item_id>/', views.supprimer_du_panier, name='supprimer-panier'),
    path('panier/update/<int:item_id>/', views.update_cart_quantity, name='update-panier'),
    path('panier/vider/', views.vider_panier, name='vider-panier'),
    path('panier/devis/', views.devis_panier, name='devis-panier'),
    path('panier/confirmer/', views.confirmer_panier, name='confirmer-panier'),

    # ═══════════════════════════════════════════════════════════════
    #  ROUTES API REST (JSON — pour Fetch / Mobile / ESP32)
    # ═══════════════════════════════════════════════════════════════

    path('api/marketplace/', include(router.urls)),
    path('api/marketplace/cart-count/', views.cart_count_api, name='cart-count'),
    path('api/orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('api/orders/<int:order_id>/status/', views.update_order_status, name='order-status'),
    path('api/orders/<int:order_id>/confirmer/', views.confirmer_commande, name='confirmer-commande'),
    path('api/orders/<int:order_id>/livrer/', views.confirmer_livraison, name='confirmer-livraison'),
    path('api/seller/dashboard/', views.seller_dashboard, name='seller-dashboard'),
    path('api/marketer/dashboard/', views.marketer_dashboard, name='marketer-dashboard'),

    # PromoCode CRUD (marketeur uniquement)
    path('api/marketer/promos/', views.promo_codes_list, name='promo-codes-list'),
    path('api/marketer/promos/create/', views.promo_code_create, name='promo-code-create'),
    path('api/marketer/promos/<int:promo_id>/delete/', views.promo_code_delete, name='promo-code-delete'),
]