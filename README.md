# e-Mebel CRM — REST API

Faqat API orqali ishlaydigan backend.

## Ishga tushirish

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## API Endpoints

| Method | URL | Tavsif |
|--------|-----|--------|
| POST | /api/auth/login/ | Login → token |
| POST | /api/auth/logout/ | Logout |
| GET | /api/auth/me/ | Joriy foydalanuvchi |
| GET | /api/dashboard/ | Statistika |
| GET/POST | /api/clients/ | Mijozlar |
| GET/PUT/DELETE | /api/clients/<pk>/ | Mijoz detail |
| GET/POST | /api/products/ | Mahsulotlar |
| GET/PUT/DELETE | /api/products/<pk>/ | Mahsulot detail |
| GET/POST | /api/categories/ | Kategoriyalar |
| GET/POST | /api/orders/ | Buyurtmalar |
| GET/PUT | /api/orders/<pk>/ | Buyurtma detail |
| POST | /api/orders/<pk>/status/ | Holat o'zgartirish |
| POST | /api/orders/<pk>/payments/ | To'lov qo'shish |
| GET | /api/stock/ | Ombor |
| GET/POST | /api/movements/ | Harakatlar |
| GET/POST | /api/messages/ | Xabarlar |
| GET | /api/users/ | Foydalanuvchilar |

## Authentication

```
Authorization: Token <your_token>
```

## .env

```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
TELEGRAM_BOT_TOKEN=your-bot-token
```
