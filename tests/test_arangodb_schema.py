#!/usr/bin/env python3
"""
Test script to validate ArangoDB schema format
"""

import json
import jsonschema
from jsonschema import validate

# Define the JSON schema based on our findings
ARANGODB_SCHEMA = {
    "type": "object",
    "required": ["document", "raw_corpus"],
    "properties": {
        "document": {
            "type": "object",
            "required": ["id", "title", "pages"],
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "author": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "version": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["page_num", "blocks"],
                        "properties": {
                            "page_num": {"type": "integer"},
                            "blocks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["block_id", "type", "text"],
                                    "properties": {
                                        "block_id": {"type": "string"},
                                        "type": {"type": "string", "enum": ["section_header", "text", "list_item", "code", "table"]},
                                        "text": {"type": "string"},
                                        "level": {"type": "integer"},
                                        "position": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "raw_corpus": {
            "type": "object",
            "required": ["full_text"],
            "properties": {
                "full_text": {"type": "string"}
            }
        }
    }
}

# Test data - what we generated
test_data = {
    "document": {
        "id": "marker_doc_20250325_123456",
        "title": "Sample PDF Document",
        "metadata": {
            "source": "PDF Extraction",
            "author": "Test Author",
            "date": "2025-03-25",
            "keywords": ["test", "sample", "pdf"]
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
                        "text": "This is the introduction text."
                    }
                ]
            }
        ]
    },
    "raw_corpus": {
        "full_text": "Introduction\n\nThis is the introduction text."
    }
}

def validate_schema(data, schema):
    """Validate data against schema"""
    try:
        validate(instance=data, schema=schema)
        print("✅ Schema validation PASSED!")
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"❌ Schema validation FAILED: {e.message}")
        print(f"   Failed at path: {' -> '.join(str(p) for p in e.path)}")
        return False

def test_marker_format():
    """Test the expected Marker format from documentation"""
    # This is the format from MARKER_DATA_FORMAT.md
    marker_format = {
        "document": {
            "id": "marker_doc_123",
            "title": "ArangoDB Overview",
            "metadata": {
                "source": "Technical Documentation",
                "author": "ArangoDB Team",
                "date": "2025-05-15"
            },
            "pages": [
                {
                    "page_num": 1,
                    "blocks": [
                        {
                            "block_id": "block_001",
                            "type": "section_header",
                            "level": 1,
                            "text": "Introduction to ArangoDB"
                        },
                        {
                            "block_id": "block_002",
                            "type": "text",
                            "text": "ArangoDB is a multi-model NoSQL database..."
                        }
                    ]
                }
            ]
        },
        "raw_corpus": {
            "full_text": "Introduction to ArangoDB\n\nArangoDB is a multi-model NoSQL database..."
        }
    }
    
    print("\nTesting Marker format from documentation...")
    return validate_schema(marker_format, ARANGODB_SCHEMA)

def test_our_generated_format():
    """Test our generated format"""
    print("\nTesting our generated format...")
    return validate_schema(test_data, ARANGODB_SCHEMA)

def print_expected_format():
    """Print the expected format"""
    print("\n" + "="*60)
    print("EXPECTED ARANGODB FORMAT:")
    print("="*60)
    
    example = {
        "document": {
            "id": "marker_doc_123",
            "title": "Document Title",
            "metadata": {
                "source": "PDF Source",
                "author": "Author Name",
                "date": "2025-03-25",
                "keywords": ["keyword1", "keyword2"]
            },
            "pages": [
                {
                    "page_num": 1,
                    "blocks": [
                        {
                            "block_id": "block_001",
                            "type": "section_header",
                            "level": 1,
                            "text": "Main Section Title"
                        },
                        {
                            "block_id": "block_002", 
                            "type": "text",
                            "text": "Paragraph content goes here..."
                        },
                        {
                            "block_id": "block_003",
                            "type": "section_header",
                            "level": 2,
                            "text": "Subsection Title"
                        },
                        {
                            "block_id": "block_004",
                            "type": "text",
                            "text": "More paragraph content..."
                        }
                    ]
                }
            ]
        },
        "raw_corpus": {
            "full_text": "Main Section Title\n\nParagraph content goes here...\n\nSubsection Title\n\nMore paragraph content..."
        }
    }
    
    print(json.dumps(example, indent=2))
    print("\nKey Points:")
    print("- 'document' and 'raw_corpus' are required top-level fields")
    print("- Each block must have 'block_id', 'type', and 'text'")
    print("- Section headers must include 'level' (1 for top level, 2 for subsection, etc.)")
    print("- 'raw_corpus.full_text' should contain the entire document as a single string")
    print("- Page numbers must be preserved in 'page_num'")

if __name__ == "__main__":
    print("ARANGODB SCHEMA VALIDATION TEST")
    print("================================")
    
    # Test both formats
    marker_passed = test_marker_format()
    our_passed = test_our_generated_format()
    
    # Print expected format
    print_expected_format()
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY:")
    print("="*60)
    print(f"Marker documentation format: {'✅ PASSED' if marker_passed else '❌ FAILED'}")
    print(f"Our generated format:        {'✅ PASSED' if our_passed else '❌ FAILED'}")
    
    if marker_passed and our_passed:
        print("\n✅ Both formats are valid for ArangoDB ingestion!")
    else:
        print("\n❌ Schema validation issues detected - review the errors above")