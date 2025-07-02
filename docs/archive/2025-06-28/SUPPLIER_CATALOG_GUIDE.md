# Supplier Catalog Management Guide

## Overview
This guide explains how to upload and process supplier catalogs (PDFs) for LeafLoaf.

## Cloud Storage Structure

```
gs://leafloaf-supplier-data/
├── raw/                    # Original PDFs as uploaded
│   ├── laxmi/
│   ├── vistar/
│   ├── shakti_foods/
│   ├── baldor/
│   └── other_suppliers/
├── processed/              # Extracted data in JSON/CSV format
├── laxmi/                 # Supplier-specific folders
├── vistar/
├── shakti_foods/
├── baldor/
├── kehe/
├── unfi/
└── local_farms/
```

## Naming Convention

All catalog PDFs must follow this format:
```
{supplier}_{YYYYMMDD}_{type}.pdf
```

Examples:
- `laxmi_20250625_full.pdf` - Full catalog from Laxmi
- `vistar_20250701_update.pdf` - Price update from Vistar
- `shakti_foods_20250615_promo.pdf` - Promotional items

Types:
- `full` - Complete product catalog
- `update` - Price/availability updates only
- `promo` - Promotional/sale items
- `new` - New product additions

## Step 1: Upload PDF to Cloud Storage

### Method 1: Using the Upload Script
```bash
./upload_supplier_catalog.sh laxmi laxmi_20250625_full.pdf
```

### Method 2: Using gsutil directly
```bash
# Upload to raw folder
gsutil cp laxmi_20250625_full.pdf gs://leafloaf-supplier-data/raw/laxmi/

# Also copy to supplier folder
gsutil cp laxmi_20250625_full.pdf gs://leafloaf-supplier-data/laxmi/
```

### Method 3: Using Google Cloud Console
1. Go to https://console.cloud.google.com/storage/browser/leafloaf-supplier-data
2. Navigate to `raw/laxmi/`
3. Click "Upload Files"
4. Select your PDF

## Step 2: Process PDF (Coming Soon)

We'll implement automated processing that:
1. Extracts product data using OCR/PDF parsing
2. Validates SKUs, prices, and descriptions
3. Creates structured JSON data
4. Updates Weaviate database
5. Logs changes to BigQuery

## Step 3: Verify Upload

Check that your file was uploaded:
```bash
gsutil ls gs://leafloaf-supplier-data/raw/laxmi/
```

## Indian Suppliers Added

### Laxmi
- Folder: `gs://leafloaf-supplier-data/laxmi/`
- Products: Rice, dal, flour, spices, oils
- Example: `laxmi_20250625_full.pdf`

### Vistar (Already existed)
- Folder: `gs://leafloaf-supplier-data/vistar/`
- Products: South Indian specialties
- Example: `vistar_20250625_full.pdf`

### Shakti Foods
- Folder: `gs://leafloaf-supplier_data/shakti_foods/`
- Products: Snacks, pickles, ready-to-eat
- Example: `shakti_foods_20250625_full.pdf`

## API Access

Your deployed API: **https://leafloaf-v2srnrkkhq-uc.a.run.app**

### Test Indian Products
```bash
# Search for Indian products
curl -X POST https://leafloaf-v2srnrkkhq-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me basmati rice and dal"}'

# Search by supplier
curl -X POST https://leafloaf-v2srnrkkhq-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what products do you have from Laxmi?"}'
```

### Web Interfaces
1. **Chat Interface**: Open `chatbot.html` and set API URL to https://leafloaf-v2srnrkkhq-uc.a.run.app
2. **Promotion Manager**: Open `promotion_manager.html` and set API URL

## Promotions for Indian Products

We've already added:
1. **DIWALI20** - 20% off all Indian groceries (min $35)
2. **NAMASTE15** - 15% off for new Indian grocery customers (min $25)
3. **Rice & Dal Bundle** - 10% off when buying 2+ staples

## Next Steps

After uploading `laxmi_20250625_full.pdf`:
1. The file will be in `gs://leafloaf-supplier-data/raw/laxmi/`
2. We'll process it to extract products
3. Products will be added/updated in Weaviate
4. Analytics will track the catalog update

## Manual Product Addition

While waiting for automated processing, you can manually add products:
```python
# Run add_indian_suppliers.py to add more products
python3 add_indian_suppliers.py
```

## Support

For issues or questions:
- Check BigQuery logs: https://console.cloud.google.com/bigquery?project=leafloafai
- View Cloud Storage: https://console.cloud.google.com/storage/browser/leafloaf-supplier-data
- API health: https://leafloaf-v2srnrkkhq-uc.a.run.app/health