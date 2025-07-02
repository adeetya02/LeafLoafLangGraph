#!/bin/bash
# Start the Spanner instance

echo "🚀 Starting Spanner instance..."

# Update the instance to have nodes (it was probably scaled to 0)
gcloud spanner instances update leafloaf-graph \
    --nodes=1 \
    --description="LeafLoaf Graph Instance - Production"

echo "✅ Spanner instance started with 1 node"
echo "💰 Cost: ~$0.90/hour for single-node instance"
echo ""
echo "To stop it later and save costs, run:"
echo "gcloud spanner instances update leafloaf-graph --nodes=0"