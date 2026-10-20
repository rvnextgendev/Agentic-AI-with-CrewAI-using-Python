"""Research tools compatible with the project's LangChain/CrewAI versions."""

import json
import os

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool


class SerperDevTool(BaseTool):
    name: str = "Search the internet"
    description: str = "Search the web for current information. Input is a search query."

    def _run(self, search_query: str) -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Search unavailable: SERPER_API_KEY is missing."
        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key},
                json={"q": search_query, "num": 10},
                timeout=30,
            )
            response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False)
        except (requests.RequestException, ValueError):
            return "Search failed. Try another query or retry later."


class ScrapeWebsiteTool(BaseTool):
    name: str = "Read website content"
    description: str = "Read the text of a web page. Input is a full HTTP or HTTPS URL."

    def _run(self, website_url: str) -> str:
        if not website_url.lower().startswith(("http://", "https://")):
            return "Provide a full HTTP or HTTPS URL."
        try:
            response = requests.get(website_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()
            return soup.get_text(separator=" ", strip=True)[:20000]
        except requests.RequestException:
            return "Unable to read this page. Try another URL."
