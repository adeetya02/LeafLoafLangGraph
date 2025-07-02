-- LeafLoaf Database Schema
-- Supports multi-supplier products with dynamic pricing and promotions

-- Suppliers table
CREATE TABLE suppliers (
    supplier_id VARCHAR(50) PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    supplier_code VARCHAR(100) UNIQUE NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    payment_terms VARCHAR(100),
    delivery_schedule TEXT,
    minimum_order_value DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products master table (relatively static)
CREATE TABLE products (
    sku VARCHAR(100) PRIMARY KEY,
    upc VARCHAR(50) UNIQUE,
    name VARCHAR(500) NOT NULL,
    brand VARCHAR(255),
    category VARCHAR(255) NOT NULL,
    subcategory VARCHAR(255),
    description TEXT,
    
    -- Attributes (denormalized for performance)
    is_organic BOOLEAN DEFAULT false,
    is_gluten_free BOOLEAN DEFAULT false,
    is_vegan BOOLEAN DEFAULT false,
    is_kosher BOOLEAN DEFAULT false,
    is_halal BOOLEAN DEFAULT false,
    is_non_gmo BOOLEAN DEFAULT false,
    
    -- Additional attributes as JSONB for flexibility
    attributes JSONB DEFAULT '{}',
    
    -- Packaging info
    unit_size VARCHAR(100),
    unit_type VARCHAR(50), -- 'each', 'lb', 'oz', 'bunch', 'pack'
    case_quantity INTEGER,
    
    -- Search optimization
    search_terms TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Supplier products mapping
CREATE TABLE supplier_products (
    id SERIAL PRIMARY KEY,
    product_sku VARCHAR(100) REFERENCES products(sku),
    supplier_id VARCHAR(50) REFERENCES suppliers(supplier_id),
    supplier_sku VARCHAR(100) NOT NULL,
    supplier_product_name VARCHAR(500),
    is_preferred BOOLEAN DEFAULT false,
    availability_status VARCHAR(50) DEFAULT 'available',
    lead_time_days INTEGER DEFAULT 1,
    minimum_order_quantity INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(supplier_id, supplier_sku)
);

-- Dynamic pricing table
CREATE TABLE product_prices (
    id SERIAL PRIMARY KEY,
    product_sku VARCHAR(100) NOT NULL,
    supplier_id VARCHAR(50) REFERENCES suppliers(supplier_id),
    wholesale_price DECIMAL(10,2) NOT NULL,
    retail_price DECIMAL(10,2) NOT NULL,
    unit_price DECIMAL(10,2), -- Price per unit (lb, each, etc)
    
    -- Tiered pricing
    tier_pricing JSONB DEFAULT '[]', -- [{"min_qty": 10, "price": 2.50}, ...]
    
    effective_date DATE NOT NULL,
    end_date DATE,
    
    -- Price metadata
    currency VARCHAR(3) DEFAULT 'USD',
    price_basis VARCHAR(50), -- 'per_case', 'per_pound', 'per_each'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Ensure one active price per supplier per product
    CONSTRAINT unique_active_price EXCLUDE USING gist (
        product_sku WITH =,
        supplier_id WITH =,
        daterange(effective_date, end_date, '[)') WITH &&
    )
);

-- Promotions table
CREATE TABLE promotions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('percentage', 'fixed', 'bogo', 'bundle', 'tiered')),
    
    -- Flexible rules engine
    rules JSONB NOT NULL,
    
    -- Basic values
    discount_value DECIMAL(10,2),
    max_discount_amount DECIMAL(10,2),
    
    -- Applicability
    applies_to VARCHAR(50) DEFAULT 'products', -- 'products', 'categories', 'brands', 'all'
    product_skus TEXT[],
    categories TEXT[],
    brands TEXT[],
    supplier_ids TEXT[],
    
    -- Validity
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    
    -- Usage limits
    usage_limit_total INTEGER,
    usage_limit_per_customer INTEGER,
    usage_count INTEGER DEFAULT 0,
    
    -- Display
    priority INTEGER DEFAULT 100,
    is_featured BOOLEAN DEFAULT false,
    display_text TEXT,
    terms_conditions TEXT,
    
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track promotion usage
CREATE TABLE promotion_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    promotion_id UUID REFERENCES promotions(id),
    order_id VARCHAR(100),
    customer_id VARCHAR(200),
    discount_amount DECIMAL(10,2) NOT NULL,
    products_affected JSONB,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attribute definitions (for standardization)
CREATE TABLE attribute_definitions (
    attribute_key VARCHAR(100) PRIMARY KEY,
    attribute_name VARCHAR(255) NOT NULL,
    attribute_type VARCHAR(50) NOT NULL, -- 'boolean', 'text', 'number', 'enum'
    category VARCHAR(100), -- 'dietary', 'certification', 'storage', 'origin'
    possible_values TEXT[],
    validation_rules JSONB,
    display_order INTEGER,
    is_searchable BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Supplier data ingestion log
CREATE TABLE supplier_data_imports (
    id SERIAL PRIMARY KEY,
    supplier_id VARCHAR(50) REFERENCES suppliers(supplier_id),
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50), -- 'excel', 'csv', 'pdf'
    gcs_path TEXT,
    import_status VARCHAR(50) DEFAULT 'pending',
    total_records INTEGER,
    processed_records INTEGER,
    failed_records INTEGER,
    error_log JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_products_upc ON products(upc);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_attributes ON products USING GIN(attributes);
CREATE INDEX idx_products_search ON products USING GIN(search_terms);

CREATE INDEX idx_prices_sku_date ON product_prices(product_sku, effective_date DESC);
CREATE INDEX idx_prices_supplier ON product_prices(supplier_id);

CREATE INDEX idx_promotions_active ON promotions(active, start_date, end_date);
CREATE INDEX idx_promotions_products ON promotions USING GIN(product_skus);
CREATE INDEX idx_promotions_categories ON promotions USING GIN(categories);

CREATE INDEX idx_supplier_products_sku ON supplier_products(product_sku);
CREATE INDEX idx_supplier_products_preferred ON supplier_products(supplier_id, is_preferred);

-- Views for common queries
CREATE VIEW current_product_prices AS
SELECT DISTINCT ON (pp.product_sku, pp.supplier_id)
    pp.*,
    s.supplier_name,
    p.name as product_name,
    p.upc,
    sp.is_preferred
FROM product_prices pp
JOIN suppliers s ON pp.supplier_id = s.supplier_id
JOIN products p ON pp.product_sku = p.sku
LEFT JOIN supplier_products sp ON sp.product_sku = pp.product_sku AND sp.supplier_id = pp.supplier_id
WHERE pp.effective_date <= CURRENT_DATE
  AND (pp.end_date IS NULL OR pp.end_date > CURRENT_DATE)
ORDER BY pp.product_sku, pp.supplier_id, pp.effective_date DESC;

CREATE VIEW active_promotions AS
SELECT *
FROM promotions
WHERE active = true
  AND start_date <= CURRENT_TIMESTAMP
  AND end_date > CURRENT_TIMESTAMP
ORDER BY priority DESC, created_at DESC;

-- Sample data for attribute definitions
INSERT INTO attribute_definitions (attribute_key, attribute_name, attribute_type, category, possible_values) VALUES
('organic', 'Organic', 'boolean', 'certification', NULL),
('gluten_free', 'Gluten Free', 'boolean', 'dietary', NULL),
('vegan', 'Vegan', 'boolean', 'dietary', NULL),
('kosher', 'Kosher', 'boolean', 'certification', NULL),
('halal', 'Halal', 'boolean', 'certification', NULL),
('non_gmo', 'Non-GMO', 'boolean', 'certification', NULL),
('fair_trade', 'Fair Trade', 'boolean', 'certification', NULL),
('local', 'Locally Sourced', 'boolean', 'origin', NULL),
('refrigerated', 'Requires Refrigeration', 'boolean', 'storage', NULL),
('frozen', 'Frozen', 'boolean', 'storage', NULL),
('country_of_origin', 'Country of Origin', 'text', 'origin', NULL),
('allergens', 'Allergens', 'text', 'dietary', ARRAY['milk', 'eggs', 'fish', 'shellfish', 'tree_nuts', 'peanuts', 'wheat', 'soybeans']);