#!/usr/bin/env bash
set -euo pipefail

STORAGE_ACCOUNT="mediablobazfct"
RESOURCE_GROUP="rg-11-video-compressor-az-function"

echo "==============================================="
echo "🧹 Cleanup Unused Resources"
echo "==============================================="
echo ""

# STEP 1: Delete unused queues (safe now - B2 doesn't use them)
echo "📝 Step 1: Deleting unused queues..."

queues=(
  "media-processing-queue"
  "media-processing-poison-queue"
  "media-processing-queue-poison"
)

for queue in "${queues[@]}"; do
  echo "  Deleting queue: $queue"
  az storage queue delete \
    --name "$queue" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode key \
    --only-show-errors 2>&1 | grep -v "WARNING" || echo "  (queue may not exist)"
done

echo "✅ Unused queues deleted"
echo ""

# STEP 2: Check if EP1 is still running
echo "📝 Step 2: Checking if Function App (EP1) is still running..."

if az functionapp show --name mediaprocessor2 --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "⚠️  WARNING: Function App 'mediaprocessor2' (EP1) is still running!"
  echo ""
  echo "Before deleting blob trigger queues and runtime containers:"
  echo "  1. Test B2 in production for 3-7 days"
  echo "  2. Delete EP1: az functionapp delete --name mediaprocessor2 --resource-group $RESOURCE_GROUP"
  echo "  3. Then run this script again to clean up remaining resources"
  echo ""
  exit 0
else
  echo "✅ Function App (EP1) not found - safe to delete remaining resources"
  echo ""

  # STEP 3: Delete blob trigger queues
  echo "📝 Step 3: Deleting blob trigger queues..."

  trigger_queues=(
    "azure-webjobs-blobtrigger-mediaprocessor"
    "azure-webjobs-blobtrigger-mediaprocessor2"
  )

  for queue in "${trigger_queues[@]}"; do
    echo "  Deleting queue: $queue"
    az storage queue delete \
      --name "$queue" \
      --account-name "$STORAGE_ACCOUNT" \
      --auth-mode key \
      --only-show-errors 2>&1 | grep -v "WARNING" || echo "  (queue may not exist)"
  done

  echo "✅ Blob trigger queues deleted"
  echo ""

  # STEP 4: Delete Functions runtime containers
  echo "📝 Step 4: Deleting Functions runtime containers..."

  runtime_containers=(
    "azure-webjobs-hosts"
    "azure-webjobs-secrets"
  )

  for container in "${runtime_containers[@]}"; do
    echo "  Deleting container: $container"
    az storage container delete \
      --name "$container" \
      --account-name "$STORAGE_ACCOUNT" \
      --auth-mode login \
      --only-show-errors || echo "  (container may not exist)"
  done

  echo "✅ Functions runtime containers deleted"
  echo ""
fi

echo "==============================================="
echo "✅ Cleanup Complete!"
echo "==============================================="
echo ""
echo "📊 Remaining Resources (KEEP THESE):"
echo "  Containers:"
echo "    - uploads (B2 uses)"
echo "    - processed (B2 uses)"
echo "  Tables:"
echo "    - processingjobs (B2 uses for job tracking)"
echo ""
echo "💰 Storage costs after cleanup: ~$2-5/month (minimal)"
echo ""
