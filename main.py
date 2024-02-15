from json import loads, dumps
from os import environ, path
from re import sub
from typing import Generator
from logging import getLogger, config
from feedgen.feed import FeedGenerator

import feedparser
import openai
from feedparser import FeedParserDict
from inscriptis import get_text
from openai.types.chat import ChatCompletion
from openai.types.chat.completion_create_params import ResponseFormat
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from yeahscience.model import (
    Entry,
    FilterResponseEntry,
    AiFilterResponse,
    AiSummaryResponse,
)
from yeahscience.log import LOGGING_CONFIG

MODEL = "gpt-4-1106-preview"
BATCH_SIZE = int(environ.get("BATCH_SIZE", 10))
FEED_URLS = environ.get(
    "FEED_URLS",
    "https://export.arxiv.org/rss/cs.AI,https://www.reddit.com/r/LocalLLaMA/.rss",
).split(",")
OPENAI_API_KEY = environ.get("OPENAI_API_KEY")
SEEN_CACHE_FILE = "rss/seen.txt"
SYSTEM_PROMPT = "Always return output in JSON format."

if not FEED_URLS or not OPENAI_API_KEY:
    raise ValueError("FEED_URLS and OPENAI_API_KEY environment variables must be set.")

config.dictConfig(LOGGING_CONFIG)
logger = getLogger(__name__)


def load_seen_cache(file_path: str) -> set[str]:
    """Load seen cache from a file."""
    logger.info("load_seen_cache, file_path=%s", file_path)

    if not path.exists(file_path):
        return set()

    with open(file_path, "r") as file:
        return set(line.strip() for line in file)


def save_seen_cache(file_path: str, links: set):
    """Save seen links to a file."""
    logger.info("save_seen_cache, file_path=%s, links=%s", file_path, len(links))

    with open(file_path, "w") as file:
        for link in links:
            file.write(f"{link}\n")


def get_rss_entries(urls: list[str], seen_cache: set[str]) -> list[Entry]:
    """Get RSS feed entries from given URLs"""
    logger.info("get_rss_entries, urls=%s, seen_cache=%s", urls, len(seen_cache))
    result: list[Entry] = []

    for url in urls:
        logger.info("get_rss_entries, url=%s", url)

        feed: FeedParserDict = feedparser.parse(url)
        not_seen_entries: list = list(
            filter(lambda x: x.link not in seen_cache, feed.entries)
        )

        logger.debug("get_rss_entries, new entries=%s", len(not_seen_entries))

        result += [
            Entry(
                title=e.title,
                description=sub(r" {5,}", " ", get_text(e.description)),
                link=e.link,
            )
            for e in not_seen_entries
        ]

    return result


def create_batches(
    entries: list[Entry], batch_size: int
) -> Generator[list[Entry], None, None]:
    """Create batches out of a list of entries"""
    logger.info("create_batches, entries=%s, batch_size=%s", len(entries), batch_size)

    for i in range(0, len(entries), batch_size):
        yield entries[i : i + batch_size]


def filter_entries(batch: list[Entry], template: Template) -> list[Entry]:
    """Filter entries using ChatGPT"""
    logger.info("filter_entries, batch=%s, template=%s", len(batch), template)

    prompt: str = template.render(
        entries=dumps(
            [entry.model_dump(exclude={"topic"}) for entry in batch], indent=4
        )
    )
    logger.debug("filter_entries, prompt=%s", prompt)

    completion: ChatCompletion = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
        response_format=ResponseFormat(type="json_object"),
    )

    # Assuming the response is a list of titles separated by newlines
    filter_response: AiFilterResponse = AiFilterResponse(
        **loads(completion.choices[0].message.content)
    )
    logger.debug("filter_entries, filter_response=%s", filter_response)

    response_entries: list[FilterResponseEntry] = filter_response.entries
    topics_by_link: dict[str, str] = {
        entry.link: entry.topic for entry in response_entries
    }
    filtered_batch: list[Entry] = list(
        filter(lambda entry: entry.link in topics_by_link, batch)
    )

    for entry in filtered_batch:
        entry.topic = topics_by_link[entry.link]

    logger.debug(
        "filter_entries, filtered entries=(%s) %s",
        len(filtered_batch),
        filtered_batch,
    )

    return filtered_batch


def get_summary(entry: Entry, template: Template) -> str:
    """Get summary for an entry"""
    logger.info("get_summary, entry=%s, template=%s", entry, template)
    prompt: str = template.render(description=entry.description)

    completion: ChatCompletion = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
        response_format=ResponseFormat(type="json_object"),
    )

    summary_response: AiSummaryResponse = AiSummaryResponse(
        **loads(completion.choices[0].message.content)
    )
    logger.debug("get_summary, summary_response=%s", summary_response)

    return summary_response.summary


def generate_rss_feed(entries: list[Entry]):
    """Generate RSS feed out of entries list"""
    logger.info("generate_rss_feed, entries=%s", len(entries))

    fg: FeedGenerator = FeedGenerator()
    fg.id("https://yeahscience.sparetime.tech")
    fg.title("Yeah Science")
    fg.author({"name": "Yeah Science", "email": "anton@sparetime.tech"})
    fg.link(href="https://yeahscience.sparetime.tech")
    fg.description("Yeah Science: arXiv and Reddit/LocalLLaMA overview")

    for entry in entries:
        logger.info("generate_rss_feed, link=%s, description=%s", entry.link, entry.description)
        fe = fg.add_entry()
        fe.id(entry.link)
        fe.title(entry.title)
        fe.description(entry.description)
        fe.link(href=entry.link)
        fe.category(term=entry.topic)

    fg.rss_file("rss/rss.xml")


def generate_summaries(entries: list[Entry], template: Template):
    """Generate summaries for entries"""
    logger.info("generate_summaries, entries=%s, template=%s", len(entries), template)
    ctr: int = 0

    for e in entries:
        logger.info("generate_summaries, entry=%s/%s", ctr, len(entries))
        e.description = get_summary(e, template)

        ctr += 1


if __name__ == "__main__":
    seen_cache: set[str] = load_seen_cache(SEEN_CACHE_FILE)
    rss_entries: list[Entry] = get_rss_entries(FEED_URLS, seen_cache)
    logger.debug("RSS entries=%s", len(rss_entries))

    entries: list[Entry] = []

    template_env = Environment(
        loader=FileSystemLoader("prompts"), autoescape=select_autoescape()
    )
    filter_template: Template = template_env.get_template("filter.txt")
    summary_template: Template = template_env.get_template("summary.txt")

    if len(rss_entries) > 0:
        batches: list[list[Entry]] = [
            batch for batch in create_batches(rss_entries, batch_size=BATCH_SIZE)
        ]
        ctr: int = 0

        for batch in batches:
            logger.info("batch=%s/%s", ctr, len(batches))
            ctr += 1
            entries.extend(filter_entries(batch, filter_template))

        logger.debug("final filtered result, entries=%s", len(entries))

    # generate RSS feed out of entries list
    if len(entries) > 0:
        generate_summaries(entries, summary_template)
        generate_rss_feed(entries)
    else:
        logger.warning("No new entries to generate RSS feed from")

    # save cache
    for item in rss_entries:
        seen_cache.add(item.link)

    save_seen_cache(SEEN_CACHE_FILE, seen_cache)
