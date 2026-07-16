# Contributing to InfraSpend

First off, thank you for considering contributing to InfraSpend! It's people like you that make InfraSpend such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Exercise consideration and empathy
- Focus on what is best for the community
- Gracefully accept constructive criticism

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps which reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead and why
- Include screenshots if possible

### Suggesting Enhancements

If you have a suggestion for a new feature or enhancement:

1. Use a clear and descriptive title
2. Provide a step-by-step description of the suggested enhancement
3. Provide specific examples to demonstrate the steps
4. Describe the current behavior and explain which behavior you expected to see instead
5. Explain why this enhancement would be useful to most InfraSpend users

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Development Setup

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/your-username/finops-xray.git
```

3. Set up development environment:
```bash
# Frontend setup
cd dashboard
npm install

# Backend setup
cd api
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

4. Create a branch for your changes:
```bash
git checkout -b feature/your-feature-name
```

## Dependency Management

### Python Dependencies

We use `uv` for Python dependency management. It's faster and more reliable than pip. Here's how to use it:

1. Adding a new dependency:
```bash
uv pip install package_name
uv pip freeze > requirements.txt
```

2. Updating dependencies:
```bash
uv pip install --upgrade package_name
uv pip freeze > requirements.txt
```

3. Installing dependencies in development mode:
```bash
uv pip install -e .
```

4. Why uv?
- Much faster than pip (5-100x)
- Reliable dependency resolution
- Built-in virtual environment management
- Consistent builds across platforms

### Node.js Dependencies

For frontend dependencies, use npm:
```bash
npm install package_name
npm install package_name --save-dev  # for dev dependencies
```

## Project Structure

```
infraspend/
├── api/                 # Backend FastAPI application
│   ├── app/
│   │   ├── routers/    # API endpoints
│   │   ├── services/   # Business logic
│   │   └── helpers/    # Utility functions
│   └── tests/          # Backend tests
└── dashboard/          # Frontend React application
    ├── src/
    │   ├── components/ # Reusable components
    │   ├── views/      # Page components
    │   └── utils/      # Utility functions
    └── tests/          # Frontend tests
```

## Coding Style

### Frontend (TypeScript/React)

- Use TypeScript for all new code
- Follow the existing code style
- Use functional components with hooks
- Write meaningful component and function names
- Add proper TypeScript types
- Use CSS classes from Tailwind when possible

### Backend (Python/FastAPI)

- Follow PEP 8 style guide
- Use type hints
- Write meaningful function and variable names
- Add docstrings for functions and classes
- Keep functions small and focused
- Write unit tests for new functionality

## Testing

### Frontend Testing
```bash
cd dashboard
npm test
```

### Backend Testing
```bash
cd api
pytest
```

## Documentation

- Update the README.md if you change required dependencies
- Add JSDoc comments for new functions and components
- Update API documentation if you modify endpoints
- Include code examples where appropriate

## Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Questions?

Feel free to open an issue with your question or reach out to the maintainers directly.

Thank you for contributing to InfraSpend! 🚀
