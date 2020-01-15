from facebook import FacebookScraper
import argparse
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facebook posts, reviews and user scraper.')
    parser.add_argument('--N', type=int, default=10, help='Number of posts/reviews to scrape')
    parser.add_argument('--u', type=str, default='mattia.gasparini.5', help='Target account')
    parser.add_argument('--review', dest='review', action='store_true', help='Scrape reviews instead of posts')
    # parser.add_argument('--t', type=str, help='Target hashtag to scrape posts')
    parser.set_defeaults(review=False)

    args = parser.parse_args()

    # ig account credentials (needed for posts, not for users data)
    fb_credentials = json.load(open('credentials.json', 'r'))
    scraper = FacebookScraper(fb_credentials)

    if args.review:
        if scraper.login():
            reviews = scraper.get_reviews()
            print(reviews)
