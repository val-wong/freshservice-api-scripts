import requests
import base64
import json

API_KEY = os.getenv("FRESH_API_KEY")
TICKET_URL = os.getenv("TICKET_URL")
KNOWLEDGE_BASE_URL = os.getenv("KNOWLEDGE_BASE_URL")
FOLDER_ID = int(os.getenv("FOLDER_ID", 0))  
GROUP_ID = int(os.getenv("GROUP_ID", 0))  

def create_ticket(subject, description, group_id=None, tags=None):
    try:
        encoded_auth = base64.b64encode(f"{API_KEY}:X".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        ticket_data = {
            "subject": subject,
            "description": description,
            "priority": 1,
            "status": 2,
            "source": 2,
        }

        if group_id:
            ticket_data["group_id"] = group_id

        if tags:
            ticket_data["tags"] = tags

        response = requests.post(TICKET_URL, headers=headers, json=ticket_data)

        if response.status_code == 201:
            return {"status": "success", "message": f"Ticket created: {subject}"}
        else:
            return {"status": "error", "message": f"Failed to create ticket: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def create_knowledge_article(article_title, article_content):
    try:
        encoded_auth = base64.b64encode(f"{API_KEY}:X".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        modified_title = f"Access to {article_title}"  # Prepend "Access to" to article title

        article_data = {
            "title": modified_title,
            "description": article_content,
            "folder_id": FOLDER_ID,  
            "status": 1  
        }

        response = requests.post(KNOWLEDGE_BASE_URL, headers=headers, json=article_data)

        if response.status_code in [200, 201]:
            article_id = response.json().get("article", {}).get("id")  # Extract article ID
            return {
                "status": "success",
                "message": f"Knowledge article created: {modified_title}",
                "article_url": article_url
            }
        else:
            return {"status": "error", "message": f"Failed to create knowledge article: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_changes(changes):
    if not changes:
        return {"status": "error", "message": "Empty payload received"}

    results = []
    for change in changes:
        article_title = change.get("title")
        article_content = change.get("content")
        article_url = change.get("url")
        status = change.get("status")

        if not article_title or not status:
            continue

        if status.lower() == "new":
            article_result = create_knowledge_article(article_title, article_content)
            actual_article_url = article_result.get("article_url", KNOWLEDGE_BASE_URL)  

            ticket_result = create_ticket(
                subject=f"New Knowledge Article Created: {article_title}",
                description=f"A new knowledge article has been created.\n\n"
                            f"Title: {article_title}\n"
                            f"URL: {article_url}\n\n"
                            f"Review the article and update as needed in Freshservice - {actual_article_url}",
                group_id=GROUP_ID,  
                tags=["freshservice_kb"]
            )
            results.extend([article_result, ticket_result])
        elif "updated" in status.lower():
            ticket_result = create_ticket(
                subject=f"Knowledge Article Updated: {article_title}",
                description=f"The knowledge article '{article_title}' has been updated.\n\n"
                            f"URL: {article_url}\n\n"
                            f"Review the updates in Freshservice - {actual_article_url}",
                group_id=GROUP_ID,
                tags=["freshservice_kb"]
            )
            results.append(ticket_result)
        elif status.lower() in ["delete", "deleted"]:
            ticket_result = create_ticket(
                subject=f"Knowledge Article Deleted: {article_title}",
                description=f"The knowledge article '{article_title}' has been deleted.\n\n"
                            f"URL: {article_url}\n\n"
                            f"Ensure it has been properly archived or removed in Freshservice - {actual_article_url}",
                group_id=GROUP_ID,
                tags=["freshservice_kb"]
            )
            results.append(ticket_result)

    return {"status": "success", "message": "Changes processed successfully", "results": results}

def main():
    try:
        payload = {{ $.event }}
        result = handle_changes(payload)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    print(main())
