from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes import addresses, admin_dashboard, auth, bundles, cart, categories, conversations, coupons, delivery, health, low_stock, notifications, orders, payments, payouts, pickup, product_images, product_requests, products, questions, recently_viewed, recommendations, returns, reviews, seller_dashboard, seller_orders, shipping, support_tickets, wishlist
from app.core.config import settings


app = FastAPI(title=settings.app_name)
_media_root = Path(settings.media_root)
if not _media_root.is_absolute():
    _media_root = Path(__file__).resolve().parent.parent / _media_root
app.mount("/media", StaticFiles(directory=str(_media_root), check_dir=False), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(bundles.router, prefix=settings.api_v1_prefix)
app.include_router(bundles.admin_router, prefix=settings.api_v1_prefix)
app.include_router(pickup.router, prefix=settings.api_v1_prefix)
app.include_router(delivery.router, prefix=settings.api_v1_prefix)
app.include_router(conversations.router, prefix=settings.api_v1_prefix)
app.include_router(product_images.router, prefix=settings.api_v1_prefix)
app.include_router(cart.router, prefix=settings.api_v1_prefix)
app.include_router(orders.router, prefix=settings.api_v1_prefix)
app.include_router(payments.router, prefix=settings.api_v1_prefix)
app.include_router(coupons.router, prefix=settings.api_v1_prefix)
app.include_router(shipping.router, prefix=settings.api_v1_prefix)
app.include_router(addresses.router, prefix=settings.api_v1_prefix)
app.include_router(low_stock.seller_router, prefix=settings.api_v1_prefix)
app.include_router(low_stock.admin_router, prefix=settings.api_v1_prefix)
app.include_router(wishlist.router, prefix=settings.api_v1_prefix)
app.include_router(reviews.router, prefix=settings.api_v1_prefix)
app.include_router(seller_dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(seller_orders.router, prefix=settings.api_v1_prefix)
app.include_router(payouts.seller_router, prefix=settings.api_v1_prefix)
app.include_router(payouts.admin_router, prefix=settings.api_v1_prefix)
app.include_router(admin_dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(recently_viewed.router, prefix=settings.api_v1_prefix)
app.include_router(recommendations.router, prefix=settings.api_v1_prefix)
app.include_router(notifications.router, prefix=settings.api_v1_prefix)
app.include_router(questions.router, prefix=settings.api_v1_prefix)
app.include_router(returns.router, prefix=settings.api_v1_prefix)
app.include_router(support_tickets.buyer_router, prefix=settings.api_v1_prefix)
app.include_router(support_tickets.admin_router, prefix=settings.api_v1_prefix)
app.include_router(product_requests.buyer_router, prefix=settings.api_v1_prefix)
app.include_router(product_requests.admin_router, prefix=settings.api_v1_prefix)
app.include_router(categories.router, prefix=settings.api_v1_prefix)
