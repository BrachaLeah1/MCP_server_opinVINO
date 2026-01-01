# OpenVINO GitHub Issues MCP Server

A Model Context Protocol (MCP) server that provides AI agents with powerful tools to search and analyze OpenVINO GitHub issues. Perfect for helping developers navigate the OpenVINO issue tracker, find relevant bugs, and understand ongoing discussions.

## Features

### 🔍 Three Powerful Tools

1. **`search_openvino_issues`** - Search issues by keyword with advanced filtering
   - Search by any keyword (e.g., "segmentation fault", "python API")
   - Filter by state (open/closed/all)
   - Filter by labels
   - Sort by created, updated, or comment count
   - Pagination support

2. **`get_openvino_issue_details`** - Get complete details for any issue
   - Full issue description
   - Labels, assignees, milestones
   - Optional comments (up to 20 most recent)
   - All metadata (created/updated timestamps, state, etc.)

3. **`list_openvino_issues_by_label`** - Filter issues by specific labels
   - Find all bugs: `labels: "bug"`
   - Find CPU-related enhancements: `labels: "enhancement,CPU"`
   - Combine multiple labels
   - All standard filtering and sorting options

### 📊 Flexible Output Formats

- **Markdown**: Human-readable format perfect for AI agents
- **JSON**: Structured data for programmatic processing

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup
1. **clone this repository:**

```bash
git clone https://github.com/BrachaLeah1/MCP_server_opinVINO.git
```
   
2. **Create virtual environment:**

```bash
cd MCP_server_opinVINO
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Verify installation:**

```bash
python openvino_mcp.py --help
```

You should see the MCP server running successfully message.

## Testing Your MCP Server

### Option 1: MCP Inspector (Recommended for Testing)

The MCP Inspector is the best way to test your server locally:

```bash
# Install the inspector
npm install -g @modelcontextprotocol/inspector

# Run your server with the inspector
npx @modelcontextprotocol/inspector python openvino_mcp.py
```

This will open a web interface where you can:
- See all available tools
- Test each tool with different parameters
- View responses in real-time
- Debug any issues

### Option 2: Direct Testing with Python

You can also test tools directly:

```python
# Test search
python -c "
import asyncio
from openvino_mcp import search_openvino_issues, SearchIssuesInput

async def test():
    result = await search_openvino_issues(
        SearchIssuesInput(query='python API', per_page=5)
    )
    print(result)

asyncio.run(test())
"
```

## Integration with Coding Agents

### Claude Code

1. **Find your Claude Code config file:**
   ```bash
   # On Mac/Linux
   ~/.config/claude-code/config.json
   
   # On Windows
   %APPDATA%\claude-code\config.json
   ```

2. **Add the MCP server configuration:**

```json
{
  "mcpServers": {
    "openvino": {
      "command": "python",
      "args": ["/absolute/path/to/openvino_mcp.py"]
    }
  }
}
```

3. **Restart Claude Code**

4. **Test it:**
   ```
   You: "Search OpenVINO issues about segmentation faults"
   Claude: [uses the search_openvino_issues tool]
   ```

### Cursor

1. **Open Cursor Settings** → **MCP Servers**

2. **Add configuration:**
   - **Name**: `openvino`
   - **Command**: `python`
   - **Arguments**: `/absolute/path/to/openvino_mcp.py`

3. **Save and restart Cursor**

### Windsurf / Other MCP-Compatible Agents

Similar configuration pattern - check their documentation for MCP server setup.

## Usage Examples

### Example 1: Search for Python-related bugs

```python
Tool: search_openvino_issues
Parameters:
{
  "query": "python API",
  "state": "open",
  "labels": "bug",
  "per_page": 10
}
```

### Example 2: Get details of a specific issue

```python
Tool: get_openvino_issue_details
Parameters:
{
  "issue_number": 12345,
  "include_comments": true,
  "max_comments": 5
}
```

### Example 3: Find all open CPU-related bugs

```python
Tool: list_openvino_issues_by_label
Parameters:
{
  "labels": "bug,CPU",
  "state": "open",
  "sort": "updated",
  "order": "desc"
}
```

## How It Works

### Architecture

```
AI Agent (Claude Code, Cursor, etc.)
    ↓
MCP Protocol (stdio transport)
    ↓
openvino_mcp.py (FastMCP server)
    ↓
GitHub REST API
    ↓
OpenVINO Repository Data
```

### Key Components

1. **FastMCP Framework**: Handles MCP protocol communication
2. **Pydantic Models**: Validates all inputs with clear error messages
3. **httpx**: Async HTTP client for GitHub API calls
4. **GitHub API**: No authentication needed for public repository access

### Error Handling

The server provides helpful error messages:

- **404 Not Found**: "Resource not found. Please check the issue number..."
- **403 Forbidden**: "API rate limit exceeded. Please wait..."
- **422 Unprocessable**: "Invalid request parameters. Please check..."
- **Timeout**: "Request timed out. Please try again."

## API Rate Limits

GitHub API allows:
- **Unauthenticated**: 60 requests per hour per IP
- **Authenticated**: 5,000 requests per hour (not implemented in this version)

The server will inform you if you hit rate limits.

## Development

### Project Structure

```
openvino-mcp/
├── openvino_mcp.py      # Main MCP server
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Key Design Decisions

1. **No Authentication Required**: Uses public GitHub API for simplicity
2. **Dual Output Formats**: Supports both human-readable and machine-readable output
3. **Pagination**: All list endpoints support pagination to handle large result sets
4. **Error Recovery**: Comprehensive error handling with actionable messages
5. **Type Safety**: Full Pydantic validation for all inputs

### Extending the Server

To add more tools:

1. **Define Pydantic input model:**
```python
class NewToolInput(BaseModel):
    param1: str = Field(..., description="Parameter description")
```

2. **Register the tool:**
```python
@mcp.tool(name="new_tool_name", annotations={...})
async def new_tool(params: NewToolInput) -> str:
    # Implementation
    pass
```

## Troubleshooting

### Server won't start

```bash
# Check Python version (must be 3.10+)
python --version

# Verify all dependencies are installed
pip list | grep -E "mcp|httpx|pydantic"

# Try running with verbose output
python openvino_mcp.py 2>&1
```

### Tools not appearing in agent

1. Check server configuration path is absolute
2. Restart the coding agent completely
3. Check agent logs for MCP connection errors

### API rate limit errors

- Wait 1 hour for limit reset
- Consider implementing GitHub authentication (add token to API calls)
- Reduce number of requests by using pagination wisely

## Contributing

Improvements welcome! Areas for enhancement:

- [ ] Add GitHub authentication for higher rate limits
- [ ] Add tool to list available labels
- [ ] Add tool to search by assignee
- [ ] Add caching to reduce API calls
- [ ] Add tool to get issue timeline/events
- [ ] Support for GitHub Projects integration

## License

MIT License - feel free to use and modify!

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [GitHub REST API](https://docs.github.com/en/rest)
- [OpenVINO Repository](https://github.com/openvinotoolkit/openvino)

## Support

For issues with:
- **This MCP server**: Open an issue in this repository
- **OpenVINO itself**: Visit the [OpenVINO repository](https://github.com/openvinotoolkit/openvino)
- **MCP protocol**: See [MCP Documentation](https://modelcontextprotocol.io/)

---

**Built with ❤️ for the OpenVINO developer community**
