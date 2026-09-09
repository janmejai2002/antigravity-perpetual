# Contributing to Antigravity Perpetual

Thank you for contributing to Antigravity Perpetual!

## Development Workflow

1. Clone the repository:
   ```bash
   git clone https://github.com/janmejai2002/antigravity-perpetual.git
   cd antigravity-perpetual
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov
   ```
4. Run tests:
   ```bash
   python -m pytest
   ```

## Pull Request Guidelines
- Ensure all pytest unit tests pass cleanly.
- Keep terminal outputs compatible with Windows console encodings (avoid bare unicode in standard print outputs).
- Add new unit tests for any new features or bug fixes.
