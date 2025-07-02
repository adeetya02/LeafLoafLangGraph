# Supplier Catalogs

This directory contains PDF catalogs from all suppliers organized by supplier and date.

## Folder Structure

```
supplier_catalogs/
├── laxmi/
│   ├── 2025/
│   │   ├── 01/
│   │   │   ├── laxmi_20250115_full.pdf
│   │   │   └── laxmi_20250130_update.pdf
│   │   ├── 02/
│   │   └── ...
│   └── archive/
│       └── laxmi_2024_annual.pdf
├── vistar/
│   ├── 2025/
│   │   └── ...
│   └── archive/
└── shakti_foods/
    ├── 2025/
    │   └── ...
    └── archive/
```

## Naming Convention

All catalog files follow this naming pattern:
```
{supplier}_{YYYYMMDD}_{type}.pdf
```

Where:
- `supplier`: lowercase supplier name (laxmi, vistar, shakti_foods)
- `YYYYMMDD`: Date in format 20250625
- `type`: 
  - `full`: Complete catalog
  - `update`: Partial update/price changes
  - `promo`: Promotional items only
  - `new`: New products only

## Examples

- `laxmi_20250625_full.pdf` - Laxmi's full catalog for June 25, 2025
- `vistar_20250615_update.pdf` - Vistar's price update for June 15, 2025
- `shakti_foods_20250701_promo.pdf` - Shakti Foods promotional items for July 1, 2025

## Processing Status

Track processing status in `processing_log.json`:
- `pending`: PDF uploaded but not processed
- `processing`: Currently being extracted
- `completed`: Successfully imported to database
- `failed`: Processing failed (see error log)

## Automated Processing

The system automatically:
1. Monitors for new PDFs
2. Extracts product data using OCR/parsing
3. Updates Weaviate database
4. Moves processed files to archive after 90 days