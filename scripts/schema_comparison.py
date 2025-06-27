#!/usr/bin/env python3
"""
Compare different schema formats to show what might be wrong
"""

import json

# CORRECT FORMAT (What ArangoDB expects)
correct_format = {
    "document": {
        "id": "marker_doc_123",
        "title": "Sample Document",
        "metadata": {
            "source": "PDF",
            "author": "Author",
            "date": "2025-03-25"
        },
        "pages": [
            {
                "page_num": 1,
                "blocks": [
                    {
                        "block_id": "block_001",
                        "type": "section_header",
                        "level": 1,
                        "text": "Introduction"
                    },
                    {
                        "block_id": "block_002",
                        "type": "text",
                        "text": "This is content."
                    }
                ]
            }
        ]
    },
    "raw_corpus": {
        "full_text": "Introduction\n\nThis is content."
    }
}

# POSSIBLE WRONG FORMAT 1: PDF_REQUIREMENTS.md style (includes embeddings)
wrong_format_1 = {
    "document_id": "doc_123",
    "metadata": {
        "title": "Sample Document",
        "author": "Author",
        "date": "2025-03-25"
    },
    "sections": [
        {
            "section_id": "sec_001",
            "section_title": "Introduction",
            "section_level": 1,
            "parent_section_id": None,
            "content": "This is content.",
            "content_type": "paragraph",
            "page_number": 1,
            "vector_embedding": [0.123, -0.456, 0.789],  # Wrong - shouldn't include this
            "references": []
        }
    ],
    "relationships": []  # Wrong - ArangoDB generates these
}

# POSSIBLE WRONG FORMAT 2: Mixed format
wrong_format_2 = {
    "document": {
        "id": "doc_123",
        "sections": [  # Wrong - should be "pages" with "blocks"
            {
                "id": "sec_001",
                "title": "Introduction",
                "content": "This is content.",
                "embeddings": []  # Wrong - no embeddings needed
            }
        ]
    }
    # Missing raw_corpus
}

# POSSIBLE WRONG FORMAT 3: Flat structure
wrong_format_3 = {
    "id": "doc_123",
    "title": "Sample Document",
    "blocks": [  # Wrong - should be nested under document.pages[].blocks
        {
            "id": "block_001",
            "type": "header",  # Wrong - should be "section_header"
            "text": "Introduction"
        }
    ],
    "full_text": "Introduction\n\nThis is content."  # Wrong - should be under raw_corpus
}

def print_comparison():
    print("SCHEMA FORMAT COMPARISON")
    print("="*60)
    
    print("\n✅ CORRECT FORMAT (What ArangoDB expects):")
    print("-"*60)
    print(json.dumps(correct_format, indent=2))
    
    print("\n\n❌ WRONG FORMAT 1 (PDF_REQUIREMENTS.md style - too complex):")
    print("-"*60)
    print(json.dumps(wrong_format_1, indent=2))
    print("\nIssues:")
    print("- Uses 'sections' instead of 'pages/blocks' structure")
    print("- Includes vector_embedding (ArangoDB generates these)")
    print("- Includes relationships (ArangoDB extracts these)")
    print("- Different field names (document_id vs document.id)")
    
    print("\n\n❌ WRONG FORMAT 2 (Mixed/incomplete format):")
    print("-"*60)
    print(json.dumps(wrong_format_2, indent=2))
    print("\nIssues:")
    print("- Missing 'raw_corpus' field")
    print("- Uses 'sections' instead of 'pages/blocks'")
    print("- Includes embeddings field")
    print("- Missing required block structure")
    
    print("\n\n❌ WRONG FORMAT 3 (Flat structure):")
    print("-"*60)
    print(json.dumps(wrong_format_3, indent=2))
    print("\nIssues:")
    print("- Flat structure instead of nested document/pages/blocks")
    print("- Wrong type names ('header' vs 'section_header')")
    print("- raw_corpus not properly structured")
    print("- Missing metadata structure")
    
    print("\n\nKEY DIFFERENCES TO REMEMBER:")
    print("="*60)
    print("1. Structure: document > pages > blocks (NOT sections)")
    print("2. No embeddings in input (ArangoDB generates them)")
    print("3. No relationships in input (ArangoDB extracts them)")
    print("4. Must include raw_corpus.full_text for validation")
    print("5. Block types: 'section_header' (not 'header')")
    print("6. Section headers need 'level' field")
    print("7. Each block needs unique 'block_id'")

if __name__ == "__main__":
    print_comparison()