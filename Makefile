.PHONY: seed-qdrant e2e-test e2e-dry-run up down logs migrate \
        test test-analytics test-support test-marketing test-content test-visual test-platform

test: test-analytics test-support test-marketing test-content test-visual test-platform ## يشغّل كل الاختبارات
	@echo "\n✅ جميع الاختبارات نجحت"

test-analytics: ## اختبارات analytics-agent
	python -m pytest agents/analytics/analytics-agent/tests/ -q

test-support: ## اختبارات support-agent
	python -m pytest agents/support/support-agent/tests/ -q

test-marketing: ## اختبارات marketing-agent
	python -m pytest agents/marketing/marketing-agent/tests/ -q

test-content: ## اختبارات content-agent
	python -m pytest agents/content/content-agent/tests/ -q

test-visual: ## اختبارات visual_production-agent
	python -m pytest agents/visual_production/visual-production-agent/tests/ -q

test-platform: ## اختبارات platform-agent
	python -m pytest agents/platform/platform-agent/tests/ -q

seed-qdrant: ## يملأ Qdrant بقاعدة المعرفة الأولية
	python scripts/seed_qdrant.py

e2e-test: ## يشغّل اختبار E2E كامل
	python scripts/e2e_smoke_test.py

e2e-dry-run: ## يتحقق من الاتصالات فقط بدون كتابة
	python scripts/e2e_smoke_test.py --dry-run

up: ## يشغّل كل الخدمات
	docker compose up -d

down: ## يوقف كل الخدمات
	docker compose down

logs: ## يعرض logs كل الخدمات
	docker compose logs -f

migrate: ## يشغّل migrations يدوياً
	docker compose run --rm migrate
