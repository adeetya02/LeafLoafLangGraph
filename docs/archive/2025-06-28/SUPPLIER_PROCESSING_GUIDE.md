# Supplier Catalog Processing Guide

## 📋 Overview

This guide documents how to process supplier catalogs correctly, focusing on maintaining data quality and optimizing for search/ML performance.

## 🏢 Supplier-Specific Processing Rules

### 1. Laxmi (Indian - Completed)

**Catalog Format**: PDF with line-by-line structure
```
SR.
ITEM_CODE
DESCRIPTION (can be multi-line)
*UPC*
Weight
Qty
PRICE
AMOUNT
```

**Key Patterns**:
- Pack sizes: `8X908 GM` = 8 packets of 908 grams
- Multi-line descriptions
- NON-GMO indicators
- Price includes shipping

**Search Terms**: 
- Cuisine: "indian", "desi"
- Dietary: "vegetarian", "non-gmo" (if applicable)
- Storage: "frozen" (if applicable)

### 2. Vistar (Indian - Pending)

**Expected Format**: Similar to Laxmi
**Special Considerations**:
- South Indian focus (rice varieties, dal types)
- Include Tamil/Telugu names in search terms
- Idli/Dosa specific products

### 3. Korean Suppliers (Pending)

**Expected Challenges**:
- Romanization variations (kimchi/kimchee)
- Korean product names + English translations
- Pack sizes might be in different units

**Search Terms Strategy**:
```python
korean_terms = {
    "김치": ["kimchi", "kimchee", "fermented cabbage"],
    "고추가루": ["gochugaru", "korean chili powder", "red pepper flakes"],
    "된장": ["doenjang", "soybean paste", "fermented bean paste"]
}
```

### 4. Chinese Suppliers (Pending)

**Expected Format**: 
- Bilingual descriptions
- Metric measurements
- Different SKU patterns

**Search Terms**:
- Include Pinyin romanization
- Common English names
- Regional variations (Sichuan/Szechuan)

### 5. Baldor (Produce - Existing)

**Special Requirements**:
- Seasonality tracking
- Farm/source location
- Harvest dates
- Organic certification details
- Very short price validity (daily updates)

---

## 🔍 Search Term Extraction Rules

### DO Include:
1. **Cuisine/Ethnic indicator** (once per product)
   - "indian", "korean", "chinese", "mexican"

2. **Non-obvious attributes**
   - "frozen", "fresh", "dried"
   - "organic", "non-gmo"
   - "instant", "ready-to-eat"
   - "sugar-free", "low-sodium"

3. **Dietary restrictions**
   - "vegan", "vegetarian"
   - "gluten-free", "nut-free"
   - "halal", "kosher"

4. **Cultural synonyms** (sparingly)
   - "dal" → "lentils" (but NOT "pulse", "protein")
   - "ghee" → "clarified butter"
   - "besan" → "chickpea flour"

### DON'T Include:
1. **Words already in description**
   - If description has "Laxmi Basmati Rice", don't add "rice" to search terms

2. **Generic terms**
   - "food", "product", "item", "grocery"

3. **Assumptions**
   - NOT all dal = protein source
   - NOT all Indian = spicy
   - NOT all frozen = ready-to-eat

4. **Too many terms**
   - Maximum 10-15 search terms per product

---

## 📊 Data Quality Checklist

### For Each Product:
- [ ] Valid UPC (12-13 digits)
- [ ] Clean SKU (supplier's item code)
- [ ] Accurate description (no truncation)
- [ ] Correct price (wholesale, includes shipping?)
- [ ] Pack size parsed (understand multipliers)
- [ ] Category assigned
- [ ] Cuisine/ethnic marked
- [ ] Search terms appropriate (10-15 max)

### Pack Size Understanding:
```
5X8 LB      = 5 packs of 8 pounds each = 40 lbs total
24X300 GM   = 24 packets of 300 grams each
12X12X85 GM = 12 cases × 12 packs × 85 grams
```

---

## 🏗️ Processing Pipeline

### 1. PDF Extraction
```python
# Use pdfplumber for tables
# Fallback to PyPDF2 for text
# Consider OCR for scanned PDFs
```

### 2. Data Parsing
```python
# Supplier-specific parser
# Handle multi-line descriptions
# Extract all numeric fields correctly
```

### 3. Enhancement
```python
# Categorization (rule-based)
# Pack size parsing
# Search term generation
# Dietary flags
```

### 4. Validation
```python
# Check required fields
# Validate UPC format
# Ensure prices > 0
# Verify pack sizes parsed
```

### 5. Storage
```python
# products/ - Full details
# inventory/ - Stock status
# prices/ - Pricing data
# Create summary JSON
```

---

## 🚀 Optimization Points

### For Search:
1. **Minimize search_terms array size**
2. **Use consistent cuisine naming**
3. **Standardize dietary flags**

### For ML:
1. **Consistent categorization**
2. **Accurate pack size data** (for purchase patterns)
3. **Ethnic/cuisine indicators** (for complementary recs)

### For Pricing:
1. **Clear wholesale prices**
2. **Understand case quantities**
3. **Note if shipping included**

---

## 📝 Common Mistakes to Avoid

1. **Over-indexing**: Adding entire description to search terms
2. **Wrong assumptions**: "All Indian food is vegetarian"
3. **Lost context**: Multi-line descriptions truncated
4. **Price confusion**: Not noting if shipping included
5. **Pack size errors**: Confusing 5X8 as 5×8=40 vs 5.8

---

## 🔄 Future Improvements

1. **Multi-language search**
   - Store original language terms
   - Add transliterations

2. **Automated quality checks**
   - Flag suspicious prices
   - Detect duplicate UPCs
   - Validate against known products

3. **Smart categorization**
   - ML-based category assignment
   - Learn from user behavior

4. **Dynamic pricing data**
   - Separate volatile prices
   - Track price history

---

## 📊 Metrics to Track

1. **Data Quality**
   - % products with UPC
   - % products with prices
   - % products categorized

2. **Search Performance**
   - Search term effectiveness
   - Category accuracy
   - User satisfaction

3. **Processing Efficiency**
   - Time per catalog
   - Error rates
   - Manual intervention needed

---

This guide should be updated after processing each new supplier to capture lessons learned.