import requests
import base64
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("FRESH_API_KEY")
TICKET_URL = os.getenv("TICKET_URL")
KNOWLEDGE_BASE_URL = os.getenv("KNOWLEDGE_BASE_URL")
FOLDER_ID = int(os.getenv("FOLDER_ID", 0))  
GROUP_ID = int(os.getenv("GROUP_ID", 0))   

def create_ticket(subject, description, tags=None):
    """Creates a ticket in Freshservice."""
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
            "group_id": GROUP_ID
        }

        if tags:
            ticket_data["tags"] = tags

        response = requests.post(TICKET_URL, headers=headers, json=ticket_data)

        if response.status_code == 201:
            return {"status": "success", "message": f"Ticket created: {subject}"}
        else:
            return {"status": "error", "message": f"Failed to create ticket: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def create_knowledge_article(article_title, article_url):
    """Creates a new knowledge article in Freshservice and ensures it is published."""
    try:
        encoded_auth = base64.b64encode(f"{API_KEY}:X".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        formatted_content = (
            f"<p>{article_title} is now handled via "
        )

        article_data = {
            "title": article_title,
            "description": formatted_content,
            "folder_id": FOLDER_ID,  
            "status": 1  
        }

        response = requests.post(KNOWLEDGE_BASE_URL, headers=headers, json=article_data)

        if response.status_code in [200, 201]:
            article_json = response.json()
            article_id = article_json.get("article", {}).get("id")  

            return {
                "status": "success",
                "message": f"Knowledge article created: {article_title}",
                "article_url": article_link
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to create knowledge article: {response.text}"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_article_id(article_title):
    """Fetches the article ID based on the exact title from Freshservice."""
    try:
        encoded_auth = base64.b64encode(f"{API_KEY}:X".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        page = 1
        while True:
            response = requests.get(f"{KNOWLEDGE_BASE_URL}?folder_id={FOLDER_ID}&per_page=100&page={page}", headers=headers)

            if response.status_code == 200:
                articles = response.json().get("articles", [])
                for article in articles:
                    if article["title"].strip().lower() == article_title.strip().lower():
                        return article["id"]

                if len(articles) < 100:
                    break  
                page += 1
            else:
                return None

        return None
    except Exception as e:
        return None

def delete_knowledge_article(article_title):
    """Deletes a knowledge article from Freshservice."""
    try:
        article_id = get_article_id(article_title)

        if not article_id:
            return {"status": "error", "message": f"Article '{article_title}' not found, cannot delete."}

        encoded_auth = base64.b64encode(f"{API_KEY}:X".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        delete_url = f"{KNOWLEDGE_BASE_URL}/{article_id}"
        response = requests.delete(delete_url, headers=headers)

        if response.status_code == 204:
            return {
                "status": "success",
                "message": f"Knowledge article '{article_title}' deleted",
            }
        elif response.status_code == 403:
            return {
                "status": "error",
                "message": f"Permission denied. Cannot delete article '{article_title}'. Check Freshservice API permissions."
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to delete article '{article_title}': {response.text}"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_changes(changes):
    if not changes:
        return {"status": "error", "message": "Empty payload received"}

    results = []
    for change in changes:
        article_title = change.get("title").strip()  
        article_url = change.get("url")
        status = change.get("status")

        if not article_title or not status:
            continue

        actual_article_url = KNOWLEDGE_BASE_URL  

        if status.lower() == "new":
            article_result = create_knowledge_article(article_title, article_url)
            actual_article_url = article_result.get("article_url", KNOWLEDGE_BASE_URL)  

            ticket_result = create_ticket(
                subject=f"New Knowledge Article Created: {article_title}",
                description=(
                    f"A new knowledge article has been created.\n\n"
                    f"Title: {article_title}\n"
                    f"URL: {article_url}\n\n"
                    f"Review the article and update as needed in Freshservice - {actual_article_url}"
                ),
                tags=["freshservice_kb"]
            )
            results.extend([article_result, ticket_result])

        elif "updated" in status.lower():
            ticket_result = create_ticket(
                subject=f"Knowledge Article Updated: {article_title}",
                description=(
                    f"The knowledge article '{article_title}' has been updated.\n\n"
                    f"URL: {article_url}\n\n"
                    f"Review the updates in Freshservice - {actual_article_url}"
                ),
                tags=["freshservice_kb"]
            )
            results.append(ticket_result)

        elif status.lower() in ["delete", "deleted"]:
            delete_result = delete_knowledge_article(article_title)
            actual_article_url = delete_result.get("article_url", KNOWLEDGE_BASE_URL)

            ticket_result = create_ticket(
                subject=f"Knowledge Article Deleted: {article_title}",
                description=(
                    f"The knowledge article '{article_title}' has been deleted.\n\n"
                    f"URL: {article_url}\n\n"
                    f"Ensure it has been properly archived or removed in Freshservice - {actual_article_url}"
                ),
                tags=["freshservice_kb"]
            )
            results.extend([delete_result, ticket_result])

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
