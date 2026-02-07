"""Jira REST API client — fetches issues, comments, epics, and subtasks."""

import requests
from mapper import adf_to_markdown


class JiraClient:
    def __init__(self, base_url, email, api_token):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})

    def fetch_all_issues(self, project_key):
        """Fetch all issues for a project, handling pagination. Returns a list of issues."""
        jql = f"project={project_key} ORDER BY created ASC"
        issues = []
        start_at = 0
        max_results = 100

        while True:
            resp = self.session.get(
                f"{self.base_url}/rest/api/3/search",
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "summary,description,status,priority,issuetype,parent,labels,subtasks,comment",
                    "expand": "names",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            batch = data.get("issues", [])
            issues.extend(batch)

            total = data.get("total", 0)
            start_at += len(batch)
            if start_at >= total or not batch:
                break

        return issues

    def fetch_comments(self, issue_key):
        """Fetch all comments for an issue."""
        comments = []
        start_at = 0

        while True:
            resp = self.session.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                params={"startAt": start_at, "maxResults": 100},
            )
            resp.raise_for_status()
            data = resp.json()

            batch = data.get("comments", [])
            comments.extend(batch)

            total = data.get("total", 0)
            start_at += len(batch)
            if start_at >= total or not batch:
                break

        return comments

    def parse_issue(self, raw_issue):
        """Parse a raw Jira issue into a normalized dict."""
        fields = raw_issue["fields"]
        key = raw_issue["key"]

        description_adf = fields.get("description")
        description_md = adf_to_markdown(description_adf) if description_adf else ""

        parent_key = None
        parent_field = fields.get("parent")
        if parent_field:
            parent_key = parent_field.get("key")

        subtask_keys = []
        for sub in fields.get("subtasks") or []:
            subtask_keys.append(sub["key"])

        issue_type = (fields.get("issuetype") or {}).get("name", "Task")
        status = (fields.get("status") or {}).get("name", "To Do")
        priority = (fields.get("priority") or {}).get("name", "Medium")

        return {
            "key": key,
            "summary": fields.get("summary", ""),
            "description": description_md,
            "issue_type": issue_type,
            "status": status,
            "priority": priority,
            "labels": fields.get("labels") or [],
            "parent_key": parent_key,
            "subtask_keys": subtask_keys,
            "fields": fields,
        }

    def parse_comment(self, raw_comment):
        """Parse a raw Jira comment into a normalized dict."""
        body_adf = raw_comment.get("body")
        body_md = adf_to_markdown(body_adf) if body_adf else ""
        author = (raw_comment.get("author") or {}).get("displayName", "Unknown")
        created = raw_comment.get("created", "")

        return {
            "author": author,
            "created": created,
            "body": body_md,
        }
