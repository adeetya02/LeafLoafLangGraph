#!/usr/bin/env python3
"""
Create supplier folder structure in GCS and local filesystem
Handles Excel/PDF files from suppliers with processing pipelines
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

try:
    from google.cloud import storage
except ImportError:
    storage = None
    print("Warning: google-cloud-storage not installed. Using local storage only.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCS bucket for supplier data
GCS_BUCKET_NAME = "leafloaf-supplier-data"

# Supplier configuration
SUPPLIERS = {
    "BALD001": {
        "name": "Baldor Specialty Foods",
        "code": "baldor",
        "file_types": ["excel", "pdf"],
        "update_frequency": "weekly"
    },
    "LFRM001": {
        "name": "Local Farms Collective", 
        "code": "local_farms",
        "file_types": ["csv", "excel"],
        "update_frequency": "daily"
    },
    "ULIN001": {
        "name": "Unfi/Albert's", 
        "code": "unfi",
        "file_types": ["excel", "pdf"],
        "update_frequency": "weekly"
    },
    "KEHE001": {
        "name": "KeHE Distributors",
        "code": "kehe", 
        "file_types": ["excel"],
        "update_frequency": "monthly"
    }
}

# Folder structure template
FOLDER_STRUCTURE = {
    "raw": {
        "description": "Original files from supplier (Excel, PDF)",
        "subfolders": ["archive", "current", "failed"]
    },
    "processed": {
        "description": "Cleaned and standardized data",
        "subfolders": ["products", "prices", "inventory"]
    },
    "staging": {
        "description": "Ready for import to database",
        "subfolders": ["pending", "completed", "errors"]
    },
    "logs": {
        "description": "Processing logs and audit trail",
        "subfolders": ["import", "validation", "errors"]
    },
    "config": {
        "description": "Supplier-specific configurations",
        "subfolders": []
    }
}

class SupplierDataManager:
    def __init__(self, local_base_path: str = "./data/suppliers"):
        self.local_base_path = Path(local_base_path)
        self.gcs_client = None
        self.bucket = None
        
    def init_gcs(self):
        """Initialize GCS client and bucket"""
        if storage is None:
            logger.warning("GCS not available. Using local storage only.")
            return
            
        try:
            self.gcs_client = storage.Client()
            self.bucket = self.gcs_client.bucket(GCS_BUCKET_NAME)
            logger.info(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
        except Exception as e:
            logger.warning(f"GCS initialization failed: {e}. Continuing with local storage only.")
    
    def create_folder_structure(self):
        """Create folder structure for all suppliers"""
        for supplier_id, supplier_info in SUPPLIERS.items():
            self.create_supplier_folders(supplier_id, supplier_info)
            
    def create_supplier_folders(self, supplier_id: str, supplier_info: Dict):
        """Create folder structure for a specific supplier"""
        supplier_code = supplier_info['code']
        
        # Create local folders
        for folder, config in FOLDER_STRUCTURE.items():
            base_folder = self.local_base_path / supplier_code / folder
            base_folder.mkdir(parents=True, exist_ok=True)
            
            # Create subfolders
            for subfolder in config['subfolders']:
                (base_folder / subfolder).mkdir(exist_ok=True)
                
            # Create README
            readme_content = f"# {folder.upper()}\n\n{config['description']}\n"
            (base_folder / "README.md").write_text(readme_content)
        
        # Create supplier config file
        self.create_supplier_config(supplier_id, supplier_info)
        
        # Create GCS folders (by uploading placeholder files)
        if self.bucket:
            self.create_gcs_folders(supplier_code)
            
        logger.info(f"Created folder structure for {supplier_info['name']} ({supplier_code})")
    
    def create_supplier_config(self, supplier_id: str, supplier_info: Dict):
        """Create supplier-specific configuration file"""
        supplier_code = supplier_info['code']
        config_path = self.local_base_path / supplier_code / "config" / "supplier_config.json"
        
        config = {
            "supplier_id": supplier_id,
            "supplier_name": supplier_info['name'],
            "supplier_code": supplier_code,
            "update_frequency": supplier_info['update_frequency'],
            "file_types": supplier_info['file_types'],
            "attribute_mappings": {
                # Supplier-specific attribute mappings
                "organic": ["organic", "org", "certified organic"],
                "gluten_free": ["gluten free", "gf", "no gluten"],
                "vegan": ["vegan", "plant based", "plant-based"],
                "local": ["local", "locally grown", "regional"]
            },
            "column_mappings": {
                # Map supplier columns to our standard schema
                "product_name": ["name", "product", "item", "description"],
                "sku": ["sku", "item_code", "product_code", "code"],
                "upc": ["upc", "barcode", "gtin", "ean"],
                "price": ["price", "wholesale_price", "cost", "unit_price"],
                "unit": ["unit", "uom", "unit_of_measure", "size"],
                "pack_size": ["pack", "case_size", "case_qty", "pack_size"],
                "category": ["category", "dept", "department", "group"]
            },
            "price_rules": {
                "markup": 2.5,  # Default retail markup
                "round_to": 0.09,  # Round prices to nearest 9 cents
                "minimum_margin": 0.20  # Minimum 20% margin
            },
            "processing_rules": {
                "skip_discontinued": True,
                "minimum_price": 0.01,
                "maximum_price": 9999.99,
                "required_fields": ["sku", "name", "price"]
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        config_path.parent.mkdir(exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Created config for {supplier_code} at {config_path}")
        
    def create_gcs_folders(self, supplier_code: str):
        """Create folder structure in GCS by uploading placeholder files"""
        for folder, config in FOLDER_STRUCTURE.items():
            # Upload README to create the folder
            blob_path = f"{supplier_code}/{folder}/README.md"
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(f"# {folder.upper()}\n\n{config['description']}")
            
            # Create subfolders
            for subfolder in config['subfolders']:
                blob_path = f"{supplier_code}/{folder}/{subfolder}/.keep"
                blob = self.bucket.blob(blob_path)
                blob.upload_from_string("")
                
    def create_attribute_inference_rules(self):
        """Create rules for inferring product attributes when not provided by supplier"""
        rules_path = self.local_base_path / "attribute_inference_rules.json"
        
        rules = {
            "organic": {
                "keywords": ["organic", "org", "certified organic", "usda organic"],
                "exclude": ["non-organic", "conventional"],
                "confidence": 0.9
            },
            "gluten_free": {
                "keywords": ["gluten free", "gf", "no gluten", "gluten-free"],
                "categories": ["produce", "meat", "dairy", "eggs"],  # Naturally GF
                "confidence": 0.85
            },
            "vegan": {
                "keywords": ["vegan", "plant based", "plant-based"],
                "exclude_categories": ["meat", "poultry", "seafood", "dairy", "eggs"],
                "confidence": 0.9
            },
            "local": {
                "keywords": ["local", "locally grown", "locally sourced", "regional"],
                "supplier_codes": ["local_farms"],  # Some suppliers are inherently local
                "confidence": 0.95
            },
            "kosher": {
                "keywords": ["kosher", "kosher certified", "ou", "ok kosher"],
                "confidence": 0.95
            },
            "non_gmo": {
                "keywords": ["non-gmo", "non gmo", "gmo free", "no gmo"],
                "confidence": 0.9
            },
            "refrigerated": {
                "categories": ["dairy", "meat", "deli", "prepared foods"],
                "keywords": ["refrigerated", "keep cold", "perishable"],
                "confidence": 0.85
            },
            "frozen": {
                "categories": ["frozen"],
                "keywords": ["frozen", "keep frozen", "freezer"],
                "confidence": 0.95
            }
        }
        
        with open(rules_path, 'w') as f:
            json.dump(rules, f, indent=2)
            
        logger.info(f"Created attribute inference rules at {rules_path}")
        
    def create_processing_script(self):
        """Create template script for processing supplier data"""
        script_path = self.local_base_path / "process_supplier_data.py"
        
        script_content = '''#!/usr/bin/env python3
"""
Process supplier data files (Excel/CSV) and prepare for import
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

class SupplierDataProcessor:
    def __init__(self, supplier_code: str):
        self.supplier_code = supplier_code
        self.base_path = Path(f"./data/suppliers/{supplier_code}")
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Load supplier configuration"""
        config_path = self.base_path / "config" / "supplier_config.json"
        with open(config_path) as f:
            return json.load(f)
            
    def process_excel_file(self, file_path: Path) -> pd.DataFrame:
        """Process Excel file from supplier"""
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Standardize column names
        df = self.standardize_columns(df)
        
        # Clean and validate data
        df = self.clean_data(df)
        
        # Infer missing attributes
        df = self.infer_attributes(df)
        
        # Add supplier info
        df['supplier_id'] = self.config['supplier_id']
        df['supplier_code'] = self.supplier_code
        
        return df
        
    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map supplier columns to standard schema"""
        column_mappings = self.config['column_mappings']
        
        for standard_col, possible_names in column_mappings.items():
            for col in df.columns:
                if col.lower() in [name.lower() for name in possible_names]:
                    df.rename(columns={col: standard_col}, inplace=True)
                    break
                    
        return df
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate data"""
        rules = self.config['processing_rules']
        
        # Remove rows with missing required fields
        required_fields = rules['required_fields']
        df = df.dropna(subset=required_fields)
        
        # Clean prices
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df[df['price'] >= rules['minimum_price']]
            df = df[df['price'] <= rules['maximum_price']]
            
        # Clean UPC codes (remove check digit issues)
        if 'upc' in df.columns:
            df['upc'] = df['upc'].astype(str).str.strip()
            df['upc'] = df['upc'].str.replace(r'\\D', '', regex=True)
            df.loc[df['upc'].str.len() != 12, 'upc'] = None
            
        return df
        
    def infer_attributes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Infer product attributes from name and category"""
        # Load inference rules
        rules_path = Path("./data/suppliers/attribute_inference_rules.json")
        with open(rules_path) as f:
            rules = json.load(f)
            
        # Initialize attribute columns
        for attr in ['is_organic', 'is_gluten_free', 'is_vegan', 'is_kosher', 
                     'is_non_gmo', 'is_refrigerated', 'is_frozen']:
            if attr not in df.columns:
                df[attr] = False
                
        # Apply inference rules
        for idx, row in df.iterrows():
            product_name = str(row.get('product_name', '')).lower()
            category = str(row.get('category', '')).lower()
            
            # Check each attribute
            for attr_key, rule in rules.items():
                attr_col = f"is_{attr_key}"
                
                # Check keywords
                if 'keywords' in rule:
                    for keyword in rule['keywords']:
                        if keyword.lower() in product_name:
                            df.at[idx, attr_col] = True
                            break
                            
                # Check categories
                if 'categories' in rule and category:
                    for rule_cat in rule['categories']:
                        if rule_cat.lower() in category:
                            df.at[idx, attr_col] = True
                            break
                            
        return df
        
    def calculate_retail_price(self, wholesale_price: float) -> float:
        """Calculate retail price from wholesale"""
        rules = self.config['price_rules']
        retail = wholesale_price * rules['markup']
        
        # Round to nearest 9 cents
        round_to = rules['round_to']
        retail = round(retail / round_to) * round_to - 0.01
        
        # Ensure minimum margin
        min_margin = rules['minimum_margin']
        if (retail - wholesale_price) / retail < min_margin:
            retail = wholesale_price / (1 - min_margin)
            
        return round(retail, 2)

if __name__ == "__main__":
    # Example usage
    processor = SupplierDataProcessor("baldor")
    
    # Process latest Excel file
    raw_folder = Path("./data/suppliers/baldor/raw/current")
    for excel_file in raw_folder.glob("*.xlsx"):
        print(f"Processing {excel_file}")
        df = processor.process_excel_file(excel_file)
        
        # Save processed data
        output_path = Path(f"./data/suppliers/baldor/processed/products/{excel_file.stem}_processed.csv")
        df.to_csv(output_path, index=False)
        print(f"Saved to {output_path}")
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
            
        # Make executable
        os.chmod(script_path, 0o755)
        logger.info(f"Created processing script at {script_path}")

def main():
    """Create complete supplier data infrastructure"""
    manager = SupplierDataManager()
    
    # Initialize GCS if available
    manager.init_gcs()
    
    # Create folder structure
    manager.create_folder_structure()
    
    # Create attribute inference rules
    manager.create_attribute_inference_rules()
    
    # Create processing script template
    manager.create_processing_script()
    
    print("\n✅ Supplier infrastructure created successfully!")
    print(f"\n📁 Local folders created at: {manager.local_base_path}")
    print("\n📋 Next steps:")
    print("1. Upload supplier Excel/PDF files to: ./data/suppliers/{supplier_code}/raw/current/")
    print("2. Run process_supplier_data.py to process files")
    print("3. Import processed data to database")
    print("\n🔧 To process files manually, I can help with:")
    print("- Reading Excel/PDF files")
    print("- Mapping columns to standard schema")
    print("- Inferring missing attributes")
    print("- Calculating retail prices")
    print("- Generating UPC codes if missing")

if __name__ == "__main__":
    main()