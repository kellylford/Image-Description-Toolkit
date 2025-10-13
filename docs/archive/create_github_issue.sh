#!/bin/bash
# Create GitHub issue for Claude API Key bug

gh issue create \
  --title "Claude API Key Configuration Fails in Guideme" \
  --body-file ISSUE_CLAUDE_API_KEY.md \
  --label "bug,high-priority,provider-claude" \
  --assignee "@me"
