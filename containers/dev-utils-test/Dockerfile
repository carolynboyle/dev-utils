# =============================================================================
# dev-utils-test
# Python test container with setupkit pre-installed
# =============================================================================
#
# Extends python-test with setupkit installed from the dev-utils GitHub repo.
# Use this container to test the dev-utils provisioning workflow on a clean
# Python environment without affecting your host machine.
#
# Requires python-test image to be built first:
#   cd ../python-test && docker compose up --build
#
# Build:
#   docker compose up --build
#
# =============================================================================

FROM python-test:latest

# Install setupkit from GitHub
# No repo clone required — pip fetches directly from the subdirectory
RUN pip install git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/setupkit

# Verify install
RUN setupkit --help
