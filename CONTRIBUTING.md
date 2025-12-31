# Contributing to Driftline

Thank you for your interest in contributing to Driftline! This document provides guidelines and instructions for contributing.

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and professional in all interactions.

## 🐛 Bug Reports

Before submitting a bug report:

1. Check if the issue has already been reported
2. Verify the bug exists in the latest version
3. Collect relevant information (logs, screenshots, environment details)

When submitting a bug report, include:

- Clear description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs or error messages

## ✨ Feature Requests

We welcome feature requests! When submitting:

1. Check if the feature has been requested before
2. Clearly describe the feature and its use case
3. Explain why this feature would be valuable
4. Consider including mockups or examples

## 🔧 Development Setup

### Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Go 1.21+ (for backend development)
- Node.js 20+ (for frontend development)
- Python 3.11+ (for worker development)

### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/driftline.git
   cd driftline
   ```

3. Set up environment:
   ```bash
   cp .env.example .env
   ```

4. Start development environment:
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

### Project Structure

```
driftline/
├── frontend/              # React + TypeScript frontend
├── services/
│   ├── api/              # Go API server
│   ├── drift-worker/     # Python OpenDrift worker
│   ├── data-service/     # Go data service
│   └── results-processor/ # Python results processor
├── sql/                  # Database schemas
├── nginx/                # Nginx configurations
└── monitoring/           # Prometheus & Grafana configs
```

## 📝 Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes:
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. Commit your changes:
   ```bash
   git commit -m "feat: add new feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting, etc.)
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Open a Pull Request:
   - Use a clear, descriptive title
   - Reference any related issues
   - Describe your changes in detail
   - Include screenshots for UI changes
   - List any breaking changes

### Code Review Process

- At least one maintainer approval is required
- All CI checks must pass
- Code must follow project standards
- Documentation must be updated

## 🎨 Code Style

### Go Code

- Follow [Effective Go](https://golang.org/doc/effective_go.html)
- Use `gofmt` for formatting
- Run `go vet` and `golint`

### TypeScript/React

- Use ESLint configuration
- Follow React best practices
- Use TypeScript strict mode

### Python

- Follow PEP 8
- Use type hints
- Run `pylint` and `black`

## 🧪 Testing

### Running Tests

```bash
# Frontend tests
cd frontend
npm test

# API tests
cd services/api
go test ./...

# Python tests
cd services/drift-worker
pytest
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Include both unit and integration tests

## 📚 Documentation

- Update README.md for user-facing changes
- Add inline comments for complex logic
- Update API documentation
- Include examples where helpful

## 🚀 Release Process

Releases are managed by maintainers:

1. Version bump following [Semantic Versioning](https://semver.org/)
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish Docker images
5. Create GitHub release with notes

## ❓ Questions?

- Open a discussion on GitHub
- Check existing documentation
- Review closed issues

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Driftline! 🌊
