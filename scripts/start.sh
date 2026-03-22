#!/bin/bash
echo "🚀 تشغيل منظومة قوالب WordPress العربية..."
docker-compose up -d redis postgres
sleep 5
docker-compose up -d
echo "✓ المنظومة تعمل"
docker-compose ps
