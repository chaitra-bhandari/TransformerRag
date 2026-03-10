# Document Filling Module

## Overview

Fills order document templates with extracted specifications from RAG answers.

**Module:** `doc_filling_blob.py`

**Main Class:** `DocumentFiller`

## What It Does

```
Template DOCX
    ├─ Find placeholders: {{SPEC_VOLTAGE}}, {{SPEC_POWER}}
    ├─ Load RAG answers: {"voltage": "110 kV", ...}
    ├─ Replace placeholders with values
    └─ Save filled document
```

## API Reference

### DocumentFiller

```python
from doc_filling_blob import DocumentFiller

filler = DocumentFiller()
```

#### `fill_and_save(project_name: str, answers: Dict[str, str])`

Fill template and save output:

```python
answers = {
    "SPEC_VOLTAGE": "110 kV",
    "SPEC_POWER": "250 MVA",
    "SPEC_FREQUENCY": "50 Hz",
    ...
}

filler.fill_and_save(
    project_name="Energinet_onshore",
    answers=answers
)

# Outputs to:
# order-design-documents/Energinet_onshore/Order_A.docx
# order-design-documents/Energinet_onshore/Order_B.docx
```

#### `fill_template(template_path: str, answers: Dict[str, str]) → Document`

Fill template and return Document object:

```python
from pathlib import Path
import json

with open("answers.json") as f:
    answers = json.load(f)

doc = filler.fill_template("Order_A.docx", answers)

# Modify further if needed
for para in doc.paragraphs:
    print(para.text)

# Save
doc.save("Order_A_filled.docx")
```

## Usage Examples

### Basic Filling

```python
from doc_filling_blob import DocumentFiller
import json

# Load RAG answers
with open("answers.json") as f:
    answers = json.load(f)

# Fill templates
filler = DocumentFiller()
filler.fill_and_save("MyProject", answers)

print("✓ Documents filled")
```

### Fill Multiple Projects

```python
from doc_filling_blob import DocumentFiller
import json
from pathlib import Path

filler = DocumentFiller()

# Fill each project
for answers_file in Path("results").glob("*_answers.json"):
    project = answers_file.stem.replace("_answers", "")
    
    with open(answers_file) as f:
        answers = json.load(f)
    
    filler.fill_and_save(project, answers)
    print(f"✓ Filled {project}")
```

### Custom Placeholder Mapping

```python
# Map RAG answers to template placeholders
answers = {
    "voltage": "110 kV",
    "power": "250 MVA",
    "frequency": "50 Hz",
}

# Convert to template placeholders
mapped = {
    "SPEC_VOLTAGE": answers["voltage"],
    "SPEC_POWER": answers["power"],
    "SPEC_FREQUENCY": answers["frequency"],
}

filler.fill_and_save("Project", mapped)
```

## Placeholder Format

### Recognized Formats

```
{{PLACEHOLDER}}         # Standard
{{ PLACEHOLDER }}       # With spaces
{PLACEHOLDER}           # Single braces
[PLACEHOLDER]           # Square brackets
<PLACEHOLDER>           # Angle brackets
```

### Typical Placeholders

```
# Electrical
{{SPEC_VOLTAGE}}        → "110 kV"
{{SPEC_POWER}}          → "250 MVA"
{{SPEC_FREQUENCY}}      → "50 Hz"
{{SPEC_CONNECTION}}     → "Y/Δ-11"

# Cooling
{{SPEC_COOLING}}        → "ONAN"
{{SPEC_FAN_TYPE}}       → "Forced air"

# Tank
{{SPEC_TANK_TYPE}}      → "Hermetically sealed"
{{SPEC_CONSERVATOR}}    → "With conservator"

# Oil
{{SPEC_OIL_TYPE}}       → "Mineral oil"
{{SPEC_OIL_VOLUME}}     → "5000 L"

# Document
{{PROJECT_NAME}}        → "Energinet_onshore"
{{GENERATION_DATE}}     → "2024-03-10"
```

## Template Creation

### Creating a Template

1. Open Word template
2. Insert placeholders where needed
3. Example:

```
Order Document
==============

Project: {{PROJECT_NAME}}

Technical Specifications:
- Rated Voltage: {{SPEC_VOLTAGE}}
- Rated Power: {{SPEC_POWER}}
- Frequency: {{SPEC_FREQUENCY}}

Cooling System: {{SPEC_COOLING}}

Save as: Order_A.docx
Upload to: order-templates/ blob container
```

### Upload Templates

```bash
az storage blob upload \
  --container-name order-templates \
  --name Order_A.docx \
  --file ./Order_A.docx
```

## Output Location

Filled documents saved to:

```
order-design-documents/
├── ProjectName_onshore_offshore/
│   ├── Order_A.docx
│   └── Order_B.docx
├── ProjectName_onshore/
│   ├── Order_A.docx
│   └── Order_B.docx
└── ProjectName_offshore/
    ├── Order_A.docx
    └── Order_B.docx
```

## Configuration

Environment variables:

```env
BLOB_TEMPLATES_CONTAINER=order-templates
BLOB_RESULTS_CONTAINER=order-design-documents
```

## Advanced Features

### Conditional Content

```python
# Skip filling if value is "Not found"
answers = {
    "SPEC_VOLTAGE": "Not found",  # Skip this placeholder
    "SPEC_POWER": "250 MVA",      # Fill this
}
```

### Multiple Templates

```python
templates = ["Order_A.docx", "Order_B.docx", "Order_C.docx"]

for template in templates:
    doc = filler.fill_template(template, answers)
    # Process each doc
```

### Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor

projects = ["Project1", "Project2", "Project3"]

def fill_project(project):
    with open(f"results/{project}_answers.json") as f:
        answers = json.load(f)
    filler.fill_and_save(project, answers)

with ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(fill_project, projects)
```

## Error Handling

### Missing Placeholder

```python
# Placeholder in template but not in answers
# Result: Placeholder left as-is in document
# OR: Can be configured to leave blank
```

### Template Not Found

```python
# If Order_A.docx not in blob storage
# Error: FileNotFoundError
# Solution: Upload template to blob first
```

### Invalid Answer Format

```python
# If answer contains special characters
# Handled gracefully - just replaced as-is
# No escaping needed
```

## Troubleshooting

### "Template not found"

**Solution:**
```bash
# Verify template exists in blob
az storage blob list --container-name order-templates
```

### Placeholders not replacing

**Check:**
1. Placeholder spelling matches exactly
2. Placeholder format correct: `{{PLACEHOLDER}}`
3. No extra spaces or typos
4. Answer key matches placeholder name

### Special characters in answers

**Handled automatically** - no special encoding needed

### Document corruption

**Solution:**
```python
# If filled doc is corrupted
# Try filling again
# Or validate answers JSON first
```

## Integration with Pipeline

```
[RAG Query] → answers.json
                    ↓
              [Document Filling]
                    ↓
         order-design-documents/
         (filled documents ready)
```

---

**Next:** [FastAPI Backend](app.md) → Orchestrate the entire pipeline
