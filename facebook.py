from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import re

URL_ACCOUNT = "http://www.facebook.com/{}"
URL_REVIEWS = "http://www.facebook.com/{}/reviews"
URL_POSTS = "http://www.facebook.com/{}/posts"

rating_regex = re.compile('_51mq\simg(\ssp_(.){11}\ssx_(.){6})?')

class FacebookScraper:

    def __init__(self, credentials):
        self.login_ = credentials
        self.driver = self.__get_driver()
        self.logger = self.__get_logger()


    # login to your account
    def login(self):
        fb_login = self.login_

        try:
            self.driver.get("http://www.facebook.com/")
            elem = self.driver.find_element_by_id("email")
            elem.send_keys(fb_login['email'])
            elem = self.driver.find_element_by_id('pass')
            elem.send_keys(fb_login['password'])
            elem.send_keys(Keys.RETURN)
        except Exception as e:
            self.logger.error('Login Error: {}'.format(str(e)))
            return False

        return True


    # sort reviews by date
    def sort_by_date(self, username):
        self.driver.get(URL_REVIEWS.format(username))

        # click for most recent: change using XPath
        buttons = self.driver.find_elements_by_css_selector('a._3m1v._468f')
        for b in buttons:
            if b.get_attribute('aria-selected') == 'false':
                b.click()
                break

        time.sleep(5)

        return True


    def get_reviews(self, offset):

        # scroll to bottom of page
        self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')

        # wait ajax call to load reviews
        time.sleep(6)

        # expand text of reviews
        self.__expand_content()

        resp = BeautifulSoup(self.driver.page_source, 'html.parser')

        # get posts list and parse data
        review_list = resp.find_all('div', class_='_5pcr userContentWrapper')
        parsed_reviews = []
        for idx, review in enumerate(review_list):
            if idx >= offset:
                parsed_reviews.append(self.__get_review_data(review))

        return parsed_reviews


    def get_account(self, username):

        self.driver.get(URL_ACCOUNT.format(username))
        resp = BeautifulSoup(self.driver.page_source, 'html.parser')

        # official page data
        # some pages do not have ratings and reviews: default to 0 for these fields
        try:
            overall_rating = resp.find('span', class_='_2w0a').text.split(' ')[0].replace(',', '.')
            reviews = int(resp.find('span', class_='_2w0b').text.split(' ')[5].replace(',', ''))
        except:
            overall_rating = 0
            reviews = 0

        other = list(resp.find_all('div', class_='_4bl9'))
        likes = 0
        followers = 0
        for d in other:
            if 'Piace a' in d.text:
                likes = int(d.text.split(' ')[2].replace('.', ''))

            if 'Follower' in d.text:
                followers = int(d.text.split(' ')[1].replace('.', ''))

        timestamp = datetime.strptime(date, '%Y-%m-%d')
        fb_account = {'id_mibact': id_mibact,
                      'id_2': id_2,
                      'fb_profile': fb_profile,
                      'date': date,
                      'n_reviews': reviews,
                      'overall_rating': overall_rating,
                      'n_likes': likes,
                      'n_followers': followers,
                      'timestamp': timestamp}

        return fb_account


    def get_content(self, username, offset):

        if offset == 0:
            self.driver.get(URL_POSTS.format(username))

        # scroll to bottom of page
        self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')

        # wait for other reviews to load
        time.sleep(6)

        # expand text of posts
        self.__expand_content()

        resp = BeautifulSoup(self.driver.page_source, 'html.parser')

        # get posts list
        post_list = resp.find_all('div', class_='_5pcr userContentWrapper')
        parsed_posts = []
        for idx, post in enumerate(post_list):
            # save the ones just loaded with the scroll
            if idx >= offset:
                p = self.__get_post_data(post)
                if p != {}:
                    parsed_posts.append()

        return parsed_posts


    # TODO: hashtag search
    # def get_post_by_tag(self, tag)

    def __get_review_data(self, r):

        review = {}

        # review date
        date = r.find('abbr', class_='_5ptz')['title']
        timestamp = datetime.strptime(date, '%d/%m/%y, %H:%M')
        review['date'] = date
        review['timestamp'] = timestamp

        # id review
        id_review = int(r.find('div', class_='_5pcp _5lel _2jyu _232_')['id'].split(':')[0].split('_')[2])
        review['id_review'] = id_review

        # timestamp
        # timestamp_fb = r.find('abbr', class_='_5ptz')['data-utime']

        # content of review, if any
        text_div = r.find('div', class_='_5pbx userContent _3576')
        try:
            caption = filterString(text_div.text)
        except:
            caption = ''
        review['caption'] = caption

        # user that made the review
        userlink = r.find('a', class_='profileLink')
        try:
            user = userlink.text
            user_url = userlink['href'].split('?')[0]
            review['user_url'] = user_url
            review['username'] = user
        except:
            user = ''
            user_url = ''

        # rating
        try:
            rating = int(r.find('i', {'class': rating_regex}).text.split(' ')[0])
            review_type = 'recensione'
        except:
            rating = 0  # 0 means no rating in the review
            try:
                review_type = r.find('i', {'class': rating_regex}).next_sibling.strip()
            except:
                review_type = r.find('img', {'class': rating_regex}).next_sibling.strip()

        review['rating'] = rating
        review['review_type'] = review_type

        return review


    def __get_post_data(self, p):

        pinned = p.find('i', class_='_5m7w img sp_bjbQDwUU8b8 sx_81fd46')

        # id format id="feed_subtitle_57579540619;580620952460311;;9" -> .split(';')[1]
        id = p.find('div', class_='_5pcp _5lel _2jyu _232_')['id'].encode('utf-8')

        # pinned elements are skipped
        if pinned is None and ':' not in id:

            post = {}

            id_post = int(id.split(';')[1])
            date = datetime.strptime(p.find('abbr', class_='_5ptz')['title'], '%d/%m/%y, %H:%M')
            timestamp = date
            date = str(date)  # db consistency

            post['id_post'] = id_post
            post['date'] = date
            post['timestamp'] = timestamp

            # image url and description
            try:
                img = p.find('img', class_='scaledImageFitWidth img')
                img_url = img['src']  #.encode('utf-8')
                img_desc = filterString(img['alt'])

                post['img_url'] = img_url
                post['img_desc'] = img_desc
            except Exception as e:
                img_url = None
                img_desc = None

            reactions = self.__get_reactions(p)
            shares = self.__get_shares(p)
            comments = self.__get_comments(p)

            if len(reactions) > 0:
                post['reactions'] = reactions

            post['comments'] = comments
            post['shares'] = shares

            # content of post
            text_div = p.find('div', class_='_5pbx userContent _3576')
            if text_div is not None:
                caption = filterString(text_div.text)
                post['caption'] = caption
            else:
                caption = None

            # check presence of event
            try:
                event = p.find('span', class_='fcg')
                links = event.find_all('a', class_='profileLink')
                # print links
                if len(links) > 1:
                    event_link = links[1]['href']
                else:
                    event_link = None
            except:
                event_link = None

            post['event'] = event_link

            return post

        return {}

    # load review complete text
    def __expand_content(self):
        try:
            expand_bts = self.driver.find_elements_by_xpath('//span[@class=\'see_more_link_inner\']')
            for bt in expand_bts:
                bt.click()

            time.sleep(5)
        except:
            pass


    def __get_shares(self, p):
        try:
            shares = int(p.find('a', class_='_3rwx _42ft').text.split(': ')[1])
        except:
            shares = 0
            self.logger.warn('Share element not found.')

        return shares


    def __get_comments(self, p):
        try:
            comments = int(p.find('a', class_='_3hg- _42ft').text.split(': ')[1])
        except:
            comments = 0
            self.logger.warn('Comment element not found.')

        return comments


    def __get_reactions(self, p):
        reactions_elem = p.find_all('a', class_='_1n9l')

        reactions = []
        try:
            for r in reactions_elem:
                if 'Mi piace' in r['aria-label']:
                    value, key1, key2 = r['aria-label'].split(' ')
                    key = key1 + ' ' + key2
                else:
                    value, key = r['aria-label'].split(' ')

                reactions.append(key + ': ' + value)
        except:
            pass

        if len(reactions) == 0:
            self.logger.warn('Reactions element not found.')

        return reactions


    def __get_logger(self):
        # create logger
        logger = logging.getLogger('facebook-scraper')
        logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        fh = logging.FileHandler('fb-scraper.log')
        fh.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # add formatter to ch
        fh.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(fh)

        return logger


    def __get_driver(self, debug=False):
        options = Options()
        if not debug:
            options.add_argument("--headless")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-notifications")
        options.add_argument("--lang=en")
        options.add_argument("--no-sandbox")
        input_driver = webdriver.Chrome(chrome_options=options)

        return input_driver
