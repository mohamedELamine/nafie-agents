.PHONY: seed-qdrant e2e-test e2e-dry-run up down logs migrate

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
