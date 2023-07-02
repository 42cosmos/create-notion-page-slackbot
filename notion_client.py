import re
import os
import json
import requests
from typing import List
from dotenv import load_dotenv
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension


class Notion:
    def __init__(self, env_path=None):
        load_dotenv(env_path) if env_path is not None else load_dotenv()
        self._notion_api_key = os.getenv("NOTION_API_KEY", "")
        self._database_id = os.getenv("NOTION_DATABASE_ID", "")
        assert self._notion_api_key, "Notion API key not found"
        assert self._database_id, "Notion database ID not found"

        self._headers = {
            "Authorization": "Bearer " + self._notion_api_key,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def create_page(self, title: str, contents: str, tags: List[List]=None, image_url: str=None):
        page_url = 'https://api.notion.com/v1/pages'

        properties = {
            "parent": {"type": "database_id", "database_id": self._database_id},
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title}
                        }
                    ]
                },
            }
        }

        children_content = self.markdown_to_notion_api_json(contents)
        if children_content:
            properties["children"] = children_content

        if image_url:
            image_contents = {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": image_url}
                }
            }
            properties["children"].insert(0, image_contents)

        if tags:
            tag_contents = {"Tags": {
                "multi_select": [{
                    "name": name,
                    "color": colour} for name, colour in tags]
            }
            }
            properties["properties"].update(tag_contents)

        data = json.dumps(properties)

        res = requests.request("POST", page_url, headers=self._headers, data=data)
        assert res.status_code == 200, f"Error creating page: {res.status_code} {res.text}"
        return res.json()

    @staticmethod
    def markdown_to_notion_api_json(md_text):
        notion_blocks = []
        md = markdown.Markdown(extensions=[FencedCodeExtension()])
        # html = md.convert(md_text)

        removed_all_line = re.sub("\<\/*[a-zA-Z]+\>", "", md_text)
        for line in removed_all_line.split("\n"):
            if line.startswith("#"):
                count_hash = line.count("#")
                text = line.replace(f"{'#' * count_hash} ", "").strip()
                block = {
                    "object": "block",
                    "type": f"heading_{count_hash}",
                    f"heading_{count_hash}": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                }
                notion_blocks.append(block)
            elif line != "" and line[0].isdigit():
                is_numbered_list = True if re.findall(r"[\d]+\. ", line) else False
                if is_numbered_list:
                    text = re.sub(r"[\d]+\. ", "", line).strip()
                    block = {
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": text,
                                    }
                                }
                            ],
                            "color": "default"
                        }
                    }
                    notion_blocks.append(block)

            elif not line.startswith("#") and not line.startswith("1."):
                # Handle hyperlinks in text
                hyperlinks = extract_text_and_url(line, extract_hyperlink=True)
                if hyperlinks:
                    text, url = hyperlinks[0]
                    front_text, back_text = extract_text_and_url(line, extract_hyperlink=False)

                    hyperlink_block = {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": front_text.strip()
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": text.strip(),
                                        "link": {"url": url.strip()}
                                    }
                                }
                            ]
                        }
                    }
                    notion_blocks.append(hyperlink_block)

                    if back_text:
                        closed_text = {
                            "type": "text",
                            "text": {
                                "content": back_text.strip()
                            }
                        }
                        hyperlink_block["paragraph"]["rich_text"].append(closed_text)
                else:
                    paragraph_block = {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": line
                                    }
                                }
                            ]
                        }
                    }
                    notion_blocks.append(paragraph_block)

        return notion_blocks


def extract_text_and_url(markdown_string, extract_hyperlink=True):
    pattern = r'\[([^\[]+)\]\(([^\)]+)\)'
    if extract_hyperlink:
        matches = re.findall(pattern, markdown_string)
    else:
        matches = re.sub(pattern, "&&", markdown_string).split("&&")
    return matches
