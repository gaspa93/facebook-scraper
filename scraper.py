from facebook import FacebookScraper
import argparse
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facebook posts, reviews and user scraper.')
    parser.add_argument('--N', type=int, default=10, help='Number of posts/reviews to scrape')
    parser.add_argument('--u', type=str, default='museoegizio', help='Target account')
    parser.add_argument('--review', dest='review', action='store_true', help='Scrape reviews instead of posts')
    # parser.add_argument('--t', type=str, help='Target hashtag to scrape posts')
    parser.set_defaults(review=False)

    args = parser.parse_args()

    # ig account credentials (needed for posts, not for users data)
    fb_credentials = json.load(open('credentials.json', 'r'))
    with FacebookScraper(fb_credentials) as scraper:
        if scraper.login():

            # account metadata
            account = scraper.get_account(args.u)
            print(account)

            # review data
            if args.review:
                # sort by date reviews of target public account
                scraper.sort_by_date(args.u)
                reviews = scraper.get_reviews(0)
                print(reviews)

            # post data
            else:
                posts = scraper.get_content(args.u, 0)
                print(posts)
