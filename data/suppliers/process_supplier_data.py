#!/usr/bin/env python3
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
            df['upc'] = df['upc'].str.replace(r'\D', '', regex=True)
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
