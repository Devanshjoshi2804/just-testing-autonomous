#!/bin/bash
#
# Helper script to add API documentation files
#

echo "======================================================================"
echo "Add API Documentation"
echo "======================================================================"
echo ""
echo "Where are your API documentation files?"
echo ""
echo "Options:"
echo "  1. Copy from another directory"
echo "  2. Show instructions to upload manually"
echo ""
read -p "Choose option (1 or 2): " option

if [ "$option" == "1" ]; then
    read -p "Enter path to your API docs directory: " docs_path

    if [ ! -d "$docs_path" ]; then
        echo "❌ Directory not found: $docs_path"
        exit 1
    fi

    # Count files
    pdf_count=$(find "$docs_path" -name "*.pdf" | wc -l)
    json_count=$(find "$docs_path" -name "*.json" | wc -l)
    yaml_count=$(find "$docs_path" -name "*.yaml" -o -name "*.yml" | wc -l)
    total=$((pdf_count + json_count + yaml_count))

    echo ""
    echo "Found in $docs_path:"
    echo "  📄 PDFs: $pdf_count"
    echo "  📄 JSON: $json_count"
    echo "  📄 YAML: $yaml_count"
    echo "  ──────────"
    echo "  📄 Total: $total"
    echo ""

    if [ $total -eq 0 ]; then
        echo "❌ No API documentation files found!"
        exit 1
    fi

    read -p "Copy these files to docs/api-specs/? (y/n): " confirm

    if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
        # Copy PDFs
        if [ $pdf_count -gt 0 ]; then
            cp "$docs_path"/*.pdf docs/api-specs/ 2>/dev/null
            echo "✅ Copied $pdf_count PDF files"
        fi

        # Copy JSON
        if [ $json_count -gt 0 ]; then
            cp "$docs_path"/*.json docs/api-specs/ 2>/dev/null
            echo "✅ Copied $json_count JSON files"
        fi

        # Copy YAML
        if [ $yaml_count -gt 0 ]; then
            cp "$docs_path"/*.yaml docs/api-specs/ 2>/dev/null
            cp "$docs_path"/*.yml docs/api-specs/ 2>/dev/null
            echo "✅ Copied $yaml_count YAML files"
        fi

        echo ""
        echo "✅ Files copied successfully!"
        echo ""
        echo "Run discovery to confirm:"
        echo "  python discover_docs.py"
        echo ""
        echo "Then test the pipeline:"
        echo "  python test_real_apis.py"
    else
        echo "❌ Cancelled"
    fi

elif [ "$option" == "2" ]; then
    echo ""
    echo "Manual Upload Instructions"
    echo "────────────────────────────────────────────────────────────────"
    echo ""
    echo "1. Place your API documentation in one of these directories:"
    echo "   • docs/api-specs/  (recommended for organized docs)"
    echo "   • uploads/         (for uploaded files via API)"
    echo "   • data/api-docs/   (alternative location)"
    echo ""
    echo "2. Supported formats:"
    echo "   • PDF  (.pdf)"
    echo "   • JSON (.json) - OpenAPI/Swagger specs"
    echo "   • YAML (.yaml, .yml) - OpenAPI/Swagger specs"
    echo ""
    echo "3. Verify files were added:"
    echo "   python discover_docs.py"
    echo ""
    echo "4. Run the test pipeline:"
    echo "   python test_real_apis.py"
    echo ""
    echo "────────────────────────────────────────────────────────────────"
else
    echo "❌ Invalid option"
    exit 1
fi
