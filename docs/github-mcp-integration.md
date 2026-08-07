# GitHub MCP Integration Guide

This guide explains how to use openDAW MCP with GitHub MCP server for autonomous repository operations.

## Overview

The GitHub MCP server enables AI agents to perform GitHub operations autonomously:
- Create branches
- Commit and push changes
- Create pull requests
- Manage issues
- Review code changes

## Quick Start

### 1. Install GitHub MCP Server

Install via npm globally.

### 2. Configure GitHub Token

Create a GitHub personal access token with required permissions and set it as environment variable GITHUB_TOKEN.

Recommended token scopes:
- repo - Full control of private repositories
- workflow - Update GitHub Actions workflows

### 3. Use with MCP Client

The mcp.json configuration is already set up with both opendaw and github servers.

## Example Workflows

### Autonomous Refactoring

Agent uses openDAW MCP to analyze code quality, refactor code, and run tests. Then uses GitHub MCP to create branch, commit changes, create pull request, and link to related issues.

### Automated Release Management

Agent uses openDAW MCP to export project and generate release notes. Then uses GitHub MCP to create release branch, tag release, create GitHub release, and update documentation.

### Issue-Driven Development

Agent uses GitHub MCP to fetch open issues and analyze requirements. Then uses openDAW MCP to implement solution and test implementation. Finally uses GitHub MCP to create PR, link to issue, and close issue when merged.

## Available GitHub MCP Tools

### Repository Operations
- create_branch - Create new branch
- delete_branch - Delete branch
- list_branches - List all branches

### Commit Operations
- create_commit - Commit changes
- list_commits - List commit history
- get_commit - Get commit details

### Pull Request Operations
- create_pull_request - Create new PR
- list_pull_requests - List open PRs
- get_pull_request - Get PR details
- merge_pull_request - Merge PR
- close_pull_request - Close PR

### Issue Operations
- create_issue - Create new issue
- list_issues - List issues
- get_issue - Get issue details
- update_issue - Update issue
- close_issue - Close issue
- add_issue_comment - Add comment to issue

### Code Review
- list_pull_request_files - List changed files
- get_pull_request_diff - Get PR diff
- create_pull_request_review - Create review
- add_pull_request_review_comment - Add review comment

## Security Considerations

### Token Permissions

Use fine-grained personal access tokens with minimal required permissions.

For read-only operations use repo:read and issues:read scopes.
For write operations use repo and workflow scopes.

### Token Storage

Never commit tokens to repository!

Use environment variables or secret managers (GitHub Secrets, AWS Secrets Manager, HashiCorp Vault).

### Token Rotation

Rotate tokens regularly (every 90 days).

## Troubleshooting

### GitHub MCP Server Won't Start

Verify Node.js is installed, check npm is available, install GitHub MCP server, verify GITHUB_TOKEN is set.

### Authentication Errors

Verify token is valid, check token hasn't expired, ensure token has required scopes, verify environment variable is set correctly.

### Rate Limiting

Wait for rate limit reset, use authenticated requests, implement request caching, use GitHub App for higher limits.

## Best Practices

### 1. Minimal Permissions
- Use least-privilege principle
- Create separate tokens for different purposes
- Regularly audit token permissions

### 2. Error Handling
- Implement retry logic for transient errors
- Log errors with context
- Provide clear error messages

### 3. Rate Limiting
- Cache API responses when possible
- Implement exponential backoff
- Monitor rate limit usage

### 4. Security
- Never log tokens
- Use environment variables
- Rotate tokens regularly
- Monitor token usage

## Related Resources

- MCP Specification: https://modelcontextprotocol.io/
- GitHub MCP Server: https://github.com/modelcontextprotocol/servers/tree/main/src/github
- GitHub REST API: https://docs.github.com/en/rest
- GitHub GraphQL API: https://docs.github.com/en/graphql

## Support

For issues or questions:
- GitHub Issues: https://github.com/ameobius-ai/opendaw-mcp/issues
- Discussions: https://github.com/ameobius-ai/opendaw-mcp/discussions
