from decimal import Decimal
from rest_framework import serializers
from .models import Product, ProductCategory, Order, OrderItem


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'name_fr', 'name_ar', 'icon', 'is_active']


class ProductSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    category_name = serializers.CharField(source='category.name_fr', read_only=True)
    price_final_display = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    commission_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'seller_name', 'category', 'category_name',
            'name', 'name_fr', 'name_ar', 'description', 'unit',
            'stock_quantity', 'price_base', 'price_final_display',
            'commission_amount', 'image', 'is_organic', 'is_active',
            'harvest_date', 'created_at', 'updated_at',
        ]
        read_only_fields = ['seller', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_name', 'product_unit',
            'product_image', 'quantity', 'unit_price_base',
            'unit_price_final', 'commission_rate',
            'total_base', 'total_commission', 'total_final',
        ]
        read_only_fields = [
            'unit_price_final', 'total_base', 'total_commission', 'total_final',
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être supérieure à 0.")
        return value

    def create(self, validated_data):
        # Prendre un snapshot du prix actuel du produit
        product = validated_data['product']
        validated_data['unit_price_base'] = product.price_base
        validated_data.setdefault('commission_rate', Decimal('0.12'))
        return super().create(validated_data)


class OrderItemCreateSerializer(serializers.Serializer):
    """Pour la création de commande: liste d'items simplifiée"""
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'buyer', 'buyer_email', 'seller', 'seller_email',
            'status', 'commission_rate', 'tva_rate',
            'total_base', 'total_commission',
            'total_ht', 'total_tva', 'total_final',
            'shipping_address', 'notes', 'invoice_pdf', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'buyer', 'total_base', 'total_commission',
            'total_ht', 'total_tva', 'total_final',
            'created_at', 'updated_at',
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Création complète d'une commande avec items"""
    seller_id = serializers.IntegerField()
    shipping_address = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemCreateSerializer(many=True)


class OrderStatusSerializer(serializers.Serializer):
    """Changement de statut (workflow: preparing -> shipped -> delivered)"""
    status = serializers.ChoiceField(
        choices=['confirmed', 'preparing', 'shipped', 'delivered', 'cancelled']
    )
