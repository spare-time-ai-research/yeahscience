# Yeah Science

A simple tool for creating a RSS with arXiv summaries on recent cs.AI papers.

## Motivation

The main purpose of the project is to save time for browsing recent arXiv
papers in cs.AI category and get only most interesting papers with a short summary. 
There are tons of them published every day and once you miss a day, you will never
catch up.

The algorithm is simple:
1. Get all papers from arXiv in cs.AI category published in the last 24 hours
2. Filter out papers that are not interesting (e.g. not related to AI, not related to
   my research interests, etc.)
3. Create a _simple_ summary for each paper
4. Create/update a RSS feed with the summaries

## Configuration

1. The project is configured via environment variables. The following variables are
required:
   - `OPENAI_API_KEY` - a key for OpenAI API
   - `FEED_URLS` - a comma-separated list of RSS feed URLs to fetch 
2. Prompts are defined within `prompts` directory, you might want to customize them. 
Each prompt is a file with a single prompt. The name of the file is used as a name of 
3. the prompt:
   - `prompts/filter.txt` - a prompt to filter interesting papers
   - `prompts/summary.txt` - a prompt to create a summary

## Running

There are 2 ways to run the project: via Docker or locally.

### Locally

Run the main script:

```bash
mkdir rss
poetry install --no-root
python main.py
```

The script will generate a `rss/rss.xml` file that can be used as a RSS feed. 
You can serve it with the following command:

 ```bash
 python -m http.server --directory rss
 ```  

### Docker

1. First you need to build images and run the containers:

```bash
docker build --target app -t yeahscience-app .
docker build --target web-server -t yeahscience-web-server .
```

2. Rename `.env.example` to `.env` and fill in the required environment variables.

3. Then you can run the containers:

```bash
docker-compose up -d
````

4. Access the RSS feed at `http://localhost/rss.xml`.

5. The logs can be checked using the following command:

```bash
docker-compose logs -f
```
