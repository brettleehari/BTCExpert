#!/bin/bash
# CIAL Deployment Validation Test Suite
# Comprehensive testing to catch deployment bugs before production

set -e  # Exit on error

echo "=================================="
echo "CIAL Deployment Validation Suite"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# Test result tracking
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAILED++))
}

warn_test() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    ((WARNINGS++))
}

# ==============================================================================
# 1. STATIC ANALYSIS TESTS
# ==============================================================================

echo "=================================="
echo "1. Static Analysis Tests"
echo "=================================="

# Test 1.1: Python syntax check
echo -n "1.1 Checking Python syntax... "
if python3 -m py_compile cial/main.py 2>/dev/null; then
    pass_test "Python syntax valid"
else
    fail_test "Python syntax errors found"
fi

# Test 1.2: Import checks
echo -n "1.2 Checking imports... "
cd cial
if python3 -c "import sys; sys.path.insert(0, '.'); import main" 2>/dev/null; then
    pass_test "All imports resolve correctly"
else
    warn_test "Some imports may fail (expected without services running)"
fi
cd ..

# Test 1.3: Check for common security issues
echo -n "1.3 Checking for hardcoded secrets... "
if grep -r "password.*=" cial/*.py | grep -v "POSTGRES_PASSWORD" | grep -v "REDIS_PASSWORD" | grep -q "="; then
    fail_test "Potential hardcoded passwords found"
else
    pass_test "No hardcoded secrets detected"
fi

# Test 1.4: Check for TODO/FIXME
echo -n "1.4 Checking for TODOs/FIXMEs... "
TODO_COUNT=$(grep -r "TODO\|FIXME" cial/*.py 2>/dev/null | wc -l || echo "0")
if [ "$TODO_COUNT" -gt 0 ]; then
    warn_test "Found $TODO_COUNT TODO/FIXME comments"
else
    pass_test "No pending TODO/FIXME items"
fi

# ==============================================================================
# 2. CONFIGURATION VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "2. Configuration Validation"
echo "=================================="

# Test 2.1: render.yaml syntax
echo -n "2.1 Validating render.yaml syntax... "
if [ -f "render.yaml" ]; then
    if python3 -c "import yaml; yaml.safe_load(open('render.yaml'))" 2>/dev/null; then
        pass_test "render.yaml is valid YAML"
    else
        fail_test "render.yaml has syntax errors"
    fi
else
    fail_test "render.yaml not found"
fi

# Test 2.2: Check render.yaml has required fields
echo -n "2.2 Checking render.yaml required fields... "
REQUIRED_FIELDS=("services" "databases")
MISSING_FIELDS=()
for field in "${REQUIRED_FIELDS[@]}"; do
    if ! grep -q "$field:" render.yaml; then
        MISSING_FIELDS+=("$field")
    fi
done

if [ ${#MISSING_FIELDS[@]} -eq 0 ]; then
    pass_test "All required fields present in render.yaml"
else
    fail_test "Missing fields in render.yaml: ${MISSING_FIELDS[*]}"
fi

# Test 2.3: Check branch reference
echo -n "2.3 Checking branch reference in render.yaml... "
BRANCH=$(grep "branch:" render.yaml | head -1 | awk '{print $2}')
if [ "$BRANCH" == "main" ]; then
    pass_test "render.yaml references 'main' branch"
else
    fail_test "render.yaml references '$BRANCH' instead of 'main'"
fi

# Test 2.4: Check plan is set to free
echo -n "2.4 Checking plan is set to free... "
if grep -q "plan: free" render.yaml; then
    pass_test "Free tier plan configured"
else
    warn_test "Not using free tier (will cost money)"
fi

# Test 2.5: Dockerfile exists
echo -n "2.5 Checking Dockerfile exists... "
if [ -f "cial/Dockerfile" ]; then
    pass_test "Dockerfile found"
else
    fail_test "Dockerfile not found at cial/Dockerfile"
fi

# Test 2.6: Check .env.example completeness
echo -n "2.6 Checking .env.example... "
if [ -f "cial/.env.example" ]; then
    REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "SECRET_KEY" "ENVIRONMENT")
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "$var" cial/.env.example; then
            MISSING_VARS+=("$var")
        fi
    done

    if [ ${#MISSING_VARS[@]} -eq 0 ]; then
        pass_test ".env.example has all required variables"
    else
        warn_test ".env.example missing: ${MISSING_VARS[*]}"
    fi
else
    warn_test ".env.example not found"
fi

# ==============================================================================
# 3. DOCKERFILE VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "3. Dockerfile Validation"
echo "=================================="

# Test 3.1: Dockerfile syntax
echo -n "3.1 Checking Dockerfile syntax... "
if docker build -f cial/Dockerfile --no-cache -t cial-test:validation cial/ > /tmp/docker-build.log 2>&1; then
    pass_test "Dockerfile builds successfully"
else
    fail_test "Dockerfile build failed (see /tmp/docker-build.log)"
fi

# Test 3.2: Check EXPOSE port
echo -n "3.2 Checking EXPOSE port... "
if grep -q "EXPOSE 8000" cial/Dockerfile; then
    pass_test "Port 8000 exposed in Dockerfile"
else
    fail_test "Port 8000 not exposed in Dockerfile"
fi

# Test 3.3: Check Python version
echo -n "3.3 Checking Python version in Dockerfile... "
if grep -q "python:3.11.6" cial/Dockerfile; then
    pass_test "Python 3.11.6 specified in Dockerfile"
else
    warn_test "Python version may not match requirements"
fi

# Test 3.4: Check non-root user
echo -n "3.4 Checking for non-root user... "
if grep -q "USER" cial/Dockerfile; then
    pass_test "Non-root user configured in Dockerfile"
else
    warn_test "Running as root (security risk)"
fi

# Test 3.5: Check CMD/ENTRYPOINT
echo -n "3.5 Checking CMD/ENTRYPOINT... "
if grep -q "CMD\|ENTRYPOINT" cial/Dockerfile; then
    pass_test "CMD/ENTRYPOINT defined"
else
    fail_test "No CMD/ENTRYPOINT in Dockerfile"
fi

# ==============================================================================
# 4. DEPENDENCY VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "4. Dependency Validation"
echo "=================================="

# Test 4.1: requirements.txt exists
echo -n "4.1 Checking requirements.txt... "
if [ -f "cial/requirements.txt" ]; then
    pass_test "requirements.txt found"
else
    fail_test "requirements.txt not found"
fi

# Test 4.2: Check for version pinning
echo -n "4.2 Checking version pinning... "
UNPINNED=$(grep -v "^#" cial/requirements.txt | grep -v "^$" | grep -v "==" | wc -l || echo "0")
if [ "$UNPINNED" -eq 0 ]; then
    pass_test "All dependencies pinned"
else
    warn_test "$UNPINNED dependencies not pinned"
fi

# Test 4.3: Check for vulnerable dependencies
echo -n "4.3 Checking for known vulnerabilities... "
if command -v safety &> /dev/null; then
    if safety check -r cial/requirements.txt --short-report > /dev/null 2>&1; then
        pass_test "No known vulnerabilities"
    else
        warn_test "Some dependencies may have vulnerabilities"
    fi
else
    warn_test "Safety not installed (run: pip install safety)"
fi

# Test 4.4: Check critical dependencies present
echo -n "4.4 Checking critical dependencies... "
CRITICAL_DEPS=("fastapi" "uvicorn" "pydantic" "asyncpg" "redis" "pybreaker" "tenacity")
MISSING_DEPS=()
for dep in "${CRITICAL_DEPS[@]}"; do
    if ! grep -qi "^$dep==" cial/requirements.txt; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    pass_test "All critical dependencies present"
else
    fail_test "Missing dependencies: ${MISSING_DEPS[*]}"
fi

# ==============================================================================
# 5. ENVIRONMENT VARIABLE VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "5. Environment Variable Validation"
echo "=================================="

# Test 5.1: Check config.py for env var definitions
echo -n "5.1 Checking environment variable definitions... "
if [ -f "cial/infrastructure/config.py" ]; then
    pass_test "config.py found"
else
    fail_test "config.py not found"
fi

# Test 5.2: Check for default values
echo -n "5.2 Checking for safe defaults... "
if grep -q "Field(default=" cial/infrastructure/config.py; then
    pass_test "Default values defined for config"
else
    warn_test "Some config may require environment variables"
fi

# Test 5.3: Check SECRET_KEY handling
echo -n "5.3 Checking SECRET_KEY handling... "
if grep -q "SECRET_KEY" cial/infrastructure/config.py; then
    pass_test "SECRET_KEY configuration found"
else
    fail_test "SECRET_KEY not configured"
fi

# ==============================================================================
# 6. HEALTH CHECK VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "6. Health Check Validation"
echo "=================================="

# Test 6.1: Check health endpoint exists
echo -n "6.1 Checking health endpoint... "
if grep -r "def.*health\|@.*health" cial/*.py cial/**/*.py 2>/dev/null | grep -q "health"; then
    pass_test "Health endpoint defined"
else
    fail_test "Health endpoint not found"
fi

# Test 6.2: Check health endpoint path
echo -n "6.2 Checking health endpoint path... "
if grep -r '"/health"' cial/*.py cial/**/*.py 2>/dev/null | grep -q "/health"; then
    pass_test "Health endpoint at /health"
else
    warn_test "Health endpoint may not be at /health"
fi

# ==============================================================================
# 7. PORT CONFIGURATION
# ==============================================================================

echo ""
echo "=================================="
echo "7. Port Configuration"
echo "=================================="

# Test 7.1: Check port configuration
echo -n "7.1 Checking port configuration... "
if grep -q "port.*8000\|PORT.*8000" cial/infrastructure/config.py; then
    pass_test "Port 8000 configured"
else
    warn_test "Port configuration not found or different"
fi

# Test 7.2: Check Dockerfile EXPOSE matches config
echo -n "7.2 Checking Dockerfile EXPOSE matches... "
if grep -q "EXPOSE 8000" cial/Dockerfile; then
    pass_test "Dockerfile EXPOSE matches config"
else
    fail_test "Port mismatch between config and Dockerfile"
fi

# ==============================================================================
# 8. DATABASE CONFIGURATION
# ==============================================================================

echo ""
echo "=================================="
echo "8. Database Configuration"
echo "=================================="

# Test 8.1: Check PostgreSQL configuration
echo -n "8.1 Checking PostgreSQL configuration... "
if grep -q "POSTGRES" cial/infrastructure/config.py; then
    pass_test "PostgreSQL configuration found"
else
    fail_test "PostgreSQL configuration missing"
fi

# Test 8.2: Check Redis configuration
echo -n "8.2 Checking Redis configuration... "
if grep -q "REDIS" cial/infrastructure/config.py; then
    pass_test "Redis configuration found"
else
    fail_test "Redis configuration missing"
fi

# Test 8.3: Check database connection handling
echo -n "8.3 Checking database connection error handling... "
if grep -r "try.*connect\|except.*connect" cial/infrastructure/*.py 2>/dev/null | grep -q "except"; then
    pass_test "Connection error handling present"
else
    warn_test "May lack connection error handling"
fi

# ==============================================================================
# 9. INTEGRATION TEST (Container)
# ==============================================================================

echo ""
echo "=================================="
echo "9. Container Integration Test"
echo "=================================="

# Test 9.1: Run container and check startup
echo -n "9.1 Testing container startup... "
if docker run -d --name cial-validation-test -p 8888:8000 \
    -e DATABASE_URL="postgresql://test:test@localhost:5432/test" \
    -e REDIS_URL="redis://localhost:6379" \
    -e SECRET_KEY="test-secret-key-min-32-characters-long-for-testing" \
    -e ENVIRONMENT="testing" \
    cial-test:validation > /dev/null 2>&1; then

    sleep 5  # Wait for startup

    # Check if container is running
    if docker ps | grep -q cial-validation-test; then
        pass_test "Container started successfully"

        # Test 9.2: Check health endpoint response
        echo -n "9.2 Testing health endpoint... "
        if curl -s http://localhost:8888/health | grep -q "healthy\|ok\|status"; then
            pass_test "Health endpoint responds"
        else
            warn_test "Health endpoint may not be working (services not connected)"
        fi
    else
        fail_test "Container failed to start"
    fi

    # Cleanup
    docker stop cial-validation-test > /dev/null 2>&1
    docker rm cial-validation-test > /dev/null 2>&1
else
    fail_test "Container failed to run"
fi

# ==============================================================================
# 10. RENDER-SPECIFIC VALIDATION
# ==============================================================================

echo ""
echo "=================================="
echo "10. Render-Specific Validation"
echo "=================================="

# Test 10.1: Check dockerfilePath is correct
echo -n "10.1 Checking dockerfilePath in render.yaml... "
DOCKERFILE_PATH=$(grep "dockerfilePath:" render.yaml | awk '{print $2}')
if [ -f "cial/Dockerfile" ] && [ "$DOCKERFILE_PATH" == "./cial/Dockerfile" ]; then
    pass_test "dockerfilePath correct"
else
    fail_test "dockerfilePath mismatch: expected ./cial/Dockerfile, got $DOCKERFILE_PATH"
fi

# Test 10.2: Check dockerContext
echo -n "10.2 Checking dockerContext... "
DOCKER_CONTEXT=$(grep "dockerContext:" render.yaml | awk '{print $2}')
if [ "$DOCKER_CONTEXT" == "./cial" ]; then
    pass_test "dockerContext correct"
else
    warn_test "dockerContext is $DOCKER_CONTEXT"
fi

# Test 10.3: Check healthCheckPath
echo -n "10.3 Checking healthCheckPath... "
HEALTH_PATH=$(grep "healthCheckPath:" render.yaml | awk '{print $2}')
if [ "$HEALTH_PATH" == "/health" ]; then
    pass_test "healthCheckPath correct"
else
    warn_test "healthCheckPath is $HEALTH_PATH"
fi

# Test 10.4: Check autoDeploy is enabled
echo -n "10.4 Checking autoDeploy... "
if grep -q "autoDeploy: true" render.yaml; then
    pass_test "autoDeploy enabled"
else
    warn_test "autoDeploy not enabled"
fi

# Test 10.5: Check PostgreSQL version
echo -n "10.5 Checking PostgreSQL version... "
if grep -q "postgresMajorVersion: 16" render.yaml; then
    pass_test "PostgreSQL 16 configured"
else
    warn_test "PostgreSQL version may not be 16"
fi

# ==============================================================================
# SUMMARY
# ==============================================================================

echo ""
echo "=================================="
echo "Test Summary"
echo "=================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${RED}Failed:${NC}   $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo "Deployment is ready for production."
    exit 0
else
    echo -e "${RED}✗ $FAILED critical test(s) failed!${NC}"
    echo "Please fix the issues before deploying."
    exit 1
fi
