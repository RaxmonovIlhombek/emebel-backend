from django.db import models
from apps.common.models import BaseModel


class Category(BaseModel):
    name        = models.CharField(max_length=100, verbose_name="Nomi")
    slug        = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name="Tavsif")

    class Meta:
        verbose_name         = "Kategoriya"
        verbose_name_plural  = "Kategoriyalar"
        ordering             = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            self.slug = slugify(self.name) or str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)


class Product(BaseModel):
    category      = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='products',
                                       verbose_name="Kategoriya")
    name          = models.CharField(max_length=200, verbose_name="Nomi")
    sku           = models.CharField(max_length=50, unique=True, verbose_name="Artikul (SKU)")
    barcode       = models.CharField(max_length=100, blank=True, verbose_name="Barcode",
                                      help_text="EAN-13, QR yoki boshqa barcode raqami")
    description   = models.TextField(blank=True, verbose_name="Tavsif")
    image         = models.ImageField(upload_to='products/', null=True, blank=True,
                                       verbose_name="Rasm")

    cost_price    = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         verbose_name="Tan narxi (so'm)")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         verbose_name="Sotish narxi (so'm)")

    material      = models.CharField(max_length=100, blank=True, verbose_name="Material")
    color         = models.CharField(max_length=50,  blank=True, verbose_name="Rang")
    dimensions    = models.CharField(max_length=100, blank=True, verbose_name="O'lcham")

    is_active     = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name        = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering            = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def stock_quantity(self):
        from apps.warehouse.models import Stock
        try:
            return Stock.objects.get(product=self).quantity
        except Exception:
            return 0

    @property
    def margin_percent(self):
        if self.selling_price and self.cost_price and self.selling_price > 0:
            return float((self.selling_price - self.cost_price) / self.selling_price * 100)
        return 0