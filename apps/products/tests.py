from django.test import TestCase
from apps.products.models import Category, Product
from django.utils.text import slugify


class CategoryModelTest(TestCase):
    def setUp(self):
        # Test uchun kategoriya yaratamiz
        self.category = Category.objects.create(
            name="Yumshoq mebel",
            description="Divan va kreslolar"
        )

    def test_category_slug_creation(self):
        """Kategoriya saqlanganda slug avtomatik yaratilishini tekshirish"""
        expected_slug = slugify(self.category.name)
        self.assertEqual(self.category.slug, expected_slug)

    def test_category_str_method(self):
        """__str__ metodi to'g'ri ishlashini tekshirish"""
        self.assertEqual(str(self.category), self.category.name)


class ProductModelTest(TestCase):
    def setUp(self):
        # Avval kategoriya yaratamiz
        self.category = Category.objects.create(name="Stullar")

        # Mahsulot yaratamiz
        self.product = Product.objects.create(
            category=self.category,
            name="Ofis stuli",
            sku="ST-001",
            cost_price=500000,  # Tan narxi
            selling_price=750000  # Sotish narxi
        )

    def test_product_str_method(self):
        """Mahsulot __str__ metodi (Nomi va SKU) tekshiruvi"""
        expected_name = f"{self.product.name} ({self.product.sku})"
        self.assertEqual(str(self.product), expected_name)

    def test_margin_percent_calculation(self):
        """Foyda foizi (margin_percent) to'g'ri hisoblanishini tekshirish"""
        # Hisob: ((750,000 - 500,000) / 750,000) * 100 = 33.333...
        expected_margin = float((750000 - 500000) / 750000 * 100)
        self.assertAlmostEqual(self.product.margin_percent, expected_margin, places=2)

    def test_margin_percent_zero_price(self):
        """Narx nol bo'lganda margin 0 qaytarishini tekshirish"""
        self.product.selling_price = 0
        self.product.save()
        self.assertEqual(self.product.margin_percent, 0)

    def test_stock_quantity_default(self):
        """Omborda mahsulot bo'lmasa stock_quantity 0 qaytarishini tekshirish"""
        self.assertEqual(self.product.stock_quantity, 0)