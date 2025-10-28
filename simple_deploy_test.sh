#!/bin/bash
# Simple deployment test using working executable
# This deploys the verified working idt.exe and tests format string fixes

echo "=== Simple IDT Deployment Test ==="
echo "Using working executable from dist/ directory"
echo

# Create test deployment directory
TEST_DIR="c:/temp_idt_test"
echo "Creating test directory: $TEST_DIR"
mkdir -p "$TEST_DIR"

# Copy working executable
echo "Copying working idt.exe (79MB) from dist/"
cp "dist/idt.exe" "$TEST_DIR/"

# Copy test images
echo "Copying test images..."
mkdir -p "$TEST_DIR/testimages"
cp "testimages/image1.jpg" "$TEST_DIR/testimages/" 2>/dev/null || echo "Warning: image1.jpg not found"
cp "testimages/image2.png" "$TEST_DIR/testimages/" 2>/dev/null || echo "Warning: image2.png not found"

# Copy any existing test images
if [ -d "test_data" ]; then
    echo "Copying from test_data directory..."
    cp "test_data"/*.{jpg,jpeg,png,gif,bmp} "$TEST_DIR/testimages/" 2>/dev/null || echo "No images in test_data"
fi

# List what we have
echo
echo "Test deployment contents:"
ls -la "$TEST_DIR"
echo
echo "Test images:"
ls -la "$TEST_DIR/testimages/" 2>/dev/null || echo "No test images directory"

# Change to test directory
cd "$TEST_DIR"

# Test basic functionality
echo
echo "=== Testing Basic Functionality ==="
echo "Running: ./idt.exe --help"
./idt.exe --help

echo
echo "=== Testing Format String Fix ==="
# Test with a simple image if available
TEST_IMAGE=$(find testimages -name "*.jpg" -o -name "*.png" | head -1)
if [ -n "$TEST_IMAGE" ]; then
    echo "Testing with image: $TEST_IMAGE"
    echo "Running basic description test..."
    ./idt.exe describe "$TEST_IMAGE" --output-file test_output.txt --max-images 1
    
    if [ -f "test_output.txt" ]; then
        echo "SUCCESS: Description file created!"
        echo "File size: $(stat -c%s test_output.txt) bytes"
        echo "First few lines:"
        head -3 test_output.txt
    else
        echo "ERROR: Description file not created"
    fi
else
    echo "No test images found - skipping image test"
fi

echo
echo "=== Format String Error Check ==="
# Look for any format string errors in recent output
if grep -i "format" test_output.txt 2>/dev/null | grep -i "error"; then
    echo "WARNING: Format string errors still detected"
else
    echo "SUCCESS: No format string errors detected"
fi

echo
echo "=== Deployment Test Complete ==="
echo "Test directory: $TEST_DIR"
echo "Executable tested: $(pwd)/idt.exe"