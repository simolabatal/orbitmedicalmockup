from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    name_fr = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name_fr


class Product(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogramme'),
        ('g', 'Gramme'),
        ('litre', 'Litre'),
        ('piece', 'Pièce'),
        ('botte', 'Botte'),
        ('caisse', 'Caisse'),
        ('sac', 'Sac'),
        ('tonne', 'Tonne'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'role': 'farmer'},
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
    )
    name = models.CharField(max_length=200)
    name_fr = models.CharField(max_length=200, blank=True)
    name_ar = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='kg')
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    price_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Prix de base vendeur (hors commission 12%)",
    )
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_organic = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    harvest_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.seller}) - {self.price_base} MAD/{self.unit}"

    @property
    def price_final_display(self):
        """Prix HT affiché (base + 12% commission L'Fellah incluse)"""
        return self.price_base * Decimal('1.12')

    @property
    def price_ttc(self):
        """Prix TTC client final (HT + TVA 20% marocaine)"""
        return (self.price_final_display * Decimal('1.20')).quantize(Decimal('0.01'))

    @property
    def commission_amount(self):
        """Montant de la commission (12%)"""
        return self.price_base * Decimal('0.12')


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'En attente'),
        ('confirmed', 'En preparation'),
        ('shipped', 'En cours de livraison'),
        ('delivered', 'Livree'),
        ('cancelled', 'Annulee'),
    ]

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sales',
    )
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    commission_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.12'),
        help_text="Taux de commission L'Fellah (12% par défaut, invisible client)",
    )
    tva_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.20'),
        help_text="Taux de TVA marocain (20% par défaut)",
    )
    total_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total vendeur HT (hors commission)",
    )
    total_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Commission L'Fellah 12% (interne)",
    )
    total_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total HT facture client (commission incluse, avant TVA)",
    )
    total_tva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant TVA marocaine (20%)",
    )
    total_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total TTC facturé au client (Total HT + TVA - Remise)",
    )
    shipping_address = models.TextField()
    notes = models.TextField(blank=True)
    promo_code = models.ForeignKey(
        'marketplace.PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Code promo appliqué à la commande",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant de la reduction (deduit du Total HT avant TVA)",
    )
    is_paid = models.BooleanField(default=False, help_text="Paye au vendeur apres livraison")
    invoice_pdf = models.FileField(upload_to='invoices/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Commande #{self.id} - {self.buyer} ({self.get_status_display()})"

    def calculate_totals(self):
        """Recalcule tous les totaux (commission 12% interne + TVA 20% marocaine)."""
        items = self.items.all()
        self.total_base = sum((item.total_base for item in items), Decimal('0.00'))
        self.total_commission = sum((item.total_commission for item in items), Decimal('0.00'))
        # Total HT = prix unitaire final (commission 12% incluse) × quantité
        self.total_ht = sum((item.total_final for item in items), Decimal('0.00'))
        # Remise déduite du Total HT avant TVA (norme marocaine)
        ht_apres_remise = self.total_ht
        if self.discount_amount:
            ht_apres_remise = max(Decimal('0.00'), self.total_ht - self.discount_amount)
        # TVA 20% sur le HT net
        self.total_tva = (ht_apres_remise * self.tva_rate).quantize(Decimal('0.01'))
        # Total TTC final
        self.total_final = (ht_apres_remise + self.total_tva).quantize(Decimal('0.01'))
        return self

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new:
            self.calculate_totals()
            Order.objects.filter(pk=self.pk).update(
                total_base=self.total_base,
                total_commission=self.total_commission,
                total_ht=self.total_ht,
                total_tva=self.total_tva,
                total_final=self.total_final,
            )


class OrderItem(models.Model):
    """
    Chaque ligne de commande stocke le snapshot du prix au moment de la commande.
    La commission de 12% est calculée automatiquement dans save().
    Contraintes DB natives MySQL pour l'intégrité comptable :
      - price_final >= price_base (CHECK constraint)
      - commission_rate entre 0 et 1 (CHECK constraint)
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('marketplace.Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    unit_price_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Prix unitaire vendeur (snapshot au moment de la commande)",
    )
    unit_price_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        help_text="Prix unitaire final = base x (1 + commission)",
    )
    commission_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.12'),
        help_text="Taux de commission par ligne",
    )
    total_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        help_text="Total ligne HT: base x quantité",
    )
    total_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        help_text="Commission sur la ligne: (final - base) x quantité",
    )
    total_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        help_text="Total ligne TTC: final x quantité",
    )

    class Meta:
        constraints = []
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.unit_price_final is not None and self.unit_price_base is not None:
            if self.unit_price_final < self.unit_price_base:
                raise ValidationError({'unit_price_final': 'Le prix final doit etre superieur ou egal au prix de base.'})
        if self.commission_rate is not None:
            if self.commission_rate < Decimal('0.00') or self.commission_rate > Decimal('1.00'):
                raise ValidationError({'commission_rate': 'Le taux de commission doit etre entre 0 et 1.'})

    def __str__(self):
        return f"Ligne #{self.id} - Cde #{self.order_id} - {self.product.name}"

    def save(self, *args, **kwargs):
        # Calcul automatique de la commission 12% au niveau Base de Données
        # price_final = price_base * (1 + commission_rate)
        self.unit_price_final = (self.unit_price_base * (Decimal('1.00') + self.commission_rate)).quantize(Decimal('0.01'))
        self.total_base = (self.unit_price_base * self.quantity).quantize(Decimal('0.01'))
        self.total_commission = ((self.unit_price_final - self.unit_price_base) * self.quantity).quantize(Decimal('0.01'))
        self.total_final = (self.unit_price_final * self.quantity).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
        # Recalculer les totaux de la commande parente (incluant total_ht, total_tva)
        self.order.calculate_totals()
        Order.objects.filter(pk=self.order.pk).update(
            total_base=self.order.total_base,
            total_commission=self.order.total_commission,
            total_ht=self.order.total_ht,
            total_tva=self.order.total_tva,
            total_final=self.order.total_final,
        )


class PromoCode(models.Model):
    """
    Code promotionnel géré par l'équipe marketing.
    Appliqué à une commande pour réduire le total_final.
    Deux modes : pourcentage (ex: 10%) ou montant fixe (ex: 50 MAD).
    """
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage (%)'),
        ('fixed', 'Montant fixe (MAD)'),
    ]

    code = models.CharField(max_length=30, unique=True, help_text="Code saisi par le client (ex: RAMADAN2026)")
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valeur de la réduction (ex: 10 pour 10%, ou 50 pour 50 MAD)",
    )
    max_uses = models.PositiveIntegerField(default=100, help_text="Nombre maximum d'utilisations")
    used_count = models.PositiveIntegerField(default=0, help_text="Nombre d'utilisations effectives")
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant minimum de commande pour activer ce code",
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='promo_codes',
        limit_choices_to={'role__in': ['admin', 'marketer']},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Code Promo"
        verbose_name_plural = "Codes Promo"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()}: {self.discount_value})"

    @property
    def is_valid(self):
        """Vérifie si le code promo est utilisable maintenant."""
        from django.utils import timezone as tz
        now = tz.now()
        return (
            self.is_active
            and self.used_count < self.max_uses
            and (self.valid_until is None or self.valid_until > now)
            and (self.valid_from <= now)
        )

    def calculate_discount(self, order_total):
        """Calcule le montant de réduction pour un total de commande donné."""
        if not self.is_valid or order_total < self.min_order_amount:
            return Decimal('0.00')
        if self.discount_type == 'percentage':
            return (order_total * self.discount_value / Decimal('100.00')).quantize(Decimal('0.01'))
        return min(self.discount_value, order_total)


class CartItem(models.Model):
    """
    Panier d'achat B2B.
    Un acheteur peut ajouter plusieurs produits avant de confirmer la commande.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey('marketplace.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'),
                                   validators=[MinValueValidator(Decimal('0.01'))])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = [('user', 'product')]
        indexes = [models.Index(fields=['user'])]

    def __str__(self):
        return f"Panier {self.user.email} : {self.product.name} x{self.quantity}"

    @property
    def total_ht(self):
        return (self.product.price_final_display * self.quantity).quantize(Decimal('0.01'))  # Le montant fixe ne peut dépasser le total
