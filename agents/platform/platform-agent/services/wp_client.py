"""
WordPress REST API Client
TODO: تنفيذ كامل (راجع tasks/phase2_foundation.md § T020–T023)
المرجع: agents/platform/docs/spec.md § ١٨ (أمان WordPress API)

متطلبات الأمان:
- مستخدم Editor مخصص — لا Admin
- Application Password في .env
- HTTPS فقط
- Whitelist: ar_theme_product فقط
- Rate limiting: 60 طلب/دقيقة
"""
import os
import requests
from typing import Dict, Any, Optional


class WordPressClient:
    BASE_URL: str
    AUTH: tuple

    def __init__(self):
        self.BASE_URL = os.environ["WP_SITE_URL"].rstrip("/")
        self.AUTH = (os.environ["WP_API_USER"], os.environ["WP_API_PASSWORD"])
        self._verify_https()

    def _verify_https(self):
        if not self.BASE_URL.startswith("https://"):
            raise ValueError("WP_SITE_URL يجب أن يكون HTTPS")

    # TODO: T020
    def create_theme_product(self, post_data: Dict) -> Dict:
        """
        ينشئ Custom Post Type: ar_theme_product
        يعيد: {"id": int, "link": str}
        """
        raise NotImplementedError("TODO: T020")

    # TODO: T021
    def update_theme_product(self, wp_post_id: int, post_data: Dict) -> Dict:
        """يحدث محتوى صفحة المنتج"""
        raise NotImplementedError("TODO: T021")

    # TODO: T022
    def delete_theme_product(self, wp_post_id: int) -> bool:
        """حذف للـ rollback في Saga — يعيد True عند النجاح"""
        raise NotImplementedError("TODO: T022")

    # TODO: T023
    def upload_media(self, file_path: str, alt_text: str = "") -> Dict:
        """
        رفع ملف وسائط — WebP فقط، حد أقصى 2MB
        يعيد: {"id": int, "source_url": str}
        """
        raise NotImplementedError("TODO: T023")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.BASE_URL}/wp-json/wp/v2/{endpoint}"
        resp = requests.request(method, url, auth=self.AUTH,
                                timeout=30, verify=True, **kwargs)
        resp.raise_for_status()
        return resp.json()
