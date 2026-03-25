# docker-python-builder.sh

**Path:** bash/docker-python-builder.sh
**Syntax:** bash
**Generated:** 2026-03-23 18:05:03

```bash
#!/bin/bash

# Interactive Python Docker Container Builder
# Creates a customized Dockerfile and builds a Python development container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_PYTHON_VERSION="3.11"
DEFAULT_BASE_TYPE="slim"
DEFAULT_CONTAINER_TAG="python-dev"
DEFAULT_USERNAME="devuser"

echo -e "${BLUE}=== Python Docker Container Builder ===${NC}"
echo

# Function to prompt with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local response
    
    read -p "$prompt [$default]: " response
    echo "${response:-$default}"
}

# Function to prompt yes/no with default
prompt_yes_no() {
    local prompt="$1"
    local default="$2"
    local response
    
    while true; do
        read -p "$prompt (y/n) [$default]: " response
        response="${response:-$default}"
        case $response in
            [Yy]* ) echo "y"; break;;
            [Nn]* ) echo "n"; break;;
            * ) echo "Please answer y or n.";;
        esac
    done
}

# Get user preferences
echo -e "${YELLOW}Configuration:${NC}"
PYTHON_VERSION=$(prompt_with_default "Python version (3.9/3.10/3.11/3.12)" "$DEFAULT_PYTHON_VERSION")
BASE_TYPE=$(prompt_with_default "Base image type (slim/full/alpine)" "$DEFAULT_BASE_TYPE")
CONTAINER_TAG=$(prompt_with_default "Container tag/name" "$DEFAULT_CONTAINER_TAG")
USERNAME=$(prompt_with_default "Non-root username" "$DEFAULT_USERNAME")

echo
echo -e "${YELLOW}Development Tools:${NC}"
INCLUDE_JUPYTER=$(prompt_yes_no "Include Jupyter notebook" "y")
INCLUDE_WEB_TOOLS=$(prompt_yes_no "Include web development tools (Flask/Django/requests)" "y")
INCLUDE_DATA_TOOLS=$(prompt_yes_no "Include data science tools (pandas/numpy/matplotlib)" "n")
INCLUDE_TESTING=$(prompt_yes_no "Include testing tools (pytest/coverage)" "y")
INCLUDE_LINTING=$(prompt_yes_no "Include code quality tools (black/flake8/mypy)" "y")
INCLUDE_GIT=$(prompt_yes_no "Include git and vim" "y")

echo
echo -e "${YELLOW}Build Options:${NC}"
BUILD_NOW=$(prompt_yes_no "Build container now" "y")
if [[ "$BUILD_NOW" == "y" ]]; then
    RUN_AFTER_BUILD=$(prompt_yes_no "Run container after build" "y")
fi

# Validate Python version
case $PYTHON_VERSION in
    3.9|3.10|3.11|3.12) ;;
    *) echo -e "${RED}Invalid Python version. Using 3.11${NC}"; PYTHON_VERSION="3.11";;
esac

# Validate base type
case $BASE_TYPE in
    slim|full|alpine) ;;
    *) echo -e "${RED}Invalid base type. Using slim${NC}"; BASE_TYPE="slim";;
esac

echo
echo -e "${GREEN}Generating Dockerfile...${NC}"

# Generate Dockerfile
cat > Dockerfile << EOF
# Generated Python Development Container
# Python: $PYTHON_VERSION, Base: $BASE_TYPE, Tag: $CONTAINER_TAG

FROM python:$PYTHON_VERSION-$BASE_TYPE

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

EOF

# Add system dependencies based on base type and selections
if [[ "$BASE_TYPE" == "alpine" ]]; then
    cat >> Dockerfile << EOF
# Install system dependencies (Alpine)
RUN apk update && apk add --no-cache \\
EOF
    if [[ "$INCLUDE_GIT" == "y" ]]; then
        echo "    git \\" >> Dockerfile
        echo "    vim \\" >> Dockerfile
    fi
    echo "    curl \\" >> Dockerfile
    echo "    build-base" >> Dockerfile
else
    cat >> Dockerfile << EOF
# Install system dependencies (Debian-based)
RUN apt-get update && apt-get install -y \\
EOF
    if [[ "$INCLUDE_GIT" == "y" ]]; then
        echo "    git \\" >> Dockerfile
        echo "    vim \\" >> Dockerfile
    fi
    echo "    curl \\" >> Dockerfile
    echo "    build-essential \\" >> Dockerfile
    echo "    && rm -rf /var/lib/apt/lists/*" >> Dockerfile
fi

# Add user creation
cat >> Dockerfile << EOF

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash $USERNAME

# Set working directory
WORKDIR /app

# Install Python packages
RUN pip install --upgrade pip
EOF

# Build pip install command based on selections
PIP_PACKAGES=()

if [[ "$INCLUDE_TESTING" == "y" ]]; then
    PIP_PACKAGES+=("pytest" "pytest-cov" "coverage")
fi

if [[ "$INCLUDE_LINTING" == "y" ]]; then
    PIP_PACKAGES+=("black" "flake8" "mypy")
fi

if [[ "$INCLUDE_JUPYTER" == "y" ]]; then
    PIP_PACKAGES+=("jupyter" "ipython")
fi

if [[ "$INCLUDE_WEB_TOOLS" == "y" ]]; then
    PIP_PACKAGES+=("requests" "flask" "django" "fastapi" "python-dotenv")
fi

if [[ "$INCLUDE_DATA_TOOLS" == "y" ]]; then
    PIP_PACKAGES+=("pandas" "numpy" "matplotlib" "seaborn" "plotly")
fi

# Always include some basics
PIP_PACKAGES+=("python-dotenv")

if [[ ${#PIP_PACKAGES[@]} -gt 0 ]]; then
    echo "RUN pip install \\" >> Dockerfile
    for i in "${!PIP_PACKAGES[@]}"; do
        if [[ $i -eq $((${#PIP_PACKAGES[@]}-1)) ]]; then
            echo "    ${PIP_PACKAGES[i]}" >> Dockerfile
        else
            echo "    ${PIP_PACKAGES[i]} \\" >> Dockerfile
        fi
    done
fi

# Finish Dockerfile
cat >> Dockerfile << EOF

# Change ownership of the app directory
RUN chown -R $USERNAME:$USERNAME /app

# Switch to non-root user
USER $USERNAME

# Set default command
CMD ["/bin/bash"]
EOF

echo -e "${GREEN}Dockerfile created successfully!${NC}"

# Create helper script
cat > run-container.sh << EOF
#!/bin/bash

# Helper script for running the $CONTAINER_TAG container

# Interactive development mode
echo "Starting $CONTAINER_TAG container..."
echo "Your code directory will be mounted at /app"
echo "Exit with 'exit' or Ctrl+D"
echo

docker run -it --rm \\
    -v \$(pwd):/app \\
    -p 8000:8000 \\
    -p 5000:5000 \\
    -p 8888:8888 \\
    $CONTAINER_TAG
EOF

chmod +x run-container.sh

echo -e "${GREEN}Helper script 'run-container.sh' created${NC}"

# Build if requested
if [[ "$BUILD_NOW" == "y" ]]; then
    echo
    echo -e "${BLUE}Building Docker container...${NC}"
    docker build -t "$CONTAINER_TAG" .
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Build completed successfully!${NC}"
        
        # Show summary
        echo
        echo -e "${BLUE}=== Build Summary ===${NC}"
        echo "Container tag: $CONTAINER_TAG"
        echo "Python version: $PYTHON_VERSION"
        echo "Base image: python:$PYTHON_VERSION-$BASE_TYPE"
        echo "Username: $USERNAME"
        echo
        echo -e "${BLUE}To run your container:${NC}"
        echo "  ./run-container.sh"
        echo "  OR"
        echo "  docker run -it --rm -v \$(pwd):/app -p 8000:8000 $CONTAINER_TAG"
        
        if [[ "$RUN_AFTER_BUILD" == "y" ]]; then
            echo
            echo -e "${GREEN}Starting container...${NC}"
            ./run-container.sh
        fi
    else
        echo -e "${RED}Build failed!${NC}"
        exit 1
    fi
else
    echo
    echo -e "${BLUE}Dockerfile ready! To build:${NC}"
    echo "  docker build -t $CONTAINER_TAG ."
    echo
    echo -e "${BLUE}To run after building:${NC}"
    echo "  ./run-container.sh"
fi

# Create a config file for reuse
cat > .docker-config << EOF
PYTHON_VERSION=$PYTHON_VERSION
BASE_TYPE=$BASE_TYPE
CONTAINER_TAG=$CONTAINER_TAG
USERNAME=$USERNAME
INCLUDE_JUPYTER=$INCLUDE_JUPYTER
INCLUDE_WEB_TOOLS=$INCLUDE_WEB_TOOLS
INCLUDE_DATA_TOOLS=$INCLUDE_DATA_TOOLS
INCLUDE_TESTING=$INCLUDE_TESTING
INCLUDE_LINTING=$INCLUDE_LINTING
INCLUDE_GIT=$INCLUDE_GIT
EOF

echo
echo -e "${YELLOW}Configuration saved to .docker-config for future reference${NC}"
```
