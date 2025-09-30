# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python utility project for working with Feishu (飞书) API and Bitable (多维表格) integration. The codebase consists of several scripts that help convert Feishu Wiki node tokens to Bitable app tokens and perform various API operations.

## Key Scripts and Their Purpose

### wiki2bitable.py
- **Purpose**: Converts Feishu Wiki node tokens to Bitable app tokens
- **Usage**:
  - With existing token: `export TENANT_ACCESS_TOKEN="t-xxxxx"` and `python wiki2bitable.py --wiki-url "https://xxx.feishu.cn/wiki/<node>?table=<table>"`
  - With app credentials: `export FEISHU_APP_ID="cli_xxx"` and `export FEISHU_APP_SECRET="xxx"` and `python wiki2bitable.py --node "<node_token>" --table-id "<table_id>"`
- **Key Functions**: Extracts node tokens from URLs, gets wiki node info, validates Bitable base metadata, and optionally verifies table existence

### bitable_check.py
- **Purpose**: Bitable connectivity testing and record creation
- **Usage**: `python bitable_check.py --app-token <token> --table-id <table_id> [--create]`
- **Key Functions**: Tests base connectivity, lists tables, creates test records with --create flag

### env_run.py
- **Purpose**: Environment variable injection wrapper for scripts
- **Usage**: `python env_run.py <config.json> <script.py> [--event mock_event.json] [args...]`
- **Key Functions**: Loads config file as environment variables, masks sensitive values in output, runs target script with injected environment

## Configuration

### config.local.json
Contains Feishu API credentials:
- `FEISHU_APP_ID`: Application ID for Feishu API access
- `FEISHU_APP_SECRET`: Application secret for authentication
- `FEISHU_APP_TOKEN`: Bitable app token
- `FEISHU_TABLE_ID`: Target table ID in Bitable

### mock_event.json
Sample GitHub webhook event structure used for testing issue data parsing.

## Development Workflow

### Common Commands
```bash
# Test wiki to bitable conversion
python env_run.py config.local.json wiki2bitable.py --node "<node_token>"

# Test bitable connectivity
python env_run.py config.local.json bitable_check.py --app-token <token> --table-id <table_id>

# Create test record
python env_run.py config.local.json bitable_check.py --app-token <token> --table-id <table_id> --create
```

### Environment Setup
- Use `env_run.py` to inject credentials from `config.local.json` instead of setting environment variables directly
- The script automatically masks sensitive values in output for security
- All Feishu API scripts require either `TENANT_ACCESS_TOKEN` or `FEISHU_APP_ID`/`FEISHU_APP_SECRET`

## API Integration Notes

### Feishu API Endpoints Used
- Wiki API: `https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node`
- Bitable API: `https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}`
- Authentication: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`

### Common Error Patterns
- Cross-tenant permission issues when accessing Bitable bases
- Invalid node tokens or mismatched wiki/Bitable relationships
- Missing or expired access tokens
- Table ID validation failures

## Code Patterns

### Authentication Flow
1. Check for existing `TENANT_ACCESS_TOKEN`
2. If missing, use `FEISHU_APP_ID`/`FEISHU_APP_SECRET` to obtain token
3. All API calls use Bearer token authentication

### Error Handling
- Scripts exit with specific error codes (1-6) for different failure modes
- JSON responses are parsed with try/catch fallbacks
- Chinese error messages for developer convenience

### Security Considerations
- Sensitive values are masked in console output
- Credentials loaded from config files rather than hardcoded
- Environment variable injection is isolated to subprocess execution