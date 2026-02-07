"""GitHub REST + GraphQL API client — creates issues, labels, comments, and manages Projects."""

import time
import requests


class GitHubClient:
    def __init__(self, token, repo):
        self.token = token
        self.owner, self.repo_name = repo.split("/")
        self.rest_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
        self.graphql_url = "https://api.github.com/graphql"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        self._existing_labels = None
        self._project_id = None

    # --- Labels ---

    def get_existing_labels(self):
        """Fetch all existing labels from the repo."""
        if self._existing_labels is not None:
            return self._existing_labels

        labels = {}
        page = 1
        while True:
            resp = self._request("GET", f"{self.rest_url}/labels", params={"page": page, "per_page": 100})
            batch = resp.json()
            if not batch:
                break
            for lbl in batch:
                labels[lbl["name"]] = lbl
            page += 1

        self._existing_labels = labels
        return labels

    def ensure_label(self, name, color):
        """Create a label if it doesn't already exist."""
        existing = self.get_existing_labels()
        if name in existing:
            return existing[name]

        resp = self._request(
            "POST",
            f"{self.rest_url}/labels",
            json={"name": name, "color": color},
        )
        label = resp.json()
        self._existing_labels[name] = label
        return label

    # --- Issues ---

    def create_issue(self, title, body, labels=None):
        """Create a GitHub issue. Returns the created issue data."""
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        resp = self._request("POST", f"{self.rest_url}/issues", json=payload)
        return resp.json()

    def add_comment(self, issue_number, body):
        """Add a comment to an existing issue."""
        resp = self._request(
            "POST",
            f"{self.rest_url}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return resp.json()

    # --- GitHub Projects (V2) via GraphQL ---

    def get_project_id(self, project_number):
        """Get the node ID of a GitHub Project V2 by number."""
        if self._project_id:
            return self._project_id

        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        variables = {"owner": self.owner, "number": project_number}
        result = self._graphql(query, variables)

        project = result.get("data", {}).get("user", {}).get("projectV2")
        if not project:
            query_org = """
            query($owner: String!, $number: Int!) {
              organization(login: $owner) {
                projectV2(number: $number) {
                  id
                }
              }
            }
            """
            result = self._graphql(query_org, variables)
            project = result.get("data", {}).get("organization", {}).get("projectV2")

        if not project:
            raise RuntimeError(
                f"Could not find GitHub Project #{project_number} for '{self.owner}'. "
                "Make sure the project exists and the token has 'project' scope."
            )

        self._project_id = project["id"]
        return self._project_id

    def add_issue_to_project(self, project_id, issue_node_id):
        """Add an issue to a GitHub Project V2."""
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        variables = {"projectId": project_id, "contentId": issue_node_id}
        return self._graphql(mutation, variables)

    def update_project_item_status(self, project_id, item_id, status_field_id, status_option_id):
        """Update the status field of a project item."""
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: {singleSelectOptionId: $optionId}
          }) {
            projectV2Item { id }
          }
        }
        """
        variables = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": status_field_id,
            "optionId": status_option_id,
        }
        return self._graphql(mutation, variables)

    def get_project_status_field(self, project_id):
        """Get the Status field ID and its options from a project."""
        query = """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options { id name }
                  }
                }
              }
            }
          }
        }
        """
        result = self._graphql(query, {"projectId": project_id})
        fields = result.get("data", {}).get("node", {}).get("fields", {}).get("nodes", [])

        for field in fields:
            if field.get("name") == "Status":
                options = {opt["name"]: opt["id"] for opt in field.get("options", [])}
                return field["id"], options

        return None, {}

    # --- Helpers ---

    def _request(self, method, url, **kwargs):
        """Make an HTTP request with rate-limit handling."""
        resp = self.session.request(method, url, **kwargs)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
            wait = max(reset_time - int(time.time()), 1)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            resp = self.session.request(method, url, **kwargs)

        if resp.status_code == 422:
            print(f"  Warning: {resp.json().get('message', resp.text)}")
            return resp

        resp.raise_for_status()
        return resp

    def _graphql(self, query, variables):
        """Execute a GraphQL query against the GitHub API."""
        resp = self.session.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            errors = data["errors"]
            msgs = [e.get("message", str(e)) for e in errors]
            print(f"  GraphQL warnings: {'; '.join(msgs)}")

        return data
