from decimal import Decimal
from django.db import models as django_models, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import FileResponse, JsonResponse
from datetime import timedelta
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework import serializers as drf_serializers
import tempfile
import os

from .models import Product, ProductCategory, Order, OrderItem, PromoCode, CartItem
from .serializers import (
    ProductSerializer, ProductCategorySerializer, OrderSerializer,
    OrderCreateSerializer, OrderItemSerializer, OrderStatusSerializer,
)
from .permissions import IsSellerOrReadOnly, IsBuyerOrAdmin, IsOrderParticipant
from .tasks import process_order_workflow, generate_invoice_pdf_task

User = get_user_model()

# ─── GUARDES D'ACCES PAR ROLE ─────────────────────────────────────

def is_farmer(user):
    return user.is_authenticated and user.role == 'farmer'

def is_marketer(user):
    return user.is_authenticated and user.role == 'marketer'

def is_buyer(user):
    return user.is_authenticated and user.role == 'buyer'


# ─── CATEGORIES ────────────────────────────────────────────────────

class ProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.AllowAny]


# ─── PRODUCTS (Marketplace) ────────────────────────────────────────

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsSellerOrReadOnly]

    def get_queryset(self):
        qs = Product.objects.select_related('seller', 'category').filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        seller = self.request.query_params.get('seller')
        if seller:
            qs = qs.filter(seller_id=seller)
        is_organic = self.request.query_params.get('organic')
        if is_organic == 'true':
            qs = qs.filter(is_organic=True)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)


# ─── ORDERS ────────────────────────────────────────────────────────

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrderParticipant]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.select_related('buyer', 'seller').prefetch_related('items__product').order_by('-created_at')
        return Order.objects.select_related('buyer', 'seller').prefetch_related('items__product').filter(
            django_models.Q(buyer=user) | django_models.Q(seller=user)
        ).order_by('-created_at')


class OrderCreateView(generics.CreateAPIView):
    """
    Création d'une commande avec commission 12% intégrée.
    Endpoint : POST /api/orders/create/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderCreateSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        seller = get_object_or_404(User, id=data['seller_id'], role='farmer', is_blocked=False)

        # Vérifier le code promo si fourni
        promo_code = None
        promo_code_str = request.data.get('promo_code')
        if promo_code_str:
            promo_code = PromoCode.objects.filter(code=promo_code_str.upper(), is_active=True).first()
            if not promo_code or not promo_code.is_valid:
                return Response({'error': 'Code promo invalide ou expiré.'}, status=400)

        order = Order.objects.create(
            buyer=request.user,
            seller=seller,
            shipping_address=data['shipping_address'],
            notes=data.get('notes', ''),
            commission_rate=Decimal('0.12'),
            promo_code=promo_code,
        )

        for item_data in data['items']:
            product = get_object_or_404(Product, id=item_data['product_id'], is_active=True, seller=seller)
            quantity = Decimal(str(item_data['quantity']))

            # --- CALCUL COMMISSION 12% NATIF BDD ---
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price_base=product.price_base,
                commission_rate=Decimal('0.12'),
            )

        order.refresh_from_db()

        # Appliquer la remise du code promo
        if promo_code:
            order.discount_amount = promo_code.calculate_discount(order.total_ht)
            promo_code.used_count = django_models.F('used_count') + 1
            promo_code.save(update_fields=['used_count'])
            order.save(update_fields=['discount_amount'])

        # Déclencher le workflow asynchrone : facture PDF + email automatique
        process_order_workflow.delay(order.id)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """
    Workflow de validation :
    pending -> confirmed -> preparing -> shipped -> delivered
    POST /api/orders/{id}/status/
    {"status": "shipped"}
    """
    order = get_object_or_404(Order, id=order_id)

    # Seuls le vendeur et l'admin peuvent changer le statut
    if request.user.role not in ('admin', 'farmer') or (request.user.role == 'farmer' and order.seller != request.user):
        return Response({'error': 'Permission refusée.'}, status=403)

    serializer = OrderStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_status = serializer.validated_data['status']
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    return Response({'status': 'success', 'order_status': order.get_status_display()})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@user_passes_test(is_farmer, login_url='/', redirect_field_name=None)
def confirmer_commande(request, order_id):
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    if order.status != 'pending':
        return Response({'error': f'Impossible de confirmer une commande de statut {order.status}.'}, status=400)

    order.status = 'confirmed'
    order.save(update_fields=['status', 'updated_at'])

    # Email automatique au client avec log d'erreur
    try:
        from django.core.mail import send_mail
        from django.conf import settings as s
        sent = send_mail(
            subject=f"L'Fellah - Commande N {order.id} en preparation",
            message=(
                f"Bonjour,\n\n"
                f"Votre commande N {order.id} est confirmee et en cours de preparation.\n\n"
                f"Produits : {order.items.count()} article(s)\n"
                f"Total TTC : {order.total_final:.2f} MAD\n"
                f"Livraison : {order.shipping_address[:80]}\n\n"
                f"Cordialement,\nL'equipe L'Fellah 2.0"
            ),
            from_email=s.DEFAULT_FROM_EMAIL,
            recipient_list=[order.buyer.email],
            fail_silently=False,
        )
        print(f"[EMAIL] Commande #{order.id} : email envoye a {order.buyer.email} (envoyes: {sent})")
        if sent == 0:
            print(f"[EMAIL] ERREUR: Aucun email envoye. Verifiez EMAIL_BACKEND et SMTP dans settings.")
    except Exception as email_err:
        print(f"[EMAIL] ECHEC envoi commande #{order.id}: {email_err}")

    return Response({'status': 'confirmed', 'order_status': order.get_status_display()})


# ─── CONFIRMER LIVRAISON (VENDEUR) ────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirmer_livraison(request, order_id):
    """Le vendeur confirme la livraison -> statut 'delivered' + calcul financier."""
    order = get_object_or_404(Order, id=order_id, seller=request.user)
    if order.status not in ('shipped', 'confirmed'):
        return Response({'error': f'Livraison impossible depuis le statut {order.status}.'}, status=400)

    order.status = 'delivered'
    order.is_paid = True
    order.save(update_fields=['status', 'is_paid', 'updated_at'])

    # Calcul financier : montant net reverse au vendeur
    net_vendeur = order.total_base  # Prix vendeur HT (commission deja deduite)
    commission_lfellah = order.total_commission

    return Response({
        'status': 'success',
        'order_status': order.get_status_display(),
        'finance': {
            'net_vendeur': f'{net_vendeur:.2f} MAD',
            'commission_lfellah': f'{commission_lfellah:.2f} MAD',
            'total_facture_client': f'{order.total_final:.2f} MAD',
        },
        'message': f'Commande #{order.id} livree. Montant net vendeur : {net_vendeur:.2f} MAD.',
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def seller_dashboard(request):
    """Dashboard vendeur: stats, stock, commandes récentes"""
    user = request.user
    if user.role != 'farmer':
        return Response({'error': 'Accès réservé aux vendeurs.'}, status=403)

    products = Product.objects.filter(seller=user, is_active=True)
    orders = Order.objects.filter(seller=user).order_by('-created_at')[:20]

    total_revenue = sum(
        (o.total_base for o in Order.objects.filter(seller=user, status='delivered')),
        Decimal('0.00'),
    )
    total_commission_paid = sum(
        (o.total_commission for o in Order.objects.filter(seller=user, status='delivered')),
        Decimal('0.00'),
    )

    return Response({
        'products_count': products.count(),
        'products': ProductSerializer(products, many=True).data,
        'recent_orders': OrderSerializer(orders, many=True).data,
        'total_revenue_ht': str(total_revenue),
        'total_commission_paid': str(total_commission_paid),
        'total_revenue_net': str(total_revenue - total_commission_paid),
    })


# ─── VENDEUR DASHBOARD HTML ───────────────────────────────────

@login_required
@user_passes_test(is_farmer, login_url='/', redirect_field_name=None)
def vendeur_dashboard_page(request):
    return render(request, 'marketplace/vendeur_dashboard.html', {
        'user': request.user,
    })


# ─── GESTION PRODUITS (HTML CRUD) ──────────────────────────────

@login_required
@user_passes_test(is_farmer, login_url='/', redirect_field_name=None)
def gestion_produits_page(request):
    return render(request, 'marketplace/gestion_produits.html', {
        'user': request.user,
    })


@login_required
@user_passes_test(is_farmer, login_url='/', redirect_field_name=None)
def ajouter_produit_page(request):
    categories = ProductCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price', '0').replace(',', '.')
        unit = request.POST.get('unit', 'kg')
        stock = request.POST.get('stock', '0').replace(',', '.')
        is_organic = request.POST.get('organic') == 'on'
        image = request.FILES.get('image')

        if not name:
            return render(request, 'marketplace/ajouter_produit.html', {
                'categories': categories, 'error': 'Nom du produit requis.',
                'form': request.POST,
            })

        try:
            price_d = Decimal(price)
            stock_d = Decimal(stock)
            if price_d <= 0 or stock_d < 0:
                raise ValueError
        except Exception:
            return render(request, 'marketplace/ajouter_produit.html', {
                'categories': categories, 'error': 'Prix ou stock invalide.',
                'form': request.POST,
            })

        category = ProductCategory.objects.filter(id=category_id).first() if category_id else None

        Product.objects.create(
            seller=request.user,
            name=name, name_fr=name,
            description=description,
            category=category,
            price_base=price_d,
            unit=unit,
            stock_quantity=stock_d,
            is_organic=is_organic,
            image=image,
        )
        return redirect('/vendeur/produits/')

    return render(request, 'marketplace/ajouter_produit.html', {
        'categories': categories,
    })


@login_required
@user_passes_test(is_farmer, login_url='/', redirect_field_name=None)
def modifier_produit_page(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    categories = ProductCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        product.name = request.POST.get('name', product.name).strip()
        product.name_fr = product.name
        product.description = request.POST.get('description', product.description).strip()
        category_id = request.POST.get('category')
        product.category = ProductCategory.objects.filter(id=category_id).first() if category_id else product.category
        product.is_organic = request.POST.get('organic') == 'on'

        price = request.POST.get('price', str(product.price_base)).replace(',', '.')
        stock = request.POST.get('stock', str(product.stock_quantity)).replace(',', '.')
        try:
            product.price_base = Decimal(price)
            product.stock_quantity = Decimal(stock)
        except Exception:
            pass

        product.unit = request.POST.get('unit', product.unit)
        image = request.FILES.get('image')
        if image:
            product.image = image
        product.save()
        return redirect('/vendeur/produits/')

    return render(request, 'marketplace/modifier_produit.html', {
        'product': product,
        'categories': categories,
    })


# ─── LANDING PAGE (PUBLIC) ──────────────────────────────────────────

def marketplace_home(request):
    qs = Product.objects.select_related('seller', 'category').filter(is_active=True)
    cat_id = request.GET.get('category')
    if cat_id and cat_id.isdigit():
        qs = qs.filter(category__id=int(cat_id))
    products = qs.order_by('-created_at')[:50]
    categories = ProductCategory.objects.filter(is_active=True)
    cart_count = 0
    if request.user.is_authenticated and request.user.role == 'buyer':
        cart_count = CartItem.objects.filter(user=request.user).count()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories,
        'cart_count': cart_count,
    })


# ─── DASHBOARD MARKETEUR (HTML) ──────────────────────────────────

@login_required
@user_passes_test(is_marketer, login_url='/', redirect_field_name=None)
def marketer_dashboard_page(request):
    return render(request, 'marketplace/marketer_dashboard.html')


# ─── GESTION CODES PROMO (MARKETEUR) ────────────────────────────

@login_required
def promo_codes_list(request):
    if request.user.role != 'marketer':
        return JsonResponse({'success': False, 'message': 'Acces refuse.'}, status=403)
    promos = PromoCode.objects.all().order_by('-created_at')
    data = [{
        'id': p.id, 'code': p.code, 'discount_type': p.discount_type,
        'discount_value': str(p.discount_value),
        'max_uses': p.max_uses, 'used_count': p.used_count,
        'is_active': p.is_active, 'is_valid': p.is_valid,
        'valid_from': p.valid_from.isoformat() if p.valid_from else None,
        'valid_until': p.valid_until.isoformat() if p.valid_until else None,
        'created_at': p.created_at.isoformat(),
    } for p in promos]
    return JsonResponse({'success': True, 'promos': data})


@login_required
def promo_code_create(request):
    if request.user.role != 'marketer':
        return JsonResponse({'success': False, 'message': 'Acces refuse.'}, status=403)
    code = request.POST.get('code', '').strip().upper()
    discount_type = request.POST.get('discount_type', 'percentage')
    discount_value = request.POST.get('discount_value', '10').replace(',', '.')
    max_uses = request.POST.get('max_uses', '100')

    if not code or len(code) < 3:
        return JsonResponse({'success': False, 'message': 'Code requis (min 3 caracteres).'}, status=400)
    if PromoCode.objects.filter(code=code).exists():
        return JsonResponse({'success': False, 'message': 'Ce code existe deja.'}, status=400)

    try:
        PromoCode.objects.create(
            code=code,
            discount_type=discount_type,
            discount_value=Decimal(discount_value),
            max_uses=int(max_uses),
            created_by=request.user,
        )
        return JsonResponse({'success': True, 'message': f'Code {code} cree avec succes.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def promo_code_delete(request, promo_id):
    if request.user.role != 'marketer':
        return JsonResponse({'success': False, 'message': 'Acces refuse.'}, status=403)
    PromoCode.objects.filter(id=promo_id).delete()
    return JsonResponse({'success': True})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def marketer_dashboard(request):
    """
    Dashboard Marketeur (lecture seule) :
    - KPIs : inscriptions, volume des ventes, commandes en cours.
    - Gestion des codes promo (CRUD via API).
    Accès : marketer, admin.
    """
    if request.user.role not in ('marketer', 'admin'):
        return Response({'error': 'Accès réservé à l\'équipe Marketing.'}, status=403)

    total_users = User.objects.count()
    total_farmers = User.objects.filter(role='farmer').count()
    total_buyers = User.objects.filter(role='buyer').count()
    new_users_this_week = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7)
    ).count()

    total_orders = Order.objects.count()
    orders_this_month = Order.objects.filter(created_at__month=timezone.now().month).count()
    total_sales_volume = sum(
        (o.total_ht for o in Order.objects.filter(status__in=['delivered', 'shipped'])),
        Decimal('0.00'),
    )
    total_commission_earned = sum(
        (o.total_commission for o in Order.objects.filter(status__in=['delivered', 'shipped'])),
        Decimal('0.00'),
    )

    active_promo_codes = PromoCode.objects.filter(is_active=True).count()
    recent_orders = Order.objects.select_related('buyer', 'seller').order_by('-created_at')[:10]

    return Response({
        'kpi': {
            'total_utilisateurs': total_users,
            'fermiers': total_farmers,
            'acheteurs': total_buyers,
            'nouveaux_cette_semaine': new_users_this_week,
            'commandes_totales': total_orders,
            'commandes_ce_mois': orders_this_month,
            'volume_ventes_ttc': str(total_sales_volume),
            'commission_totale': str(total_commission_earned),
            'codes_promo_actifs': active_promo_codes,
        },
        'commandes_recentes': OrderSerializer(recent_orders, many=True).data,
    })


# ─── PANIER (CART) ───────────────────────────────────────────────

def cart_count_api(request):
    """Endpoint AJAX pour le badge panier dans le header."""
    count = 0
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})


@login_required
def panier_page(request):
    items = CartItem.objects.select_related('product__seller', 'product__category').filter(user=request.user)
    total_ht = sum((item.total_ht for item in items), Decimal('0.00'))
    promo = request.GET.get('promo', '').strip().upper()
    discount = Decimal('0.00')
    promo_obj = None
    if promo:
        promo_obj = PromoCode.objects.filter(code=promo, is_active=True).first()
        if promo_obj and promo_obj.is_valid and total_ht >= promo_obj.min_order_amount:
            discount = promo_obj.calculate_discount(total_ht)
    total_avec_remise = total_ht - discount
    return render(request, 'marketplace/panier.html', {
        'items': items, 'total_ht': total_ht, 'total_ht_net': total_avec_remise,
        'promo_code': promo_obj, 'discount': discount,
    })


@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def ajouter_au_panier(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    qte = Decimal(request.POST.get('quantite', '1').replace(',', '.'))
    if qte <= 0:
        qte = Decimal('1')

    # Validation stock
    product.refresh_from_db()
    if qte > product.stock_quantity:
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'message': f'Stock insuffisant. Disponible : {product.stock_quantity} {product.get_unit_display()}.'
        }, status=400)

    item, created = CartItem.objects.get_or_create(
        user=request.user, product=product,
        defaults={'quantity': min(qte, product.stock_quantity)}
    )
    if not created:
        new_qty = item.quantity + qte
        if new_qty > product.stock_quantity:
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': f'Stock insuffisant. Vous avez deja {item.quantity} {product.get_unit_display()} dans le panier (max: {product.stock_quantity}).'
            }, status=400)
        item.quantity = new_qty
        item.save(update_fields=['quantity'])

    cart_count = CartItem.objects.filter(user=request.user).count()

    # AJAX : retour JSON pour mise a jour dynamique du compteur
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({'success': True, 'cart_count': cart_count, 'product_name': product.name})

    return redirect('/panier/')


@login_required
def supprimer_du_panier(request, item_id):
    CartItem.objects.filter(id=item_id, user=request.user).delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        items = CartItem.objects.select_related('product').filter(user=request.user)
        total = sum((i.total_ht for i in items), Decimal('0.00'))
        return JsonResponse({'success': True, 'cart_count': items.count(), 'total_ht': str(total)})

    return redirect('/panier/')


@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def update_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    action = request.POST.get('action', '')  # 'increase', 'decrease' ou 'set'

    if action == 'increase':
        item.quantity = min(item.quantity + Decimal('1'), item.product.stock_quantity)
    elif action == 'decrease':
        item.quantity = max(item.quantity - Decimal('1'), Decimal('1'))
    elif action == 'set':
        qte = Decimal(request.POST.get('quantite', '1').replace(',', '.'))
        item.quantity = max(min(qte, item.product.stock_quantity), Decimal('1'))
    else:
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'error': 'Action invalide'})

    item.save(update_fields=['quantity'])

    # Recalculer les totaux
    items = CartItem.objects.select_related('product').filter(user=request.user)
    total_ht = sum((i.total_ht for i in items), Decimal('0.00'))
    cart_count = items.count()

    from django.http import JsonResponse
    return JsonResponse({
        'success': True,
        'cart_count': cart_count,
        'item_total': str(item.total_ht),
        'item_quantity': str(item.quantity),
        'total_ht': str(total_ht),
    })


@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def vider_panier(request):
    CartItem.objects.filter(user=request.user).delete()
    return redirect('/panier/')


@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def devis_panier(request):
    """Génère un PDF devis du panier SANS créer de commande."""
    items = CartItem.objects.select_related('product__seller', 'product__category').filter(user=request.user)
    if not items:
        return redirect('/panier/')

    adresse = request.POST.get('adresse', '').strip()
    promo_str = request.POST.get('promo_code', '').strip().upper()

    total_ht = sum((Decimal(str(item.total_ht)) for item in items), Decimal('0.00'))
    promo_obj = None
    discount = Decimal('0.00')
    if promo_str:
        promo_obj = PromoCode.objects.filter(code=promo_str, is_active=True).first()
        if promo_obj and promo_obj.is_valid and total_ht >= promo_obj.min_order_amount:
            discount = promo_obj.calculate_discount(total_ht)

    from django.template.loader import render_to_string
    from django.conf import settings as s
    from types import SimpleNamespace
    import tempfile

    societe = getattr(s, 'LF_SOCIETE', {})
    tva_rate = Decimal('0.20')
    tva_pct = 20

    devis_items = []
    total_tva = Decimal('0.00')
    for ci in items:
        p = ci.product
        up = p.price_final_display
        lt = (up * ci.quantity).quantize(Decimal('0.01'))
        ltva = (lt * tva_rate).quantize(Decimal('0.01'))
        devis_items.append(SimpleNamespace(
            product=SimpleNamespace(name=p.name, unit=p.unit),
            quantity=ci.quantity,
            unit_price_final=up,
            total_final=lt,
            total_tva=ltva,
        ))
        total_tva += ltva

    total_ttc = (total_ht - discount + total_tva).quantize(Decimal('0.01'))

    fake_order = SimpleNamespace(
        id=0,
        buyer=SimpleNamespace(email=request.user.email),
        shipping_address=adresse or 'À confirmer',
        discount_amount=discount,
        promo_code=SimpleNamespace(code=promo_obj.code if promo_obj else ''),
        get_status_display=lambda: 'Devis',
    )

    ctx = {
        'order': fake_order, 'items': devis_items,
        'total_ht': total_ht, 'total_tva': total_tva,
        'total_ttc': total_ttc, 'tva_rate_pct': tva_pct,
        'societe': societe, 'date_emission': timezone.now(),
    }

    try:
        from weasyprint import HTML
        from pathlib import Path
        html_str = render_to_string('marketplace/invoice_panier_pdf.html', ctx)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        base_url = Path(s.MEDIA_ROOT).as_uri() + '/'
        HTML(string=html_str, base_url=base_url).write_pdf(tmp.name)
        resp = FileResponse(open(tmp.name, 'rb'), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="Devis_LFellah.pdf"'
        return resp
    except Exception as e:
        print(f'[PDF Devis] WeasyPrint échoue ({e}), fallback ReportLab...')

    return _devis_panier_reportlab(ctx)


def _devis_panier_reportlab(ctx):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from django.conf import settings as s
    import os, tempfile

    items = ctx['items']
    societe = ctx['societe']
    tva_pct = ctx['tva_rate_pct']

    filename = 'devis_panier.pdf'
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_path = tmp.name

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    m = 2 * cm
    LF_DARK, LF_GREEN, LF_BG, LF_GRAY, LF_ACCENT, LF_AMBER = '#1b4332', '#2d6a4f', '#f0fdf4', '#6b7280', '#95d5b2', '#d97706'

    c.setFillColor(colors.HexColor(LF_DARK))
    c.rect(0, h - 2.5*cm, w, 2.5*cm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(m, h - 1.5*cm, "L'FELLAH 2.0 - DEVIS")
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.HexColor(LF_ACCENT))
    sy = h - 1.2*cm
    for ligne in [f"ICE: {societe.get('ice','')} | RC: {societe.get('rc','')} | IF: {societe.get('if_','')}",
                  f"Patente: {societe.get('patente','')} | CNSS: {societe.get('cnss','')}"]:
        c.drawString(11*cm, sy, ligne); sy -= 0.3*cm

    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(m, h - 3.3*cm, 'DEVIS')
    c.setFillColor(colors.HexColor(LF_GRAY))
    c.setFont('Helvetica', 7)
    order = ctx['order']
    c.drawString(m, h - 3.9*cm, f"Date: {ctx['date_emission'].strftime('%d/%m/%Y')} | Client: {order.buyer.email} | Livraison: {order.shipping_address[:40]}")

    yt = h - 4.8*cm
    c.setFillColor(colors.HexColor(LF_BG))
    c.rect(m-0.2*cm, yt-0.5*cm, w-2*m+0.4*cm, 0.7*cm, fill=True, stroke=False)
    c.setFillColor(colors.HexColor(LF_DARK))
    c.setFont('Helvetica-Bold', 7)
    for label, x in [('PRODUIT', m), ('QTE', 7*cm), ('P.U. HT', 10*cm), ('TOTAL HT', 13*cm), (f'TVA {tva_pct}%', 15.5*cm)]:
        c.drawString(x, yt, label)

    y = yt - 0.7*cm
    for i, item in enumerate(items):
        if i % 2 == 0:
            c.setFillColor(colors.HexColor(LF_BG))
            c.rect(m-0.2*cm, y-0.25*cm, w-2*m+0.4*cm, 0.55*cm, fill=True, stroke=False)
        c.setFillColor(colors.black); c.setFont('Helvetica', 7)
        c.drawString(m, y, item.product.name[:32])
        c.drawString(7*cm, y, f'{item.quantity} {item.product.unit}')
        c.drawString(10*cm, y, f'{item.unit_price_final:.2f}')
        c.setFont('Helvetica-Bold', 7)
        c.drawString(13*cm, y, f'{item.total_final:.2f}')
        c.setFillColor(colors.HexColor(LF_AMBER))
        c.drawString(15.5*cm, y, f'{item.total_tva:.2f}')
        y -= 0.55*cm

    y -= 0.5*cm
    rxl, rxv = 12*cm, 15.5*cm
    for label, val, col in [('TOTAL HT', f"{ctx['total_ht']:.2f} MAD", colors.black),
                              (f'TVA {tva_pct}%', f"{ctx['total_tva']:.2f} MAD", colors.HexColor(LF_AMBER))]:
        c.setFont('Helvetica', 8); c.setFillColor(colors.HexColor(LF_GRAY)); c.drawString(rxl, y, label+' :')
        c.setFillColor(col); c.drawString(rxv, y, val); y -= 0.5*cm

    if order.discount_amount > 0:
        c.setFillColor(colors.HexColor(LF_GRAY)); c.drawString(rxl, y, 'REMISE :')
        c.setFillColor(colors.HexColor('#e53e3e')); c.drawString(rxv, y, f"-{order.discount_amount:.2f} MAD"); y -= 0.5*cm

    y -= 0.2*cm
    c.setStrokeColor(colors.HexColor(LF_DARK)); c.setLineWidth(1.5); c.line(rxl, y, w-m, y)
    y -= 0.6*cm
    c.setFont('Helvetica-Bold', 10); c.setFillColor(colors.HexColor(LF_DARK))
    c.drawString(rxl, y, 'TOTAL TTC :'); c.drawString(rxv, y, f"{ctx['total_ttc']:.2f} MAD")

    c.setFillColor(colors.HexColor(LF_GRAY)); c.setFont('Helvetica', 5)
    py = 1.8*cm
    raison = societe.get('raison_sociale', "L'FELLAH SARL")
    for ligne in [f"{raison} | ICE:{societe.get('ice','')} | RC:{societe.get('rc','')} | IF:{societe.get('if_','')} | Patente:{societe.get('patente','')}",
                  f"Devis genere le {ctx['date_emission'].strftime('%d/%m/%Y')}"]:
        c.drawString(m, py, ligne); py -= 0.3*cm

    c.setFillColor(colors.HexColor(LF_GREEN)); c.rect(0, 0, w, 0.2*cm, fill=True, stroke=False)
    c.save()
    resp = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="Devis_LFellah.pdf"'
    return resp


@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def confirmer_panier(request):
    items = CartItem.objects.select_related('product__seller').filter(user=request.user)
    if not items:
        return redirect('/panier/')

    adresse = request.POST.get('adresse', '').strip()
    if not adresse:
        return render(request, 'marketplace/panier.html', {
            'items': items, 'error': 'Adresse de livraison requise.',
            'total_ht': sum((i.total_ht for i in items), Decimal('0.00')),
        })

    promo_str = request.POST.get('promo_code', '').strip().upper()
    promo_obj = None
    if promo_str:
        promo_obj = PromoCode.objects.filter(code=promo_str, is_active=True).first()
        if not promo_obj or not promo_obj.is_valid:
            return render(request, 'marketplace/panier.html', {
                'items': items, 'error': 'Code promo invalide ou expire.',
'total_ht': sum((i.total_ht for i in items), Decimal('0.00')),
            })

    with transaction.atomic():
        order = Order.objects.create(
            buyer=request.user,
            seller=items[0].product.seller,
            shipping_address=adresse,
            status='pending',
            commission_rate=Decimal('0.12'),
            promo_code=promo_obj,
        )
        for ci in items:
            p = ci.product
            p.stock_quantity = F('stock_quantity') - ci.quantity
            p.save(update_fields=['stock_quantity'])
            OrderItem.objects.create(
                order=order, product=p, quantity=ci.quantity,
                unit_price_base=p.price_base, commission_rate=Decimal('0.12'),
            )

        items.delete()

    order.refresh_from_db()
    if promo_obj:
        order.discount_amount = promo_obj.calculate_discount(order.total_ht)
        promo_obj.used_count = F('used_count') + 1
        promo_obj.save(update_fields=['used_count'])
        order.save(update_fields=['discount_amount'])

    try:
        process_order_workflow.delay(order.id)
    except Exception:
        pass

    return _generer_facture_panier(order, request)


# ─── GENERATION PDF PANIER (DEVIS MULTI-PRODUITS) ─────────────────

def _generer_facture_panier(order, request):
    """Genere un PDF recapitulatif (devis) pour tous les produits du panier."""
    from django.template.loader import render_to_string
    from django.conf import settings as s
    import tempfile

    societe = getattr(s, 'LF_SOCIETE', {})
    items = order.items.select_related('product').all()
    total_ht = order.total_ht
    total_tva = order.total_tva
    total_ttc = order.total_final
    tva_pct = int(order.tva_rate * 100)

    ctx = {
        'order': order, 'items': items,
        'total_ht': total_ht, 'total_tva': total_tva,
        'total_ttc': total_ttc, 'tva_rate_pct': tva_pct,
        'societe': societe, 'date_emission': timezone.now(),
    }

    try:
        from weasyprint import HTML
        from pathlib import Path
        html_str = render_to_string('marketplace/invoice_panier_pdf.html', ctx)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        base_url = Path(s.MEDIA_ROOT).as_uri() + '/'
        HTML(string=html_str, base_url=base_url).write_pdf(tmp.name)
        resp = FileResponse(open(tmp.name, 'rb'), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="Devis_LFellah_{order.id}.pdf"'
        return resp
    except Exception as e:
        print(f"[PDF Panier] WeasyPrint echoue ({e}), fallback ReportLab...")

    return _generer_facture_panier_reportlab(order, ctx)


def _generer_facture_panier_reportlab(order, ctx):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from django.conf import settings as s

    societe = ctx['societe']
    items = ctx['items']
    tva_pct = ctx['tva_rate_pct']

    filename = f"devis_panier_{order.id}.pdf"
    pdf_dir = os.path.join(s.MEDIA_ROOT, 'invoices')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    m = 2 * cm
    LF_DARK, LF_GREEN, LF_BG, LF_GRAY, LF_ACCENT = '#1b4332', '#2d6a4f', '#f0fdf4', '#6b7280', '#95d5b2'

    c.setFillColor(colors.HexColor(LF_DARK))
    c.rect(0, h - 2.5*cm, w, 2.5*cm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(m, h - 1.5*cm, "L'FELLAH 2.0 - DEVIS")
    c.setFont("Helvetica", 6)
    c.setFillColor(colors.HexColor(LF_ACCENT))
    sx, sy = 11*cm, h - 1.2*cm
    for ligne in [f"ICE: {societe.get('ice','')} | RC: {societe.get('rc','')} | IF: {societe.get('if_','')}",
                  f"Patente: {societe.get('patente','')} | CNSS: {societe.get('cnss','')}"]:
        c.drawString(sx, sy, ligne); sy -= 0.3*cm

    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(m, h - 3.3*cm, f"DEVIS N {order.id}")
    c.setFillColor(colors.HexColor(LF_GRAY))
    c.setFont("Helvetica", 7)
    c.drawString(m, h - 3.9*cm, f"Date: {ctx['date_emission'].strftime('%d/%m/%Y')} | Client: {order.buyer.email} | Livraison: {order.shipping_address[:40]}")

    yt = h - 4.8*cm
    c.setFillColor(colors.HexColor(LF_BG))
    c.rect(m-0.2*cm, yt-0.5*cm, w-2*m+0.4*cm, 0.7*cm, fill=True, stroke=False)
    c.setFillColor(colors.HexColor(LF_DARK))
    c.setFont("Helvetica-Bold", 7)
    for label, x in [("PRODUIT", m), ("QTE", 7*cm), ("P.U. HT", 10*cm), ("TOTAL HT", 13*cm), (f"TVA {tva_pct}%", 15.5*cm)]:
        c.drawString(x, yt, label)

    y = yt - 0.7*cm
    c.setStrokeColor(colors.HexColor(LF_GREEN)); c.setLineWidth(0.5); c.line(m, y, w-m, y)

    y -= 0.5*cm
    for i, item in enumerate(items):
        if i % 2 == 0:
            c.setFillColor(colors.HexColor(LF_BG))
            c.rect(m-0.2*cm, y-0.25*cm, w-2*m+0.4*cm, 0.55*cm, fill=True, stroke=False)
        c.setFillColor(colors.black); c.setFont("Helvetica", 7)
        c.drawString(m, y, item.product.name[:32])
        c.drawString(7*cm, y, f"{item.quantity} {item.product.unit}")
        c.drawString(10*cm, y, f"{item.unit_price_final:.2f}")
        c.setFont("Helvetica-Bold", 7)
        c.drawString(13*cm, y, f"{item.total_final:.2f}")
        c.setFillColor(colors.HexColor('#d97706'))
        l_tva = (item.total_final * order.tva_rate).quantize(Decimal('0.01'))
        c.drawString(15.5*cm, y, f"{l_tva:.2f}")
        y -= 0.55*cm

    y -= 0.5*cm
    c.setStrokeColor(colors.HexColor(LF_ACCENT)); c.setLineWidth(1); c.line(m, y+0.3*cm, w-m, y+0.3*cm)
    rxl, rxv = 12*cm, 15.5*cm
    for label, val, col in [("TOTAL HT", f"{ctx['total_ht']:.2f} MAD", colors.black),
                              (f"TVA {tva_pct}%", f"{ctx['total_tva']:.2f} MAD", colors.HexColor('#d97706'))]:
        c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor(LF_GRAY)); c.drawString(rxl, y, label+" :")
        c.setFillColor(col); c.drawString(rxv, y, val); y -= 0.5*cm

    if order.discount_amount > 0:
        c.setFillColor(colors.HexColor(LF_GRAY)); c.drawString(rxl, y, "REMISE :")
        c.setFillColor(colors.HexColor('#e53e3e')); c.drawString(rxv, y, f"-{order.discount_amount:.2f} MAD"); y -= 0.5*cm

    y -= 0.2*cm
    c.setStrokeColor(colors.HexColor(LF_DARK)); c.setLineWidth(1.5); c.line(rxl, y, w-m, y)
    y -= 0.6*cm
    c.setFont("Helvetica-Bold", 10); c.setFillColor(colors.HexColor(LF_DARK))
    c.drawString(rxl, y, "TOTAL TTC :"); c.drawString(rxv, y, f"{ctx['total_ttc']:.2f} MAD")

    c.setFillColor(colors.HexColor(LF_GRAY)); c.setFont("Helvetica", 5)
    py = 1.8*cm
    raison = societe.get('raison_sociale', "L'FELLAH SARL")
    ice = societe.get('ice', '')
    rc = societe.get('rc', '')
    if_ = societe.get('if_', '')
    patente = societe.get('patente', '')
    for ligne in [f"{raison} | ICE:{ice} | RC:{rc} | IF:{if_} | Patente:{patente}",
                  f"Devis genere le {ctx['date_emission'].strftime('%d/%m/%Y')} - N {order.id}"]:
        c.drawString(m, py, ligne); py -= 0.3*cm

    c.setFillColor(colors.HexColor(LF_GREEN)); c.rect(0, 0, w, 0.2*cm, fill=True, stroke=False)
    c.save()
    resp = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="Devis_LFellah_{order.id}.pdf"'
    return resp

@login_required
@user_passes_test(is_buyer, login_url='/', redirect_field_name=None)
def acheter_produit_view(request, product_id):
    """
    Vue complète du flux d'achat marketplace.
    GET  : Affiche le formulaire d'achat (produit, quantité, adresse, code promo).
    POST : Crée la commande, décrémente le stock, génère la facture PDF.
           Retourne le PDF en téléchargement immédiat (FileResponse).

    URL : /marketplace/acheter/<int:product_id>/
    """
    product = get_object_or_404(Product.objects.select_related('seller', 'category'),
                                id=product_id, is_active=True)

    if request.method == 'GET':
        return render(request, 'marketplace/acheter.html', {
            'product': product,
            'user': request.user,
        })

    if request.method == 'POST':
        quantite_str = request.POST.get('quantite', '1')
        adresse = request.POST.get('adresse', '').strip()
        promo_str = request.POST.get('promo_code', '').strip().upper()

        if not adresse:
            return render(request, 'marketplace/acheter.html', {
                'product': product, 'user': request.user,
                'error': 'Adresse de livraison requise.'
            })

        try:
            quantite = Decimal(quantite_str.replace(',', '.'))
            if quantite <= 0:
                raise ValueError
        except Exception:
            return render(request, 'marketplace/acheter.html', {
                'product': product, 'user': request.user,
                'error': 'Quantité invalide.'
            })

        if product.seller == request.user:
            return render(request, 'marketplace/acheter.html', {
                'product': product, 'user': request.user,
                'error': 'Vous ne pouvez pas acheter votre propre produit.'
            })

        product.refresh_from_db()
        if product.stock_quantity < quantite:
            return render(request, 'marketplace/acheter.html', {
                'product': product, 'user': request.user,
                'error': f'Stock insuffisant. Disponible : {product.stock_quantity} {product.get_unit_display()}.'
            })

        promo_code = None
        if promo_str:
            promo_code = PromoCode.objects.filter(code=promo_str, is_active=True).first()
            if not promo_code or not promo_code.is_valid:
                return render(request, 'marketplace/acheter.html', {
                    'product': product, 'user': request.user,
                    'error': 'Code promo invalide ou expiré.'
                })

        with transaction.atomic():
            product.stock_quantity = F('stock_quantity') - quantite
            product.save(update_fields=['stock_quantity'])
            product.refresh_from_db()

            order = Order.objects.create(
                buyer=request.user,
                seller=product.seller,
                shipping_address=adresse,
                status='pending',
                commission_rate=Decimal('0.12'),
                promo_code=promo_code,
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantite,
                unit_price_base=product.price_base,
                commission_rate=Decimal('0.12'),
            )

        order.refresh_from_db()

        if promo_code:
            order.discount_amount = promo_code.calculate_discount(order.total_ht)
            promo_code.used_count = F('used_count') + 1
            promo_code.save(update_fields=['used_count'])
            order.save(update_fields=['discount_amount'])

        # Tâche asynchrone : facture corporate détaillée + email
        try:
            process_order_workflow.delay(order.id)
        except Exception:
            pass  # Celery/Redis peut ne pas etre disponible en dev

        # Retourner le PDF immédiatement (WeasyPrint avec fallback ReportLab)
        return _generer_facture_immediate(order, product, quantite, request)


# ─── GENERATION PDF IMMEDIATE ──────────────────────────────────────

def _generer_facture_immediate(order, product, quantite, request):
    """
    Genere une facture PDF conforme a la norme marocaine :
      - Prix unitaire HT = commission L'Fellah 12% incluse (invisible client)
      - Total HT, TVA 20%, Total TTC
      - Mentions legales : ICE, RC, IF, Patente
    Strategie : WeasyPrint (HTML) puis ReportLab (fallback).
    """
    from django.conf import settings
    societe = getattr(settings, 'LF_SOCIETE', {})

    prix_ht_unitaire = product.price_final_display
    total_ht = (prix_ht_unitaire * quantite).quantize(Decimal('0.01'))
    ht_apres_remise = total_ht
    if order.discount_amount:
        ht_apres_remise = max(Decimal('0.00'), total_ht - order.discount_amount)
    total_tva = (ht_apres_remise * order.tva_rate).quantize(Decimal('0.01'))
    total_ttc = (ht_apres_remise + total_tva).quantize(Decimal('0.01'))

    ctx = {
        'order': order,
        'product': product,
        'quantite': quantite,
        'prix_ht_unitaire': prix_ht_unitaire,
        'total_ht': total_ht,
        'total_tva': total_tva,
        'total_ttc': total_ttc,
        'tva_rate_pct': int(order.tva_rate * 100),
        'societe': societe,
        'date_emission': timezone.now(),
    }

    try:
        from weasyprint import HTML
        from pathlib import Path
        from django.template.loader import render_to_string

        html_str = render_to_string('marketplace/invoice_pdf.html', ctx)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        base_url = Path(settings.MEDIA_ROOT).as_uri() + '/'
        HTML(string=html_str, base_url=base_url).write_pdf(tmp.name)

        resp = FileResponse(open(tmp.name, 'rb'), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="Facture_LFellah_{order.id}.pdf"'
        return resp
    except Exception as e:
        print(f"[PDF] WeasyPrint echoue ({e}), fallback ReportLab...")

    return _generer_facture_reportlab(order, product, quantite, ctx)


def _generer_facture_reportlab(order, product, quantite, ctx):
    """
    Fallback ReportLab : facture conforme norme marocaine.
    Colonnes : Designation, QTE, Prix Unitaire HT, Total HT, TVA 20%, Total TTC.
    Mentions legales : ICE, RC, IF, Patente.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from django.conf import settings

    prix_ht_unitaire = ctx['prix_ht_unitaire']
    total_ht = ctx['total_ht']
    total_tva = ctx['total_tva']
    total_ttc = ctx['total_ttc']
    tva_rate_pct = ctx['tva_rate_pct']
    societe = ctx.get('societe', {})

    filename = f"invoice_lfellah_immediate_{order.id}.pdf"
    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    m = 2 * cm

    LF_GREEN = '#2d6a4f'
    LF_DARK = '#1b4332'
    LF_BG = '#f0fdf4'
    LF_GRAY = '#6b7280'
    LF_ACCENT = '#95d5b2'
    LF_AMBER = '#d97706'
    LF_RED = '#e53e3e'

    # ─── BANDEAU ENTETE ────────────────────────────────────────
    c.setFillColor(colors.HexColor(LF_DARK))
    c.rect(0, h - 3*cm, w, 3*cm, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(m, h - 1.6*cm, "L'FELLAH 2.0")
    c.setFont("Helvetica", 7)
    c.drawString(m, h - 2.3*cm, "AGRICULTURE CONNECTEE  |  MARCHE B2B")

    # Bloc societe a droite
    c.setFont("Helvetica", 6)
    c.setFillColor(colors.HexColor(LF_ACCENT))
    sx = 11*cm
    sy = h - 1.3*cm
    for ligne in [
        f"ICE : {societe.get('ice', 'N/A')}",
        f"RC : {societe.get('rc', 'N/A')}  |  IF : {societe.get('if_', 'N/A')}",
        f"Patente : {societe.get('patente', 'N/A')}  |  CNSS : {societe.get('cnss', 'N/A')}",
        f"{societe.get('adresse', '')}",
    ]:
        c.drawString(sx, sy, ligne)
        sy -= 0.35*cm

    # ─── TITRE ─────────────────────────────────────────────────
    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(m, h - 3.8*cm, f"FACTURE N {order.id}")

    c.setFillColor(colors.HexColor(LF_GRAY))
    c.setFont("Helvetica", 8)
    c.drawString(m, h - 4.4*cm, f"Date d'emission : {ctx['date_emission'].strftime('%d/%m/%Y a %H:%M')}")
    c.drawString(m, h - 4.9*cm, f"Statut : {order.get_status_display()}")

    # ─── DESTINATAIRE ──────────────────────────────────────────
    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(11*cm, h - 3.8*cm, "DESTINATAIRE")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(11*cm, h - 4.4*cm, f"Client : {order.buyer.email}")
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor(LF_GRAY))
    c.drawString(11*cm, h - 4.9*cm, f"Livraison : {order.shipping_address[:55]}")

    # ─── VENDEUR ───────────────────────────────────────────────
    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(m, h - 5.8*cm, "VENDEUR")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(m, h - 6.4*cm, f"Cooperative : {order.seller.email}")
    if order.seller.region:
        c.drawString(m, h - 6.9*cm, f"Region : {order.seller.region}")

    # ─── TABLEAU PRODUITS (NORME MAROCAINE) ────────────────────
    yt = h - 7.8*cm
    c.setFillColor(colors.HexColor(LF_BG))
    c.rect(m - 0.2*cm, yt - 0.55*cm, w - 2*m + 0.4*cm, 0.75*cm, fill=True, stroke=False)
    c.setFillColor(colors.HexColor(LF_DARK))
    c.setFont("Helvetica-Bold", 7)

    col_x = [m, 5.5*cm, 8.5*cm, 11.5*cm, 14.5*cm]
    col_labels = ["DESIGNATION", "QTE", "P.U. HT", "TOTAL HT", f"TVA {tva_rate_pct}%"]
    for label, x in zip(col_labels, col_x):
        c.drawString(x, yt, label)

    c.setStrokeColor(colors.HexColor(LF_GREEN))
    c.setLineWidth(1)
    y_line = yt - 0.7*cm
    c.line(m, y_line, w - m, y_line)

    # Ligne produit
    y = y_line - 0.55*cm
    c.setFillColor(colors.HexColor(LF_BG))
    c.rect(m - 0.2*cm, y - 0.3*cm, w - 2*m + 0.4*cm, 0.65*cm, fill=True, stroke=False)

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    cat_name = f" - {product.category.name_fr}" if product.category else ""
    c.drawString(col_x[0], y, product.name[:30] + cat_name[:30])

    c.drawString(col_x[1], y, f"{quantite} {product.unit}")
    c.setFont("Helvetica", 8)
    c.drawString(col_x[2], y, f"{prix_ht_unitaire:.2f}")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col_x[3], y, f"{total_ht:.2f}")
    c.setFillColor(colors.HexColor(LF_AMBER))
    c.drawString(col_x[4], y, f"{total_tva:.2f}")

    # ─── RECAPITULATIF ─────────────────────────────────────────
    y -= 1.5*cm
    c.setStrokeColor(colors.HexColor(LF_ACCENT))
    c.setLineWidth(1.5)
    c.line(m, y + 1*cm, w - m, y + 1*cm)

    rxl, rxv = 10.5*cm, 14.5*cm

    for label, valeur, couleur in [
        ("TOTAL HORS TAXES", f"{total_ht:.2f} MAD", colors.black),
        ("TVA ({tva_rate_pct}%)", f"{total_tva:.2f} MAD", colors.HexColor(LF_AMBER)),
    ]:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.drawString(rxl, y, label.format(tva_rate_pct=tva_rate_pct) + " :")
        c.setFillColor(couleur)
        c.drawString(rxv, y, valeur)
        y -= 0.6*cm

    if order.discount_amount > 0 and order.promo_code:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.drawString(rxl, y, f"REMISE ({order.promo_code.code}) :")
        c.setFillColor(colors.HexColor(LF_RED))
        c.drawString(rxv, y, f"-{order.discount_amount:.2f} MAD")
        y -= 0.6*cm

    y -= 0.3*cm
    c.setStrokeColor(colors.HexColor(LF_DARK))
    c.setLineWidth(2)
    c.line(rxl, y, w - m, y)

    y -= 0.7*cm
    c.setFillColor(colors.HexColor(LF_DARK))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rxl, y, "TOTAL TTC :")
    c.drawString(rxv, y, f"{total_ttc:.2f} MAD")

    # ─── PIED DE PAGE MENTIONS LEGALES ─────────────────────────
    c.setFillColor(colors.HexColor(LF_GRAY))
    c.setFont("Helvetica", 5.5)
    py = 2.3*cm
    for ligne in [
        f"L'Fellah 2.0 - {societe.get('raison_sociale', 'SARL')} au capital de {societe.get('capital', '100 000 MAD')}",
        f"ICE: {societe.get('ice', '')}  |  RC: {societe.get('rc', '')}  |  IF: {societe.get('if_', '')}  |  Patente: {societe.get('patente', '')}  |  CNSS: {societe.get('cnss', '')}",
        f"{societe.get('adresse', '')}  |  {societe.get('telephone', '')}  |  {societe.get('email', '')}  |  {societe.get('site_web', '')}",
        f"Facture generee automatiquement le {ctx['date_emission'].strftime('%d/%m/%Y a %H:%M')} - N {order.id}",
    ]:
        c.drawString(m, py, ligne)
        py -= 0.35*cm

    c.setFillColor(colors.HexColor(LF_GREEN))
    c.rect(0, 0, w, 0.25*cm, fill=True, stroke=False)
    c.save()

    resp = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="Facture_LFellah_{order.id}.pdf"'
    return resp


# ─── CODES PROMO ──────────────────────────────────────────────────

class IsMarketerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role in ('marketer', 'admin')


class PromoCodeSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'
        read_only_fields = ['used_count', 'created_at', 'created_by']


class PromoCodeViewSet(viewsets.ModelViewSet):
    """
    CRUD des codes promotionnels.
    Création réservée aux marketeurs et admins.
    Lecture publique (pour validation lors du checkout).
    """
    queryset = PromoCode.objects.all().order_by('-created_at')
    permission_classes = [IsMarketerOrReadOnly]

    def get_serializer_class(self):
        return PromoCodeSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(methods=['POST'], detail=False, url_path='validate', permission_classes=[permissions.AllowAny])
    def validate_code(self, request):
        """POST /api/promo-codes/validate/  {"code": "RAMADAN2026", "order_total": 500.00}"""
        code_str = request.data.get('code', '').upper().strip()
        order_total = Decimal(str(request.data.get('order_total', '0')))

        promo = PromoCode.objects.filter(code=code_str, is_active=True).first()
        if not promo:
            return Response({'valid': False, 'message': 'Code promo introuvable.'})
        if not promo.is_valid:
            return Response({'valid': False, 'message': 'Code promo expiré ou épuisé.'})
        if order_total < promo.min_order_amount:
            return Response({
                'valid': False,
                'message': f'Montant minimum de commande : {promo.min_order_amount:.2f} MAD.',
            })

        discount = promo.calculate_discount(order_total)
        return Response({
            'valid': True,
            'code': promo.code,
            'discount_type': promo.discount_type,
            'discount_value': float(promo.discount_value),
            'discount_amount': float(discount),
            'message': f'Réduction de {discount:.2f} MAD appliquée !',
        })

