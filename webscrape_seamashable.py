import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin
import time # Import time for potential delays

# --- Configuration ---
# Using SEA URLs based on your inspection screenshot
BASE_URL = "https://sea.mashable.com/"
CATEGORY_URLS = {
    "Tech": "https://sea.mashable.com/tech/",
    "Life": "https://sea.mashable.com/life/",
    "Science": "https://sea.mashable.com/science/",
    "Entertainment": "https://sea.mashable.com/entertainment/",
    "Social Good": "https://sea.mashable.com/social-good/"
}

CUTOFF_DATE = datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def parse_datetime(date_str):
    """Attempts to parse various ISO date formats commonly found in datetime attributes."""
    if not date_str: return None
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError: print(f"Warning: Could not parse date string: {date_str}"); return None
    except Exception as e: print(f"Error parsing date string '{date_str}': {e}"); return None


def extract_article_links_from_listing(soup, base_url, processed_links_set):
    """
    Finds article previews on a listing page and extracts only their title and link.
    Uses selectors based on user's first screenshot (listing page).
    """
    links_found = []
    #Get article name from the grid
    article_containers = soup.find_all('div', class_='grid-item')
    print(f"Found {len(article_containers)} potential articles on listing page.")

    for container in article_containers:
        try:
            #Check link in the box title class name
            link_tag = container.find('a', class_='box_title', href=True) 
            if not link_tag:
                continue

            link = urljoin(base_url, link_tag['href'])

            if link in processed_links_set:
                 continue
            processed_links_set.add(link) # Add to set to avoid duplicates

            title = link_tag.get_text(strip=True)
            links_found.append({'title': title, 'link': link})

        except Exception as e:
            print(f"Error processing one listing item container: {e}")
            continue
    return links_found

# HTML output for those articles title and date
def generate_html(articles):
    """Generates a simple black and white HTML page from the list of articles."""
    print("Generating HTML output...")
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mashable SEA Headlines Aggregator</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff; color: #000000; max-width: 800px; margin: 20px auto; padding: 15px; line-height: 1.6; }
        h1 { text-align: center; border-bottom: 1px solid #000000; padding-bottom: 10px; margin-bottom: 25px; }
        ul { list-style-type: none; padding: 0; }
        li { margin-bottom: 18px; padding-bottom: 10px; border-bottom: 1px dotted #cccccc; }
        li:last-child { border-bottom: none; }
        a { text-decoration: none; color: #000000; font-weight: bold; font-size: 1.1em; }
        a:hover, a:focus { text-decoration: underline; }
        small { display: block; color: #555555; font-size: 0.85em; margin-top: 4px; }
    </style>
</head>
<body>
    <h1>Mashable SEA Headlines (Since 2022-01-01)</h1>
    <ul>
"""
    if not articles:
        html_content += "<li>No articles found matching the criteria after checking article pages.</li>"
    else:
        for article in articles:
            display_date = article['date'].strftime('%Y-%m-%d %H:%M %Z')
            escaped_title = article.get('title', 'No Title Found').replace('<','&lt;').replace('>','&gt;')
            html_content += f"        <li>\n"
            html_content += f"            <a href=\"{article['link']}\" target=\"_blank\">{escaped_title}</a>\n"
            html_content += f"            <small>Published: {display_date}</small>\n"
            html_content += f"        </li>\n"
    html_content += """
    </ul>
</body>
</html>
"""
    print("HTML generation complete.")
    return html_content


if __name__ == "__main__":
    articles_to_fetch = []
    processed_links_on_listings = set() 

    # === STEP 1: Scrape links/titles from all category listing pages ===
    print("--- STEP 1: Scraping article links from category pages ---")
    for category_name, url in CATEGORY_URLS.items():
        print(f"\nProcessing Category Listing: {category_name} ({url})")
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Get only titles and links from this listing page
            category_links = extract_article_links_from_listing(soup, BASE_URL, processed_links_on_listings)
            print(f"Found {len(category_links)} new article links in {category_name}.")
            articles_to_fetch.extend(category_links)
        except requests.exceptions.RequestException as e:
             print(f"Error fetching or parsing listing page {url}: {e}")
             continue 

    print(f"\n--- Step 1 Complete: Found {len(articles_to_fetch)} total unique article links to check ---")

    # === STEP 2: Visit each article page to get the date and filter ===
    final_articles = [] #Store articles valid with the date
    print("\n--- STEP 2: Fetching individual articles to get dates ---")
    total_to_fetch = len(articles_to_fetch)
    for index, article_stub in enumerate(articles_to_fetch):
        link = article_stub['link']
        title = article_stub['title']
        # Provide progress update
        print(f"Checking article {index + 1}/{total_to_fetch}: {link}")

        try:
            article_response = requests.get(link, headers=HEADERS, timeout=25) 
            article_response.raise_for_status()
            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            date_tag = None
            byline_div = article_soup.find('div', class_='byline font-default')
            if byline_div:
                date_tag = byline_div.find('time', datetime=True)

            if date_tag and date_tag.get('datetime'):
                date_str = date_tag['datetime']
                article_date = parse_datetime(date_str)


                #Store the article if the date is after the required date
                if article_date and article_date >= CUTOFF_DATE:
                    print(f"  -> ADDING: '{title}' (Date: {article_date.date()})")
                    final_articles.append({
                        'title': title,
                        'link': link,
                        'date': article_date
                    })
                else:
                     # Skip if the date is too old
                     print(f"  -> Skipping (Too old or date parse error): '{title}'")
                     pass
            else:
                # Skip also is the time cannot find inside the byline class 
                print(f"  -> Skipping (Date tag not found in byline): '{title}'")
                pass

            time.sleep(0.5) #Let server rest

        except requests.exceptions.Timeout:
            print(f"  -> ERROR: Request timed out for article {link}")
            continue
        except requests.exceptions.HTTPError as http_err:
             print(f"  -> ERROR: HTTP error for article {link}: {http_err}")
             continue # Skip article if it gives an error like 404 Not Found
        except requests.exceptions.RequestException as req_err:
            print(f"  -> ERROR: Failed to fetch article {link}: {req_err}")
            continue # Skip article if fetch fails
        except Exception as e:
             print(f"  -> ERROR: Unexpected error processing article page {link}: {e}")
             continue # Skip article on other errors

    print(f"\n--- Step 2 Complete ---")
    print(f"Found {len(final_articles)} articles matching the date criteria after checking individual pages.")

    # === STEP 3: Sort the final list ===
    print("Sorting articles by publication date descending...")
    final_articles.sort(key=lambda x: x['date'], reverse=True)

    # === STEP 4: Generate the final HTML ===
    html_output = generate_html(final_articles)

    # === STEP 5: Write the HTML to a file ===
    output_filename = "mashable_headlines.html"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"\nSuccessfully created HTML file: '{output_filename}'")
    except IOError as e: print(f"\nError: Could not write HTML file '{output_filename}': {e}")
    except Exception as e: print(f"\nAn unexpected error occurred while writing the file: {e}")