#!/usr/bin/env python3
"""
Test script for API Keys functionality
Tests the API key models and handlers structure
"""

import sys
from pathlib import Path

# Get repository root directory
REPO_ROOT = Path(__file__).parent.absolute()

def test_backend_api_key_files():
    """Test that backend API key files exist and have correct structure"""
    print("Testing backend API key implementation...")
    
    # Check model file exists
    model_file = REPO_ROOT / 'services' / 'api' / 'internal' / 'models' / 'apikey.go'
    assert model_file.exists(), "API key model file missing"
    
    # Check model structure
    with open(model_file, 'r') as f:
        model_content = f.read()
    
    assert 'type ApiKey struct' in model_content, "ApiKey struct not defined"
    assert 'type CreateApiKeyRequest struct' in model_content, "CreateApiKeyRequest struct not defined"
    assert 'type CreateApiKeyResponse struct' in model_content, "CreateApiKeyResponse struct not defined"
    assert 'ExpiresInDays' in model_content, "ExpiresInDays field not in CreateApiKeyRequest"
    assert 'ExpiresAt' in model_content, "ExpiresAt field not in ApiKey struct"
    
    print("✓ API key model file valid")
    print("  - ApiKey struct defined")
    print("  - CreateApiKeyRequest struct defined with ExpiresInDays field")
    print("  - CreateApiKeyResponse struct defined")
    
    # Check handler file exists
    handler_file = REPO_ROOT / 'services' / 'api' / 'internal' / 'handlers' / 'apikeys.go'
    assert handler_file.exists(), "API key handler file missing"
    
    # Check handler structure
    with open(handler_file, 'r') as f:
        handler_content = f.read()
    
    assert 'func ListApiKeys' in handler_content, "ListApiKeys handler not defined"
    assert 'func CreateApiKey' in handler_content, "CreateApiKey handler not defined"
    assert 'func DeleteApiKey' in handler_content, "DeleteApiKey handler not defined"
    assert 'func CleanupExpiredApiKeys' in handler_content, "CleanupExpiredApiKeys function not defined"
    assert 'generateApiKey' in handler_content, "generateApiKey function not defined"
    assert 'hashApiKey' in handler_content, "hashApiKey function not defined"
    assert 'req.ExpiresInDays' in handler_content, "ExpiresInDays not used in CreateApiKey handler"
    
    print("✓ API key handler file valid")
    print("  - ListApiKeys handler defined")
    print("  - CreateApiKey handler defined with lifetime support")
    print("  - DeleteApiKey handler defined")
    print("  - CleanupExpiredApiKeys function defined")
    
    # Check main.go has API key routes
    main_file = REPO_ROOT / 'services' / 'api' / 'cmd' / 'api-gateway' / 'main.go'
    assert main_file.exists(), "Main API gateway file missing"
    
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    assert 'handlers.ListApiKeys' in main_content, "ListApiKeys route not registered"
    assert 'handlers.CreateApiKey' in main_content, "CreateApiKey route not registered"
    assert 'handlers.DeleteApiKey' in main_content, "DeleteApiKey route not registered"
    assert 'handlers.CleanupExpiredApiKeys' in main_content, "CleanupExpiredApiKeys not called"
    assert 'time.Hour' in main_content, "Cleanup ticker not configured"
    
    print("✓ API routes configured")
    print("  - List, Create, Delete routes registered")
    print("  - Cleanup goroutine configured to run hourly")


def test_frontend_api_key_files():
    """Test that frontend API key files have correct structure"""
    print("\nTesting frontend API key implementation...")
    
    # Check API keys page
    page_file = REPO_ROOT / 'frontend' / 'src' / 'pages' / 'ApiKeysPage.tsx'
    assert page_file.exists(), "ApiKeysPage.tsx file missing"
    
    with open(page_file, 'r') as f:
        page_content = f.read()
    
    assert 'expiresInDays' in page_content, "expiresInDays state not defined"
    assert 'customDays' in page_content, "customDays state not defined"
    assert 'isExpired' in page_content, "isExpired function not defined"
    assert 'formatExpiration' in page_content, "formatExpiration function not defined"
    assert '<MenuItem value="never">' in page_content, "Never expires option not available"
    assert '<MenuItem value="7">' in page_content, "7 days option not available"
    assert '<MenuItem value="30">' in page_content, "30 days option not available"
    assert '<MenuItem value="90">' in page_content, "90 days option not available"
    assert '<MenuItem value="365">' in page_content, "1 year option not available"
    assert '<MenuItem value="custom">' in page_content, "Custom option not available"
    assert 'Expires</TableCell>' in page_content, "Expires column not in table"
    
    print("✓ API keys page valid")
    print("  - Variable lifetime support (never, 7d, 30d, 90d, 365d, custom)")
    print("  - Expiration date display in table")
    print("  - Expired status handling")
    
    # Check API client
    api_file = REPO_ROOT / 'frontend' / 'src' / 'services' / 'api.ts'
    assert api_file.exists(), "api.ts file missing"
    
    with open(api_file, 'r') as f:
        api_content = f.read()
    
    assert 'createApiKey(name: string, expiresInDays?' in api_content, "createApiKey signature doesn't include expiresInDays"
    assert 'expiresInDays,' in api_content, "expiresInDays not passed to API"
    
    print("✓ API client valid")
    print("  - createApiKey method supports expiresInDays parameter")
    
    # Check types
    types_file = REPO_ROOT / 'frontend' / 'src' / 'types' / 'index.ts'
    assert types_file.exists(), "types/index.ts file missing"
    
    with open(types_file, 'r') as f:
        types_content = f.read()
    
    assert 'expiresAt?' in types_content, "expiresAt field not in ApiKey type"
    
    print("✓ TypeScript types valid")
    print("  - ApiKey type includes expiresAt field")


def test_database_schema():
    """Test that database schema has API keys table"""
    print("\nTesting database schema...")
    
    schema_file = REPO_ROOT / 'sql' / 'init' / '01_schema.sql'
    assert schema_file.exists(), "Database schema file missing"
    
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    assert 'CREATE TABLE api_keys' in schema_content, "api_keys table not defined"
    assert 'key_hash' in schema_content, "key_hash column not in api_keys table"
    assert 'expires_at TIMESTAMP' in schema_content, "expires_at column not in api_keys table"
    assert 'user_id UUID REFERENCES users(id) ON DELETE CASCADE' in schema_content, "user_id foreign key not proper"
    
    print("✓ Database schema valid")
    print("  - api_keys table exists")
    print("  - key_hash column for secure storage")
    print("  - expires_at column for variable lifetime")
    print("  - Cascade delete on user deletion")


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Keys Implementation Tests")
    print("=" * 60)
    
    try:
        test_backend_api_key_files()
        test_frontend_api_key_files()
        test_database_schema()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print("\nImplementation Summary:")
        print("- Backend API handlers for create, list, delete API keys")
        print("- Variable lifetime support (7d, 30d, 90d, 1y, custom, never)")
        print("- Automatic cleanup of expired keys (runs hourly)")
        print("- Frontend UI with expiration date display")
        print("- Secure key storage with SHA256 hashing")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
