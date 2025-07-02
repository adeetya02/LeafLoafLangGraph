#!/bin/bash

# Upload supplier catalog PDF to Cloud Storage
# Usage: ./upload_supplier_catalog.sh <supplier> <pdf_file>
# Example: ./upload_supplier_catalog.sh laxmi laxmi_20250625_full.pdf

SUPPLIER=$1
PDF_FILE=$2

if [ -z "$SUPPLIER" ] || [ -z "$PDF_FILE" ]; then
    echo "Usage: $0 <supplier> <pdf_file>"
    echo "Example: $0 laxmi laxmi_20250625_full.pdf"
    echo ""
    echo "Supported suppliers: laxmi, vistar, shakti_foods, baldor, kehe, unfi"
    exit 1
fi

# Check if file exists
if [ ! -f "$PDF_FILE" ]; then
    echo "Error: File $PDF_FILE not found!"
    exit 1
fi

# Extract date from filename
DATE=$(echo $PDF_FILE | grep -oE '[0-9]{8}')
if [ -z "$DATE" ]; then
    echo "Warning: Could not extract date from filename. Using today's date."
    DATE=$(date +%Y%m%d)
fi

echo "📤 Uploading $PDF_FILE to Cloud Storage"
echo "Supplier: $SUPPLIER"
echo "Date: $DATE"
echo "================================"

# Upload to raw folder
RAW_PATH="gs://leafloaf-supplier-data/raw/$SUPPLIER/$PDF_FILE"
echo "Uploading to: $RAW_PATH"
gsutil cp "$PDF_FILE" "$RAW_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Upload successful!"
    
    # Also copy to supplier's main folder
    MAIN_PATH="gs://leafloaf-supplier-data/$SUPPLIER/$PDF_FILE"
    echo "Copying to: $MAIN_PATH"
    gsutil cp "$PDF_FILE" "$MAIN_PATH"
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Process the PDF to extract product data"
    echo "2. Import to Weaviate database"
    echo "3. Update BigQuery analytics"
    
    # Create a processing record
    echo "{
  \"supplier\": \"$SUPPLIER\",
  \"filename\": \"$PDF_FILE\",
  \"upload_date\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"raw_path\": \"$RAW_PATH\",
  \"status\": \"pending\",
  \"date_extracted\": \"$DATE\"
}" > "upload_${SUPPLIER}_${DATE}.json"
    
    echo ""
    echo "📄 Processing record created: upload_${SUPPLIER}_${DATE}.json"
    echo "Upload this to track processing status"
    
else
    echo "❌ Upload failed!"
    exit 1
fi