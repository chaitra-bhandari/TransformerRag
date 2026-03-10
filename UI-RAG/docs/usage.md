# Usage Guide

## Basic Example

The simplest way to get started:

```python
from your_project import YourClass

# Create an instance
obj = YourClass()

# Use it
result = obj.method()
print(result)
```

## Common Use Cases

### Use Case 1: Processing Data

```python
from your_project import YourClass, DataProcessor

# Load your data
data = [1, 2, 3, 4, 5]

# Create processor
processor = YourClass()

# Process data
result = processor.method(data)
print(result)
```

### Use Case 2: Working with Files

```python
from your_project import FileHandler

handler = FileHandler()

# Read a file
content = handler.read_file("input.txt")

# Process it
processed = handler.process(content)

# Write result
handler.write_file("output.txt", processed)
```

### Use Case 3: Configuration Options

```python
from your_project import YourClass, Config

# Create custom config
config = Config(
    timeout=30,
    retries=3,
    verbose=True,
    method="fast"
)

# Use with config
obj = YourClass(config=config)
result = obj.method()
```

### Use Case 4: Error Handling

```python
from your_project import YourClass, CustomError

obj = YourClass()

try:
    result = obj.method()
except CustomError as e:
    print(f"An error occurred: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Patterns

### Pattern 1: Batch Processing

```python
from your_project import YourClass

obj = YourClass()
files = ["file1.txt", "file2.txt", "file3.txt"]

for file in files:
    try:
        result = obj.process_file(file)
        print(f"✓ Processed {file}")
    except Exception as e:
        print(f"✗ Failed to process {file}: {e}")
```

### Pattern 2: Chaining Operations

```python
from your_project import YourClass

obj = YourClass()

result = (obj
    .load_data("input.csv")
    .filter(condition=lambda x: x > 0)
    .transform()
    .save("output.csv"))
```

### Pattern 3: Using Callbacks

```python
from your_project import YourClass

def on_success(result):
    print(f"Success: {result}")

def on_error(error):
    print(f"Error: {error}")

obj = YourClass(
    on_success=on_success,
    on_error=on_error
)

obj.process()
```

## Performance Tips

### Tip 1: Use Appropriate Data Types

```python
# ✓ Good - Use native lists
data = [1, 2, 3, 4, 5]

# ✗ Avoid - Converting repeatedly
for item in data:
    result = obj.process(str(item))
```

### Tip 2: Batch Operations

```python
# ✓ Good - Process in batches
results = obj.process_batch(data, batch_size=100)

# ✗ Avoid - Processing one at a time
results = [obj.process(item) for item in data]
```

### Tip 3: Caching Results

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(key):
    return obj.method(key)
```

## Complete Real-World Example

```python
from your_project import DataProcessor, Logger, Config

# Setup logging
logger = Logger(level="INFO")

# Configure processor
config = Config(
    timeout=60,
    retries=3,
    cache=True
)

# Create processor
processor = DataProcessor(config=config)

# Process data
logger.info("Starting data processing...")

try:
    # Load data
    data = processor.load_file("data.csv")
    logger.info(f"Loaded {len(data)} records")
    
    # Filter data
    filtered = processor.filter(data, condition="status=active")
    logger.info(f"Filtered to {len(filtered)} records")
    
    # Transform data
    transformed = processor.transform(filtered)
    logger.info("Transformation complete")
    
    # Save results
    processor.save_file(transformed, "output.csv")
    logger.info("Results saved to output.csv")
    
except Exception as e:
    logger.error(f"Processing failed: {e}")
    raise
```

## Testing Your Code

```python
import unittest
from your_project import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        self.obj = YourClass()
    
    def test_basic_method(self):
        result = self.obj.method()
        self.assertIsNotNone(result)
    
    def test_with_input(self):
        result = self.obj.method([1, 2, 3])
        self.assertEqual(len(result), 3)

if __name__ == '__main__':
    unittest.main()
```

---

## Need More Help?

- See [API Reference](api-reference.md) for detailed function documentation
- Check [FAQ](faq.md) for common questions
- Review [Getting Started](getting-started.md) for basics
