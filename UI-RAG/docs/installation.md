# Installation

## System Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.8+ |
| pip | Latest |
| OS | Windows, macOS, Linux |

## Installation Methods

### Method 1: From PyPI (Recommended) ⭐

The easiest way:

```bash
pip install your-project-name
```

### Method 2: From GitHub Source

For the latest development version:

```bash
# Clone the repository
git clone https://github.com/your-username/your-project.git
cd your-project

# Install in development mode
pip install -e .
```

### Method 3: Using conda

If you prefer conda:

```bash
conda install -c conda-forge your-project-name
```

## Verify Installation

Check that everything installed correctly:

```bash
# Test import
python -c "import your_project; print(f'Version: {your_project.__version__}')"

# Or run the CLI (if available)
your-project --version
```

## Troubleshooting

### Issue: "Permission denied" Error

**Solution:** Use the `--user` flag:
```bash
pip install --user your-project-name
```

### Issue: "ModuleNotFoundError"

**Solutions:**
1. Make sure installation completed: `pip install your-project-name`
2. Check you're using the right Python: `python --version`
3. Try in a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install your-project-name
   ```

### Issue: Package not found on PyPI

**Solution:** Install from GitHub:
```bash
pip install git+https://github.com/your-username/your-project.git
```

### Issue: Version conflicts

**Solution:** Use a virtual environment:
```bash
python -m venv my_env
source my_env/bin/activate  # On Windows: my_env\Scripts\activate
pip install your-project-name
```

## Virtual Environment (Recommended)

Create an isolated Python environment:

```bash
# Create virtual environment
python -m venv myenv

# Activate it
# On Windows:
myenv\Scripts\activate
# On macOS/Linux:
source myenv/bin/activate

# Install project
pip install your-project-name

# Deactivate when done
deactivate
```

## Dependencies

The project automatically installs these dependencies:

- `dependency1` (v1.0+)
- `dependency2` (v2.0+)
- `dependency3` (optional)

View installed packages:
```bash
pip list
```

## Uninstall

To remove the project:

```bash
pip uninstall your-project-name
```

## Upgrade

To upgrade to the latest version:

```bash
pip install --upgrade your-project-name
```

Or:
```bash
pip install -U your-project-name
```

## Getting Help

- Check the [Getting Started](getting-started.md) guide
- See the [FAQ](faq.md) for common problems
- Review the [Usage Guide](usage.md)

---

**Next:** [Getting Started](getting-started.md) →
