# Kotlin Sample MCP STDIO Server

Based on the official MCP server samples:
https://github.com/modelcontextprotocol/kotlin-sdk

### Prerequisites
Mandatory:
- Claude for Desktop (need to sign up)
- `pip install flask` if you don't have flask installed

Recommended:
- Intellij IDEA 2025 Community Edition with Kotlin Plugin installed.

### How to run
Open Claude for Desktop > Settings > Developer

Add this to claude_desktop_config.json (use absolute path to run the jar)
```json
{
  "mcpServers": {
    "refund": {
      "command": "java",
      "args": [
        "-jar",
        "ABSOLUTEPATH/refund-stdio-server/build/libs/refund-stdio-server-0.1.0-all.jar"
      ]
    }
  }
}
```

Go to `src/python` directory

To make the refund email work, export your email and app password.
To generate app password, go to Google Account > Security > 2 Step Verification > App Passwords
```declarative
export REFUND_SMTP_EMAIL='someemail@gmail.com'
export REFUND_SMTP_PASSWORD='someapppassword'
```
Run the sample python server on localhost: `python app.py`

Run `./gradlew build` after any changes you made to the MCP Server code, and restart Claude for Desktop after each build to re-run the MCP server.

Also, remember that Claude has message limit per day in the free plan!