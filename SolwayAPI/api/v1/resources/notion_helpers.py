from bs4 import BeautifulSoup

from markdown_it import MarkdownIt


def naive_batch(indexable, batch_size):
    """ splits a variable that can be indexed into smaller batches of length batch_size"""
    return [indexable[i:i + batch_size] for i in range(0, len(indexable), batch_size)]


def markdown_to_html(markdown_content):
    """ Turns Markdown Content into an Object"""
    md = MarkdownIt()
    return md.render(markdown_content)


def html_to_notion_blocks(html_content):
    """ Converts HTML tags into corresponding Notion tags"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    blocks = []
    print(soup)

    for element in soup.children:
        if element.name:
            if element.name == 'h1':
                blocks.append(create_heading_block(element.text, 1))
            elif element.name == 'h2':
                blocks.append(create_heading_block(element.text, 2))
            elif element.name == 'h3':
                blocks.append(create_heading_block(element.text, 3))
            elif element.name == 'p':
                blocks.append(create_paragraph_block(element))
            elif element.name == 'ul':
                blocks.extend(create_list_block(element, 'bulleted_list_item'))
            elif element.name == 'ol':
                blocks.extend(create_list_block(element, 'numbered_list_item'))
            # Add more element handlers as needed
            else:
                print(f"Unhandled element: {element.name}")
        else:
            print(f"Non-element content: {element}")

    return blocks


def create_heading_block(text, level):
    """ Creates a Heading Block"""
    print(f"Creating heading level {level} with text: {text}")
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": [{
                "type": "text",
                "text": {"content": text}
            }]
        }
    }


def create_raw_block(text):
    """ Creates a Raw Text Block"""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": {"content": text}
            }]
        }
    }


def create_paragraph_block(element):
    """ Creates a Paragraph Block"""
    rich_text = []
    for child in element.children:
        if child.name == 'strong':
            rich_text.append({
                "type": "text",
                "text": {"content": child.text},
                "annotations": {"bold": True}
            })
        elif child.name == 'em':
            rich_text.append({
                "type": "text",
                "text": {"content": child.text},
                "annotations": {"italic": True}
            })
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": child.string if child.string else ""}
            })

    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": rich_text
        }
    }


def create_list_block(element, list_type):
    """ Creates a list block """
    blocks = []
    for item in element.find_all('li'):
        item_text = item.text
        if len(item_text) > 2000:
            text_chunks = naive_batch(item_text, 2000)
            for chunk in text_chunks:
                blocks.append({
                    "object": "block",
                    "type": list_type,
                    list_type: {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": chunk}
                        }]
                    }
                })
        else:
            blocks.append({
                "object": "block",
                "type": list_type,
                list_type: {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": item_text}
                    }]
                }
            })
    return blocks

