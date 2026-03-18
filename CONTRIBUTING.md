# Contributing to Govee H6006 BLE Integration

Thank you for your interest in contributing to the Govee H6006 BLE integration! 🎉

This project aims to provide **local-only Bluetooth control** for Govee lights in Home Assistant, with zero cloud dependency. Contributions are welcome in many forms: bug reports, feature requests, documentation improvements, code fixes, and support for additional Govee models.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality Standards](#code-quality-standards)
- [Submitting Changes](#submitting-changes)
- [Adding Support for New Models](#adding-support-for-new-models)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [Community and Support](#community-and-support)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful, constructive, and professional in all interactions.

**Expected behavior:**
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community and the project
- Show empathy towards other community members

**Unacceptable behavior:**
- Harassment, trolling, or derogatory comments
- Personal or political attacks
- Publishing others' private information without permission
- Any conduct that would be inappropriate in a professional setting

Project maintainers have the right to remove, edit, or reject contributions that do not align with this code of conduct.

## Getting Started

Before contributing, please:

1. **Search existing issues** to see if your bug or feature has already been reported
2. **Read the documentation** in `README.md`, `CLAUDE.md`, and the `docs/` folder
3. **Check the architecture** in `docs/ARCHITECTURE.md` to understand how the integration works
4. **Review recent pull requests** to see what changes are being worked on

If you're new to Home Assistant custom integrations, the [Home Assistant Developer Documentation](https://developers.home-assistant.io/) is an excellent resource.

## Development Setup

### Prerequisites

- **Python 3.11+** (match Home Assistant's minimum version)
- **Git** for version control
- **pytest** for running tests
- **ruff** for linting and formatting
- **mypy** for type checking

This integration uses **no build step** and has **no requirements.txt**. All dependencies are declared in `manifest.json` and are automatically installed by Home Assistant.

### Clone the Repository

```bash
git clone https://github.com/flippinhutt/govee-H6006-HA.git
cd govee-H6006-HA
```

### Install Development Tools

```bash
# Install testing and linting tools
pip install pytest pytest-cov ruff mypy

# (Optional) Install pre-commit hooks for automatic linting
pip install pre-commit
pre-commit install
```

### Test Your Setup

Run the test suite to verify everything is working:

```bash
pytest
```

All tests should pass. The test suite uses mocked dependencies (no Home Assistant installation required).

## Running Tests

The integration has comprehensive test coverage (92.74%+). **All contributions must include tests** for new functionality or bug fixes.

### Run All Tests

```bash
pytest
```

### Run a Specific Test File

```bash
pytest tests/test_api.py
```

### Stop on First Failure

```bash
pytest -x
```

### Run Tests Matching a Keyword

```bash
pytest -k "test_brightness"
```

### Check Test Coverage

```bash
pytest --cov=custom_components/govee_h6006 --cov-report=term-missing
```

Aim for **90%+ coverage** on any new code you write.

## Code Quality Standards

This project enforces strict code quality standards to maintain readability and prevent bugs.

### Linting with Ruff

We use [ruff](https://github.com/astral-sh/ruff) for fast Python linting and formatting.

**Check for linting issues:**

```bash
ruff check .
```

**Auto-fix linting issues:**

```bash
ruff check --fix .
```

**Format code:**

```bash
ruff format .
```

### Type Checking with Mypy

All code should include type hints and pass mypy type checking.

**Type check the entire integration:**

```bash
mypy custom_components/govee_h6006
```

**Type check a specific file:**

```bash
mypy custom_components/govee_h6006/api.py
```

### Pre-commit Hooks (Optional but Recommended)

To automatically run ruff and mypy before each commit, set up pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

Create a `.pre-commit-config.yaml` file in the repository root (if it doesn't exist):

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        files: ^custom_components/govee_h6006/
        args: [--ignore-missing-imports, --check-untyped-defs]
```

Once installed, ruff and mypy will run automatically on staged files before each commit. You can bypass the hooks with `git commit --no-verify` if needed (but please don't unless absolutely necessary).

## Submitting Changes

### Pull Request Process

1. **Fork the repository** and create a new branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** following the code quality standards above

3. **Add or update tests** for your changes

4. **Run the full test suite** and ensure all tests pass:
   ```bash
   pytest
   ruff check .
   mypy custom_components/govee_h6006
   ```

5. **Update documentation** if your changes affect user-facing behavior:
   - Update `README.md` if you add new features or change setup steps
   - Update `CLAUDE.md` if you change architecture, commands, or internal behavior
   - Update `CHANGELOG.md` with your changes (follow the existing format)

6. **Commit your changes** with clear, descriptive commit messages:
   ```bash
   git add .
   git commit -m "Add support for H6008 model"
   ```

   Good commit messages:
   - Use the imperative mood ("Add feature" not "Added feature")
   - Capitalize the first letter
   - Keep the first line under 70 characters
   - Add a blank line and more details if needed

7. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```

8. **Open a pull request** on GitHub:
   - Use a clear, descriptive title
   - Describe what your PR does and why
   - Reference any related issues (e.g., "Fixes #123")
   - Include testing notes if you tested with real hardware

### Pull Request Checklist

Before submitting, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code passes linting (`ruff check .`)
- [ ] Code passes type checking (`mypy custom_components/govee_h6006`)
- [ ] Test coverage is maintained (90%+)
- [ ] Documentation is updated (README.md, CLAUDE.md, CHANGELOG.md)
- [ ] Commit messages are clear and descriptive
- [ ] PR description explains what changed and why

### What to Expect

- A maintainer will review your PR within a few days
- You may be asked to make changes or clarifications
- Once approved, your PR will be merged and included in the next release
- Your contribution will be credited in the release notes

## Adding Support for New Models

Want to add support for a new Govee BLE device? Excellent! We have a comprehensive guide for this:

👉 **See [docs/CONTRIBUTING_DEVELOPER_GUIDE.md](docs/CONTRIBUTING_DEVELOPER_GUIDE.md)** for detailed instructions on:
- Reverse engineering the BLE protocol for your device
- Creating model-specific packet builders
- Updating the config flow for device detection
- Writing tests and validating with real hardware

You'll also want to review the **[BLE Protocol Sniffing Tutorial](docs/BLE_PROTOCOL_SNIFFING.md)** to learn how to capture and analyze Bluetooth traffic using tools like nRF Connect, btmon, or Wireshark.

**Before starting**, please open a **Device Support Request** issue using the template to discuss your device and share any BLE captures you've made. This helps coordinate efforts and avoid duplicate work.

## Reporting Bugs

Found a bug? Please help us fix it!

1. **Check existing issues** to see if it's already been reported
2. **Enable debug logging** to capture detailed logs:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.govee_h6006: debug
       bleak: debug
   ```
3. **Open a new issue** using the **Bug Report** template
4. **Include all requested information**:
   - Home Assistant version
   - Integration version
   - Device model
   - Bluetooth adapter info
   - Steps to reproduce
   - Debug logs (if available)

**Security vulnerabilities:** If you discover a security vulnerability, please email the maintainer directly rather than opening a public issue.

## Requesting Features

Have an idea for a new feature or improvement?

1. **Check existing issues** to see if it's already been requested
2. **Open a new issue** using the **Feature Request** template
3. **Describe the use case** and why this feature would be valuable
4. **Consider contributing** the feature yourself if you're able!

For **new device support**, use the **Device Support Request** template instead.

## Community and Support

### GitHub Discussions

For questions, ideas, and general discussion, please use **GitHub Discussions** rather than opening issues:

- **Q&A**: Ask questions about setup, troubleshooting, or usage
- **Ideas**: Share ideas for future improvements
- **Show and Tell**: Share your setups and configurations

#### Setting Up GitHub Discussions (For Maintainers)

**Requirements:**
- Repository owner or admin access
- Repository must be public or GitHub Enterprise

**Setup Instructions:**

1. **Navigate to repository Settings**
   - Go to your repository on GitHub
   - Click **Settings** (requires admin access)

2. **Enable Discussions feature**
   - Scroll down to the **Features** section
   - Check the box next to **Discussions**
   - Click **Set up discussions** if prompted

3. **Configure categories** (Recommended)
   - Go to the **Discussions** tab in your repository
   - Click the **⚙️** icon to manage categories
   - Create or customize categories:
     - **Q&A** - For support questions (enable answer marking)
     - **Ideas** - For feature requests and brainstorming
     - **Show and Tell** - For community showcases
     - **Announcements** - For project updates (maintainer-only posting)
     - **General** - For other discussions

4. **Set permissions**
   - Go to **Settings** → **Moderation options**
   - Configure who can create discussions (default: anyone with read access)
   - Set up moderation team if needed
   - Enable/disable anonymous posting (default: disabled for private repos)

5. **Pin important discussions**
   - Pin welcome/FAQ discussions to the top
   - Pin contribution guidelines or device support status

**Permissions Note:** Only repository administrators can enable Discussions. Once enabled, any user with read access can view discussions, and users with write access can create and reply to discussions. Moderation settings can be adjusted in **Settings** → **Moderation options**.

**Best Practices:**
- Enable the Q&A category with answer marking to help users find solutions
- Create an Announcements category with restricted posting (maintainers only)
- Use pinned discussions for frequently asked questions
- Set up discussion templates to guide users in providing helpful information
- Review moderation settings to prevent spam while keeping the community open

### Getting Help

- **Setup or usage questions**: Use GitHub Discussions (Q&A category)
- **Bugs**: Open a Bug Report issue
- **Feature requests**: Open a Feature Request issue
- **Device support**: Open a Device Support Request issue

### Stay Connected

- **Watch the repository** to get notified of new releases
- **Star the repository** to show your support
- **Share with others** who might find it useful

---

**Thank you for contributing to the Govee H6006 BLE integration!** 🎉

Your time and effort help make this integration better for everyone in the Home Assistant community.
