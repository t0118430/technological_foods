#!/usr/bin/env python3
"""Jira to GitHub migration tool — imports issues, comments, epics, subtasks into GitHub Issues + Project board."""

import argparse
import os
import sys
import time

from dotenv import load_dotenv
from jira_client import JiraClient
from github_client import GitHubClient
from mapper import get_labels_for_issue, get_project_status, get_all_label_definitions


def main():
    parser = argparse.ArgumentParser(description="Migrate Jira issues to GitHub Issues + Project board")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without creating anything")
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    args = parser.parse_args()

    # Load config
    load_dotenv(args.env)
    jira_url = os.getenv("JIRA_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")
    jira_project = os.getenv("JIRA_PROJECT_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPO")
    project_number = int(os.getenv("GITHUB_PROJECT_NUMBER", "0"))

    missing = []
    for name, val in [
        ("JIRA_URL", jira_url),
        ("JIRA_EMAIL", jira_email),
        ("JIRA_API_TOKEN", jira_token),
        ("JIRA_PROJECT_KEY", jira_project),
        ("GITHUB_TOKEN", github_token),
        ("GITHUB_REPO", github_repo),
    ]:
        if not val:
            missing.append(name)
    if missing:
        print(f"Error: Missing required env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Jira -> GitHub Migration")
    print(f"  Jira: {jira_url} (project: {jira_project})")
    print(f"  GitHub: {github_repo}")
    if project_number:
        print(f"  GitHub Project: #{project_number}")
    print()

    # Initialize clients
    jira = JiraClient(jira_url, jira_email, jira_token)
    gh = GitHubClient(github_token, github_repo)

    # Step 1: Fetch all Jira issues
    print("Fetching Jira issues...")
    raw_issues = jira.fetch_all_issues(jira_project)
    print(f"  Found {len(raw_issues)} issues")

    # Parse issues
    issues = [jira.parse_issue(raw) for raw in raw_issues]

    # Step 2: Sort — epics first, then tasks/stories, then subtasks
    type_order = {"Epic": 0, "Story": 1, "Task": 1, "Bug": 1, "Sub-task": 2, "Subtask": 2}
    issues.sort(key=lambda i: type_order.get(i["issue_type"], 1))

    # Step 3: Create GitHub labels
    print("Ensuring GitHub labels exist...")
    label_defs = get_all_label_definitions()
    if not args.dry_run:
        for label_name, color in label_defs.items():
            gh.ensure_label(label_name, color)
            print(f"  Label: {label_name}")
    else:
        for label_name in label_defs:
            print(f"  [DRY RUN] Would create label: {label_name}")

    # Step 4: Get project info
    project_id = None
    status_field_id = None
    status_options = {}
    if project_number and not args.dry_run:
        print("Fetching GitHub Project info...")
        project_id = gh.get_project_id(project_number)
        status_field_id, status_options = gh.get_project_status_field(project_id)
        print(f"  Project ID: {project_id}")
        print(f"  Status options: {list(status_options.keys())}")

    # Step 5: Create issues
    print("\nCreating GitHub issues...")
    jira_to_github = {}  # jira_key -> github_issue_number
    jira_to_node_id = {}  # jira_key -> github_node_id
    stats = {"issues": 0, "comments": 0, "project_items": 0, "errors": 0}

    for issue in issues:
        key = issue["key"]
        labels = get_labels_for_issue(issue["fields"])

        # Build issue body
        body_parts = [f"**Imported from Jira: {key}**"]
        body_parts.append(f"**Type:** {issue['issue_type']}")
        body_parts.append(f"**Status:** {issue['status']}")
        body_parts.append(f"**Priority:** {issue['priority']}")

        if issue["parent_key"] and issue["parent_key"] in jira_to_github:
            parent_num = jira_to_github[issue["parent_key"]]
            body_parts.append(f"**Parent:** #{parent_num} ({issue['parent_key']})")
        elif issue["parent_key"]:
            body_parts.append(f"**Parent:** {issue['parent_key']}")

        if issue["subtask_keys"]:
            body_parts.append(f"**Subtasks:** {', '.join(issue['subtask_keys'])}")

        body_parts.append("")
        body_parts.append("---")
        body_parts.append("")
        body_parts.append(issue["description"])

        body = "\n".join(body_parts)
        title = f"[{key}] {issue['summary']}"

        if args.dry_run:
            print(f"  [DRY RUN] Would create: {title}")
            print(f"            Labels: {labels}")
            jira_to_github[key] = 0
            stats["issues"] += 1
            continue

        try:
            gh_issue = gh.create_issue(title, body, labels)
            issue_number = gh_issue["number"]
            node_id = gh_issue["node_id"]
            jira_to_github[key] = issue_number
            jira_to_node_id[key] = node_id
            stats["issues"] += 1
            print(f"  Created #{issue_number}: {title}")

            # Fetch and add comments
            raw_comments = jira.fetch_comments(key)
            for raw_comment in raw_comments:
                comment = jira.parse_comment(raw_comment)
                comment_body = f"**{comment['author']}** ({comment['created']}):\n\n{comment['body']}"

                gh.add_comment(issue_number, comment_body)
                stats["comments"] += 1
                print(f"    Comment by {comment['author']}")

            # Add to project
            if project_id and node_id:
                result = gh.add_issue_to_project(project_id, node_id)
                item_data = result.get("data", {}).get("addProjectV2ItemById", {}).get("item", {})
                item_id = item_data.get("id")

                if item_id and status_field_id:
                    target_status = get_project_status(issue["status"])
                    if target_status in status_options:
                        gh.update_project_item_status(
                            project_id, item_id, status_field_id, status_options[target_status]
                        )

                stats["project_items"] += 1
                print(f"    Added to project board")

            # Small delay to respect rate limits
            time.sleep(0.5)

        except Exception as e:
            print(f"  ERROR creating {key}: {e}")
            stats["errors"] += 1

    # Summary
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"  {prefix}Issues created: {stats['issues']}")
    print(f"  {prefix}Comments added: {stats['comments']}")
    print(f"  {prefix}Project items added: {stats['project_items']}")
    if stats["errors"]:
        print(f"  Errors: {stats['errors']}")
    print()

    if args.dry_run:
        print("This was a dry run. Run without --dry-run to execute the migration.")


if __name__ == "__main__":
    main()
