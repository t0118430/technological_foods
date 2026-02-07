"""Maps Jira fields to GitHub labels, statuses, and issue body formatting."""

PRIORITY_MAP = {
    "Highest": {"label": "priority:critical", "color": "b60205"},
    "High": {"label": "priority:high", "color": "d93f0b"},
    "Medium": {"label": "priority:medium", "color": "fbca04"},
    "Low": {"label": "priority:low", "color": "0e8a16"},
    "Lowest": {"label": "priority:lowest", "color": "c5def5"},
}

ISSUE_TYPE_MAP = {
    "Epic": {"label": "type:epic", "color": "8b5cf6"},
    "Story": {"label": "type:story", "color": "3b82f6"},
    "Task": {"label": "type:task", "color": "6366f1"},
    "Bug": {"label": "type:bug", "color": "ef4444"},
    "Sub-task": {"label": "type:subtask", "color": "a78bfa"},
    "Subtask": {"label": "type:subtask", "color": "a78bfa"},
}

STATUS_MAP = {
    "To Do": "Todo",
    "Open": "Todo",
    "Backlog": "Todo",
    "In Progress": "In Progress",
    "In Review": "In Progress",
    "Done": "Done",
    "Closed": "Done",
    "Resolved": "Done",
}


def get_labels_for_issue(issue_fields):
    """Return a list of GitHub label names for a Jira issue."""
    labels = []

    priority_name = (issue_fields.get("priority") or {}).get("name")
    if priority_name and priority_name in PRIORITY_MAP:
        labels.append(PRIORITY_MAP[priority_name]["label"])

    type_name = (issue_fields.get("issuetype") or {}).get("name")
    if type_name and type_name in ISSUE_TYPE_MAP:
        labels.append(ISSUE_TYPE_MAP[type_name]["label"])

    jira_labels = issue_fields.get("labels") or []
    for lbl in jira_labels:
        labels.append(f"jira:{lbl}")

    return labels


def get_project_status(jira_status_name):
    """Map a Jira status name to a GitHub Project column status."""
    return STATUS_MAP.get(jira_status_name, "Todo")


def get_all_label_definitions():
    """Return all label definitions that need to be created on GitHub."""
    labels = {}
    for entry in PRIORITY_MAP.values():
        labels[entry["label"]] = entry["color"]
    for entry in ISSUE_TYPE_MAP.values():
        labels[entry["label"]] = entry["color"]
    return labels


def adf_to_markdown(adf_node):
    """Convert Jira's Atlassian Document Format (ADF) to Markdown."""
    if adf_node is None:
        return ""
    if isinstance(adf_node, str):
        return adf_node

    node_type = adf_node.get("type", "")
    content = adf_node.get("content", [])
    attrs = adf_node.get("attrs", {})

    if node_type == "doc":
        return "\n\n".join(_convert_children(content))

    if node_type == "paragraph":
        return "".join(_convert_children(content))

    if node_type == "heading":
        level = attrs.get("level", 1)
        prefix = "#" * level
        return f"{prefix} " + "".join(_convert_children(content))

    if node_type == "bulletList":
        items = []
        for item in content:
            text = "".join(_convert_children(item.get("content", [])))
            items.append(f"- {text}")
        return "\n".join(items)

    if node_type == "orderedList":
        items = []
        for i, item in enumerate(content, 1):
            text = "".join(_convert_children(item.get("content", [])))
            items.append(f"{i}. {text}")
        return "\n".join(items)

    if node_type == "codeBlock":
        lang = attrs.get("language", "")
        code = "".join(_convert_children(content))
        return f"```{lang}\n{code}\n```"

    if node_type == "blockquote":
        text = "\n\n".join(_convert_children(content))
        return "\n".join(f"> {line}" for line in text.split("\n"))

    if node_type == "rule":
        return "---"

    if node_type == "table":
        return _convert_table(content)

    if node_type == "text":
        text = adf_node.get("text", "")
        marks = adf_node.get("marks", [])
        for mark in marks:
            mark_type = mark.get("type", "")
            if mark_type == "strong":
                text = f"**{text}**"
            elif mark_type == "em":
                text = f"*{text}*"
            elif mark_type == "code":
                text = f"`{text}`"
            elif mark_type == "strike":
                text = f"~~{text}~~"
            elif mark_type == "link":
                href = mark.get("attrs", {}).get("href", "")
                text = f"[{text}]({href})"
        return text

    if node_type == "hardBreak":
        return "\n"

    if node_type == "mention":
        return f"@{attrs.get('text', attrs.get('id', 'unknown'))}"

    if node_type == "emoji":
        return attrs.get("shortName", "")

    if node_type == "inlineCard":
        url = attrs.get("url", "")
        return f"[{url}]({url})" if url else ""

    if node_type == "mediaGroup" or node_type == "mediaSingle":
        parts = []
        for child in content:
            if child.get("type") == "media":
                alt = child.get("attrs", {}).get("alt", "attachment")
                parts.append(f"[{alt}]")
        return " ".join(parts) if parts else ""

    return "".join(_convert_children(content))


def _convert_children(children):
    return [adf_to_markdown(child) for child in children]


def _convert_table(rows):
    if not rows:
        return ""
    md_rows = []
    for row in rows:
        cells = row.get("content", [])
        cell_texts = []
        for cell in cells:
            text = " ".join(_convert_children(cell.get("content", [])))
            cell_texts.append(text.replace("|", "\\|"))
        md_rows.append("| " + " | ".join(cell_texts) + " |")

    if len(md_rows) > 0:
        col_count = md_rows[0].count("|") - 1
        separator = "| " + " | ".join(["---"] * col_count) + " |"
        md_rows.insert(1, separator)

    return "\n".join(md_rows)
