#!/usr/bin/env python3
"""
OpenVINO GitHub Issues MCP Server

This MCP server provides tools to search and analyze OpenVINO GitHub issues.
It enables AI agents to help developers find relevant issues, understand bugs,
and navigate the OpenVINO issue tracker efficiently.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from enum import Enum
import httpx
import json
from datetime import datetime

# Initialize MCP server
mcp = FastMCP("openvino_mcp")

# Constants
GITHUB_API_BASE = "https://api.github.com"
OPENVINO_REPO = "openvinotoolkit/openvino"
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 30


# ============================================================================
# ENUMS AND MODELS
# ============================================================================

class IssueState(str, Enum):
    """State of GitHub issues."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class SortBy(str, Enum):
    """Sorting options for issues."""
    CREATED = "created"
    UPDATED = "updated"
    COMMENTS = "comments"


class SortOrder(str, Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# PYDANTIC INPUT MODELS
# ============================================================================

class SearchIssuesInput(BaseModel):
    """Input model for searching OpenVINO issues."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    query: str = Field(
        ...,
        description="Search query (e.g., 'segmentation fault', 'python API', 'performance')",
        min_length=1,
        max_length=200
    )
    state: IssueState = Field(
        default=IssueState.OPEN,
        description="Filter by issue state: 'open', 'closed', or 'all'"
    )
    labels: Optional[str] = Field(
        default=None,
        description="Comma-separated labels to filter by (e.g., 'bug,CPU')",
        max_length=100
    )
    sort: SortBy = Field(
        default=SortBy.CREATED,
        description="Sort results by: 'created', 'updated', or 'comments'"
    )
    order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order: 'asc' or 'desc'"
    )
    per_page: int = Field(
        default=DEFAULT_PER_PAGE,
        description="Number of results per page",
        ge=1,
        le=MAX_PER_PAGE
    )
    page: int = Field(
        default=1,
        description="Page number for pagination",
        ge=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )


class GetIssueDetailsInput(BaseModel):
    """Input model for getting issue details."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    issue_number: int = Field(
        ...,
        description="GitHub issue number (e.g., 12345)",
        ge=1
    )
    include_comments: bool = Field(
        default=False,
        description="Include issue comments in the response"
    )
    max_comments: int = Field(
        default=5,
        description="Maximum number of comments to include",
        ge=1,
        le=20
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )


class ListIssuesByLabelInput(BaseModel):
    """Input model for listing issues by label."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    labels: str = Field(
        ...,
        description="Comma-separated labels (e.g., 'bug', 'enhancement', 'bug,CPU')",
        min_length=1,
        max_length=100
    )
    state: IssueState = Field(
        default=IssueState.OPEN,
        description="Filter by issue state: 'open', 'closed', or 'all'"
    )
    sort: SortBy = Field(
        default=SortBy.CREATED,
        description="Sort results by: 'created', 'updated', or 'comments'"
    )
    order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order: 'asc' or 'desc'"
    )
    per_page: int = Field(
        default=DEFAULT_PER_PAGE,
        description="Number of results per page",
        ge=1,
        le=MAX_PER_PAGE
    )
    page: int = Field(
        default=1,
        description="Page number for pagination",
        ge=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_timestamp(timestamp_str: str) -> str:
    """Convert ISO timestamp to human-readable format."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return timestamp_str


def _handle_api_error(e: Exception) -> str:
    """Format API errors with actionable messages."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return "Error: Resource not found. Please check the issue number or repository is correct."
        elif e.response.status_code == 403:
            return "Error: API rate limit exceeded. Please wait a few minutes before making more requests."
        elif e.response.status_code == 422:
            return "Error: Invalid request parameters. Please check your input values."
        return f"Error: GitHub API request failed with status {e.response.status_code}. Details: {e.response.text}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Please try again."
    elif isinstance(e, httpx.RequestError):
        return f"Error: Network request failed. Please check your internet connection. Details: {str(e)}"
    return f"Error: Unexpected error occurred: {type(e).__name__} - {str(e)}"


def _format_issue_markdown(issue: dict) -> str:
    """Format a single issue as markdown."""
    labels = ', '.join([f"`{label['name']}`" for label in issue.get('labels', [])])
    
    markdown = f"""## #{issue['number']}: {issue['title']}

**State:** {issue['state'].upper()}  
**Author:** @{issue['user']['login']}  
**Created:** {_format_timestamp(issue['created_at'])}  
**Updated:** {_format_timestamp(issue['updated_at'])}  
**Comments:** {issue['comments']}  
**Labels:** {labels if labels else 'None'}

**URL:** {issue['html_url']}

**Description:**
{issue['body'][:500] if issue.get('body') else 'No description provided.'}{'...' if issue.get('body') and len(issue['body']) > 500 else ''}
"""
    return markdown


def _format_issues_list_markdown(issues: List[dict], total_count: int, page: int, per_page: int) -> str:
    """Format multiple issues as markdown list."""
    if not issues:
        return "No issues found matching your criteria."
    
    markdown = f"# OpenVINO Issues (Page {page})\n\n"
    markdown += f"**Total Results:** {total_count}  \n"
    markdown += f"**Showing:** {len(issues)} issues on page {page}  \n"
    markdown += f"**Has More:** {'Yes' if total_count > page * per_page else 'No'}\n\n"
    markdown += "---\n\n"
    
    for issue in issues:
        labels = ', '.join([f"`{label['name']}`" for label in issue.get('labels', [])])
        markdown += f"### #{issue['number']}: {issue['title']}\n"
        markdown += f"**State:** {issue['state']} | "
        markdown += f"**Comments:** {issue['comments']} | "
        markdown += f"**Updated:** {_format_timestamp(issue['updated_at'])}\n"
        if labels:
            markdown += f"**Labels:** {labels}\n"
        markdown += f"**URL:** {issue['html_url']}\n\n"
    
    if total_count > page * per_page:
        markdown += f"\n*Use `page: {page + 1}` to see more results*\n"
    
    return markdown


def _format_comment_markdown(comment: dict) -> str:
    """Format a single comment as markdown."""
    return f"""---
**Author:** @{comment['user']['login']}  
**Posted:** {_format_timestamp(comment['created_at'])}

{comment['body'][:300]}{'...' if len(comment['body']) > 300 else ''}
"""


# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool(
    name="search_openvino_issues",
    annotations={
        "title": "Search OpenVINO GitHub Issues",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def search_openvino_issues(params: SearchIssuesInput) -> str:
    """Search OpenVINO GitHub issues by keyword, labels, and filters.

    This tool searches the OpenVINO GitHub repository for issues matching
    your query. You can filter by state (open/closed), labels, and sort results.
    Perfect for finding relevant bugs, feature requests, or discussions.

    Args:
        params (SearchIssuesInput): Search parameters containing:
            - query (str): Search keywords (e.g., 'segmentation fault', 'python API')
            - state (IssueState): Filter by 'open', 'closed', or 'all' issues
            - labels (Optional[str]): Comma-separated labels to filter by
            - sort (SortBy): Sort by 'created', 'updated', or 'comments'
            - order (SortOrder): Sort order 'asc' or 'desc'
            - per_page (int): Number of results (1-30)
            - page (int): Page number for pagination
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Formatted search results with issue titles, numbers, states, labels, and URLs.
             In JSON format, returns structured data with pagination info.
    """
    try:
        # Build search query
        search_query = f"{params.query} repo:{OPENVINO_REPO} is:issue"
        
        if params.state != IssueState.ALL:
            search_query += f" state:{params.state.value}"
        
        if params.labels:
            label_list = [label.strip() for label in params.labels.split(',')]
            for label in label_list:
                search_query += f" label:{label}"
        
        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/search/issues",
                params={
                    "q": search_query,
                    "sort": params.sort.value,
                    "order": params.order.value,
                    "per_page": params.per_page,
                    "page": params.page
                },
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "OpenVINO-MCP-Server"
                }
            )
            response.raise_for_status()
            data = response.json()
        
        issues = data.get('items', [])
        total_count = data.get('total_count', 0)
        
        # Format response
        if params.response_format == ResponseFormat.JSON:
            result = {
                "total_count": total_count,
                "page": params.page,
                "per_page": params.per_page,
                "has_more": total_count > params.page * params.per_page,
                "issues": [
                    {
                        "number": issue['number'],
                        "title": issue['title'],
                        "state": issue['state'],
                        "url": issue['html_url'],
                        "author": issue['user']['login'],
                        "created_at": issue['created_at'],
                        "updated_at": issue['updated_at'],
                        "comments": issue['comments'],
                        "labels": [label['name'] for label in issue.get('labels', [])],
                        "body_preview": issue.get('body', '')[:200]
                    }
                    for issue in issues
                ]
            }
            return json.dumps(result, indent=2)
        else:
            return _format_issues_list_markdown(issues, total_count, params.page, params.per_page)
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="get_openvino_issue_details",
    annotations={
        "title": "Get OpenVINO Issue Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def get_openvino_issue_details(params: GetIssueDetailsInput) -> str:
    """Get complete details for a specific OpenVINO GitHub issue.

    This tool retrieves full information about an issue including its description,
    labels, assignees, milestone, and optionally recent comments. Use this when
    you need to deeply understand a specific issue.

    Args:
        params (GetIssueDetailsInput): Request parameters containing:
            - issue_number (int): GitHub issue number (e.g., 12345)
            - include_comments (bool): Whether to include comments
            - max_comments (int): Maximum comments to retrieve (1-20)
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Complete issue details including title, description, state, labels,
             assignees, timestamps, and optionally comments. In JSON format, returns
             fully structured data.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get issue details
            issue_response = await client.get(
                f"{GITHUB_API_BASE}/repos/{OPENVINO_REPO}/issues/{params.issue_number}",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "OpenVINO-MCP-Server"
                }
            )
            issue_response.raise_for_status()
            issue = issue_response.json()
            
            # Get comments if requested
            comments = []
            if params.include_comments and issue['comments'] > 0:
                comments_response = await client.get(
                    f"{GITHUB_API_BASE}/repos/{OPENVINO_REPO}/issues/{params.issue_number}/comments",
                    params={
                        "per_page": params.max_comments,
                        "sort": "created",
                        "direction": "desc"
                    },
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "OpenVINO-MCP-Server"
                    }
                )
                comments_response.raise_for_status()
                comments = comments_response.json()
        
        # Format response
        if params.response_format == ResponseFormat.JSON:
            result = {
                "number": issue['number'],
                "title": issue['title'],
                "state": issue['state'],
                "url": issue['html_url'],
                "author": issue['user']['login'],
                "created_at": issue['created_at'],
                "updated_at": issue['updated_at'],
                "closed_at": issue.get('closed_at'),
                "comments_count": issue['comments'],
                "labels": [label['name'] for label in issue.get('labels', [])],
                "assignees": [assignee['login'] for assignee in issue.get('assignees', [])],
                "milestone": issue.get('milestone', {}).get('title') if issue.get('milestone') else None,
                "body": issue.get('body', ''),
                "comments": [
                    {
                        "author": comment['user']['login'],
                        "created_at": comment['created_at'],
                        "body": comment['body']
                    }
                    for comment in comments
                ] if params.include_comments else []
            }
            return json.dumps(result, indent=2)
        else:
            markdown = _format_issue_markdown(issue)
            
            # Add assignees if present
            if issue.get('assignees'):
                assignees = ', '.join([f"@{a['login']}" for a in issue['assignees']])
                markdown += f"\n**Assignees:** {assignees}\n"
            
            # Add milestone if present
            if issue.get('milestone'):
                markdown += f"**Milestone:** {issue['milestone']['title']}\n"
            
            # Add comments if requested
            if params.include_comments and comments:
                markdown += f"\n## Recent Comments ({len(comments)} of {issue['comments']})\n"
                for comment in comments:
                    markdown += _format_comment_markdown(comment)
            
            return markdown
    
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="list_openvino_issues_by_label",
    annotations={
        "title": "List OpenVINO Issues by Label",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def list_openvino_issues_by_label(params: ListIssuesByLabelInput) -> str:
    """List OpenVINO GitHub issues filtered by specific labels.

    This tool helps you find issues tagged with specific labels like 'bug',
    'enhancement', 'documentation', 'CPU', 'GPU', etc. You can combine multiple
    labels to narrow down results.

    Args:
        params (ListIssuesByLabelInput): Request parameters containing:
            - labels (str): Comma-separated labels (e.g., 'bug', 'bug,CPU')
            - state (IssueState): Filter by 'open', 'closed', or 'all'
            - sort (SortBy): Sort by 'created', 'updated', or 'comments'
            - order (SortOrder): Sort order 'asc' or 'desc'
            - per_page (int): Number of results (1-30)
            - page (int): Page number for pagination
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: List of issues with the specified labels, including titles, numbers,
             states, and URLs. In JSON format, returns structured data with pagination.
    """
    try:
        # Parse labels
        label_list = [label.strip() for label in params.labels.split(',')]
        labels_param = ','.join(label_list)
        
        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{OPENVINO_REPO}/issues",
                params={
                    "labels": labels_param,
                    "state": params.state.value,
                    "sort": params.sort.value,
                    "direction": params.order.value,
                    "per_page": params.per_page,
                    "page": params.page
                },
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "OpenVINO-MCP-Server"
                }
            )
            response.raise_for_status()
            issues = response.json()
        
        # Note: GitHub's /repos/.../issues endpoint doesn't return total_count
        # We estimate based on returned results
        total_count = len(issues) if len(issues) < params.per_page else params.page * params.per_page + 1
        
        # Format response
        if params.response_format == ResponseFormat.JSON:
            result = {
                "labels_filter": label_list,
                "state": params.state.value,
                "page": params.page,
                "per_page": params.per_page,
                "results_count": len(issues),
                "has_more": len(issues) == params.per_page,
                "issues": [
                    {
                        "number": issue['number'],
                        "title": issue['title'],
                        "state": issue['state'],
                        "url": issue['html_url'],
                        "author": issue['user']['login'],
                        "created_at": issue['created_at'],
                        "updated_at": issue['updated_at'],
                        "comments": issue['comments'],
                        "labels": [label['name'] for label in issue.get('labels', [])],
                        "body_preview": issue.get('body', '')[:200]
                    }
                    for issue in issues
                ]
            }
            return json.dumps(result, indent=2)
        else:
            if not issues:
                return f"No {params.state.value} issues found with labels: {', '.join(label_list)}"
            
            markdown = f"# OpenVINO Issues with Labels: {', '.join([f'`{l}`' for l in label_list])}\n\n"
            markdown += f"**State:** {params.state.value}  \n"
            markdown += f"**Page:** {params.page}  \n"
            markdown += f"**Showing:** {len(issues)} issues  \n"
            markdown += f"**Has More:** {'Yes' if len(issues) == params.per_page else 'No'}\n\n"
            markdown += "---\n\n"
            
            for issue in issues:
                labels = ', '.join([f"`{label['name']}`" for label in issue.get('labels', [])])
                markdown += f"### #{issue['number']}: {issue['title']}\n"
                markdown += f"**State:** {issue['state']} | "
                markdown += f"**Comments:** {issue['comments']} | "
                markdown += f"**Updated:** {_format_timestamp(issue['updated_at'])}\n"
                markdown += f"**Labels:** {labels}\n"
                markdown += f"**URL:** {issue['html_url']}\n\n"
            
            if len(issues) == params.per_page:
                markdown += f"\n*Use `page: {params.page + 1}` to see more results*\n"
            
            return markdown
    
    except Exception as e:
        return _handle_api_error(e)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run with stdio transport (for local tools like Claude Code, Cursor)
    mcp.run()