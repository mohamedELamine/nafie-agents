#!/bin/bash
echo "🔍 فحص صحة الوكلاء..."
for agent in supervisor platform support content marketing analytics visual_production; do
    status=$(docker inspect --format='{{.State.Status}}' ar_themes_${agent} 2>/dev/null || echo "not_found")
    echo "  $agent: $status"
done
echo ""
echo "📊 حالة Redis:"
docker exec ar_themes_redis redis-cli ping
