#!/bin/bash
# Install PDF processing libraries

echo "Installing PDF processing libraries..."

# Install pdfplumber (best for tables)
pip install pdfplumber

# Install PyPDF2 as backup
pip install PyPDF2

# Install tabula-py for structured tables
pip install tabula-py

# Install camelot for advanced table extraction
pip install camelot-py[cv]

echo "PDF libraries installed!"