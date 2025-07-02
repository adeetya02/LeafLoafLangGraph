#!/bin/bash

# Create archive directory
mkdir -p docs/archive/2025-06-28

# Move old documentation to archive
echo "Archiving old documentation files..."

# Session summaries and temporary docs
mv SESSION_SUMMARY_*.md docs/archive/2025-06-28/ 2>/dev/null
mv NEXT_SESSION_*.md docs/archive/2025-06-28/ 2>/dev/null
mv MERGE_*.md docs/archive/2025-06-28/ 2>/dev/null
mv DEMO_TODO*.md docs/archive/2025-06-28/ 2>/dev/null
mv DEPLOYMENT_*.md docs/archive/2025-06-28/ 2>/dev/null
mv PRODUCTION_*.md docs/archive/2025-06-28/ 2>/dev/null
mv PERFORMANCE_*.md docs/archive/2025-06-28/ 2>/dev/null
mv GITHUB_*.md docs/archive/2025-06-28/ 2>/dev/null
mv FEATURE_*.md docs/archive/2025-06-28/ 2>/dev/null

# Move implementation specific docs
mv docs/*_IMPLEMENTATION.md docs/archive/2025-06-28/ 2>/dev/null
mv docs/*_HANDOFF.md docs/archive/2025-06-28/ 2>/dev/null
mv docs/*_PLAN.md docs/archive/2025-06-28/ 2>/dev/null

echo "Keeping only essential docs..."

# List of docs to KEEP
cat << EOF > keep_list.txt
KNOWLEDGE_BASE.md
CLAUDE.md
README.md
DEMO_SUMMARY.md
requirements.txt
.env.yaml
.env.production.yaml
docs/REALTIME_PERSONALIZATION_DEMO.md
docs/DATA_FLOW_ARCHITECTURE.md
docs/API_COMPARISON.md
docs/OPENAPI_SPEC_V3.yaml
EOF

echo "Essential files preserved:"
cat keep_list.txt

echo "Archive complete. Old docs moved to docs/archive/2025-06-28/"
rm keep_list.txt