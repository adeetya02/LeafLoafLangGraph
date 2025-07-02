#!/bin/bash

echo "🚀 Setting up Spanner for LeafLoaf Graphiti Memory"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK first."
    exit 1
fi

# Configuration
PROJECT_ID="leafloafai"  # Update this to your project
INSTANCE_ID="leafloaf-graphiti"
DATABASE_ID="graphiti-memory"
REGION="us-central1"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Instance: $INSTANCE_ID"
echo "  Database: $DATABASE_ID"
echo "  Region: $REGION"

# Set project
echo -e "\n1️⃣ Setting project..."
gcloud config set project $PROJECT_ID

# Create Spanner instance (if not exists)
echo -e "\n2️⃣ Creating Spanner instance..."
gcloud spanner instances create $INSTANCE_ID \
    --config=regional-$REGION \
    --description="LeafLoaf Graphiti Memory Store" \
    --nodes=1 \
    2>/dev/null || echo "Instance already exists"

# Create database
echo -e "\n3️⃣ Creating database..."
gcloud spanner databases create $DATABASE_ID \
    --instance=$INSTANCE_ID \
    2>/dev/null || echo "Database already exists"

# Create tables
echo -e "\n4️⃣ Creating tables..."
gcloud spanner databases ddl update $DATABASE_ID \
    --instance=$INSTANCE_ID \
    --ddl="CREATE TABLE IF NOT EXISTS entities (
        entity_id STRING(64) NOT NULL,
        entity_type STRING(64),
        entity_name STRING(256),
        attributes JSON,
        created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
        updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
    ) PRIMARY KEY (entity_id);
    
    CREATE TABLE IF NOT EXISTS relationships (
        relationship_id STRING(64) NOT NULL,
        source_id STRING(64) NOT NULL,
        target_id STRING(64) NOT NULL,
        relationship_type STRING(64),
        weight FLOAT64,
        properties JSON,
        created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
        updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
    ) PRIMARY KEY (relationship_id);
    
    CREATE INDEX idx_source ON relationships(source_id);
    CREATE INDEX idx_target ON relationships(target_id);
    
    CREATE TABLE IF NOT EXISTS episodes (
        episode_id STRING(64) NOT NULL,
        user_id STRING(64),
        session_id STRING(64),
        content STRING(MAX),
        metadata JSON,
        timestamp TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
    ) PRIMARY KEY (episode_id);"

# Create service account for application
echo -e "\n5️⃣ Creating service account..."
gcloud iam service-accounts create leafloaf-graphiti \
    --display-name="LeafLoaf Graphiti Service Account" \
    2>/dev/null || echo "Service account already exists"

# Grant permissions
echo -e "\n6️⃣ Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:leafloaf-graphiti@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/spanner.databaseUser"

# Create key file
echo -e "\n7️⃣ Creating service account key..."
gcloud iam service-accounts keys create graphiti-sa-key.json \
    --iam-account=leafloaf-graphiti@$PROJECT_ID.iam.gserviceaccount.com

# Create .env.spanner file
echo -e "\n8️⃣ Creating .env.spanner file..."
cat > .env.spanner << EOF
# Spanner Configuration for Graphiti
export SPANNER_INSTANCE_ID=$INSTANCE_ID
export SPANNER_DATABASE_ID=$DATABASE_ID
export GOOGLE_APPLICATION_CREDENTIALS="./graphiti-sa-key.json"
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
EOF

echo -e "\n✅ Spanner setup complete!"
echo -e "\n📝 To use Spanner backend:"
echo "   source .env.spanner"
echo "   python3 run.py"
echo -e "\n🔑 Service account key saved to: graphiti-sa-key.json"
echo "   ⚠️  Keep this file secure and add to .gitignore"