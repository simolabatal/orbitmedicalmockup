from django.contrib import admin
from django.utils.html import format_html
from .models import ProductCategory, Product, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price_final', 'total_base', 'total_commission', 'total_final')
    fields = ('product', 'quantity', 'unit_price_base', 'unit_price_final', 'commission_rate', 'total_base', 'total_commission', 'total_final')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_fr', 'name', 'is_active')
    list_filter = ('is_active',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'price_base', 'stock_quantity', 'is_active')
    list_filter = ('category', 'is_organic', 'is_active')
    search_fields = ('name', 'seller__email')

    def prix_ht_display(self, obj):
        return f"{obj.price_final_display:.2f} MAD"
    prix_ht_display.short_description = "Prix HT (comm. incluse)"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'seller', 'status', 'total_ht', 'total_tva', 'total_final', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('buyer__email', 'seller__email')
    readonly_fields = ('total_base', 'total_commission', 'total_ht', 'total_tva', 'total_final', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Commande', {'fields': ('buyer', 'seller', 'status', 'shipping_address', 'notes')}),
        ('Finance', {'fields': ('commission_rate', 'tva_rate', 'total_base', 'total_commission', 'total_ht', 'total_tva', 'total_final')}),
        ('Facture', {'fields': ('invoice_pdf',)}),
    )


# PromoCode : desenregistre de l'Admin Django (gere via Dashboard Marketeur)

