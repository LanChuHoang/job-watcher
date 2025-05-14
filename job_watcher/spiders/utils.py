import re

import numpy as np
from markdownify import markdownify as md
from scrapy.selector import SelectorList

from job_watcher.model import JobType


def currency_parser(cur_str):
    # Remove any non-numerical characters
    # except for ',' '.' or '-' (e.g. EUR)
    cur_str = re.sub("[^-0-9.,]", "", cur_str)
    # Remove any 000s separators (either , or .)
    cur_str = re.sub("[.,]", "", cur_str[:-3]) + cur_str[-3:]

    if "." in list(cur_str[-3:]):
        num = float(cur_str)
    elif "," in list(cur_str[-3:]):
        num = float(cur_str.replace(",", "."))
    else:
        num = float(cur_str)

    return np.round(num, 2)


def get_full_text(
    component: SelectorList, seperator: str = "", default: str = ""
) -> str:
    """
    Get the full text from a SelectorList component.
    :param component: SelectorList component
    :param seperator: Seperator to join the text
    :return: Full text
    """
    if not component:
        return default

    texts = [text.strip() for text in component.css("::text").getall() if text.strip()]
    full_text = seperator.join(texts).strip()
    return full_text if full_text else default


def markdown_converter(html_component: SelectorList) -> str:
    """
    Convert HTML component to markdown.
    :param html_component: SelectorList component
    :return: Markdown text
    """
    if not html_component:
        return ""
    return md(html_component)


def get_enum_from_job_type(job_type_str: str) -> JobType | None:
    """
    Given a string, returns the corresponding JobType enum member if a match is found.
    """
    res = None
    for job_type in JobType:
        if job_type_str in job_type.value:
            res = job_type
    return res


def extract_emails_from_text(text: str) -> list[str] | None:
    if not text:
        return None
    email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    return email_regex.findall(text)
