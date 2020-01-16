from facebook import FacebookScraper
import argparse
import json


def get_reviews(scraper, username, n):
    # sort by date reviews of target public account
    scraper.sort_by_date(username)

    reviews = []
    n_reviews = 0
    while n_reviews < n:
        curr_reviews = scraper.get_reviews(n_reviews)
        reviews = reviews + curr_reviews
        n_reviews = len(reviews)

    return reviews


def get_posts(scraper, username, n):
    posts = []
    n_posts = 0
    while n_posts < n:
        curr_posts = scraper.get_content(username, n_posts)
        posts = posts + curr_posts
        n_posts = len(posts)

    return posts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facebook posts, reviews and user scraper.')
    parser.add_argument('--N', type=int, default=10, help='Number of posts/reviews to scrape')
    parser.add_argument('--u', type=str, default='museoegizio', help='Target account')
    parser.add_argument('--review', dest='review', action='store_true', help='Scrape reviews')
    parser.add_argument('--account', dest='account', action='store_true', help='Scrape account metadata')
    # parser.add_argument('--t', type=str, help='Target hashtag to scrape posts')
    parser.set_defaults(review=False, account=False)

    args = parser.parse_args()

    # ig account credentials (needed for posts, not for users data)
    fb_credentials = json.load(open('credentials.json', 'r'))
    with FacebookScraper(fb_credentials) as scraper:
        if scraper.login():

            # account metadata
            if args.account:
                account = scraper.get_account(args.u)
                print(account)

            # review data
            elif args.review:
                rlist = get_reviews(scraper, args.u, args.N)
                print(rlist)

            # post data
            else:
                plist = get_posts(scraper, args.u, args.N)
                print(plist)
