
URL_ACCOUNT = "http://www.facebook.com/{}"
URL_REVIEWS = "http://www.facebook.com/{}/reviews"
URL_POSTS = "http://www.facebook.com/{}/posts"

class FacebookScraper:

    def __init__(self, driver, credentials):
        self.driver = driver
        self.login_ = credentials
        self.logger = self.get_logger()

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

        '''
        try:
            n_total_reviews = int(self.driver.find_element_by_css_selector('span._67l2').text.split(' ')[5].replace('.',''))
        except:
            self.logger.warn('{}: Not found total number of reviews: no review section or no review available'.format(username))
            return 1

        n_reviews_loaded = len(self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper'))
        '''

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

        self.db['user'].insert_one(fb_account)

        return 0

    def get_engagement(self, metadata, min_timestamp):
        profile = metadata['fb_profile']
        self.driver.get(URL_POSTS.format(username))

        # check date of bottom post
        bottom_date = self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper')[
            -1].find_element_by_css_selector('abbr._5ptz').get_attribute('title')
        curr_last_date = datetime.strptime(bottom_date, '%d/%m/%y, %H:%M')

        n_scrolls = 0
        while curr_last_date >= min_timestamp and n_scrolls < MAX_SCROLLS:

            # scroll to bottom of page to trigger ajax call
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')

            # wait for other reviews to load
            time.sleep(3)

            # check date of bottom post
            bottom_date = self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper')[
                -1].find_element_by_css_selector('abbr._5ptz').get_attribute('title')
            curr_last_date = datetime.strptime(bottom_date, '%d/%m/%y, %H:%M')

            n_scrolls += 1

        resp = BeautifulSoup(self.driver.page_source, 'html.parser')

        # get posts list
        post_list = resp.find_all('div', class_='_5pcr userContentWrapper')
        count = 0
        for idx, post in enumerate(post_list):
            count += self.__get_post_engagement(post, metadata, min_timestamp)

        return count

    def get_content(self, metadata):
        fb_profile = metadata['fb_profile']
        id_2 = metadata['id_2']

        self.driver.get("http://www.facebook.com/" + fb_profile + "/posts")
        self.__expand_content()

        bottom = self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper')[-1]
        bottom_date = bottom.find_element_by_css_selector('abbr._5ptz').get_attribute('title')
        curr_last_date = datetime.strptime(bottom_date, '%d/%m/%y, %H:%M')

        # check if list of post ids is present in DB
        p_ids = self.__page_ids_p()
        got_old_posts = self.db['post'].find_one({'id_2': id_2, 'id_post': {'$in': p_ids}})
        while got_old_posts is None and curr_last_date >= MIN_DATE_REVIEW:
            # scroll to bottom of page
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')

            # wait for other reviews to load
            time.sleep(3)

            # check date of bottom post
            bottom = self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper')[-1]
            bottom_date = bottom.find_element_by_css_selector('abbr._5ptz').get_attribute('title')
            curr_last_date = datetime.strptime(bottom_date, '%d/%m/%y, %H:%M')

            # check ids of post in the page
            p_ids = self.__page_ids_p()
            got_old_posts = self.db['post'].find_one({'id_2': id_2, 'id_post': {'$in': p_ids}})

        # expand text of posts
        self.__expand_content()

        resp = BeautifulSoup(self.driver.page_source, 'html.parser')

        # get posts list
        post_list = resp.find_all('div', class_='_5pcr userContentWrapper')
        new_posts = 0
        for idx, post in enumerate(post_list):
            new_posts = new_posts + self.__get_post_data(post, metadata)

        self.logger.info('POST - {}: {}'.format(metadata['fb_profile'], new_posts))

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



    def __get_post_engagement(self, p, metadata, min_timestamp):
        id_mibact = int(metadata['id_mibact'])
        id_2 = int(metadata['id_2'])
        max_timestamp = min_timestamp + relativedelta(months=1)

        pinned = p.find('i', class_='_5m7w img sp_bjbQDwUU8b8 sx_81fd46')
        id = p.find('div', class_='_5pcp _5lel _2jyu _232_')['id']
        date = datetime.strptime(p.find('abbr', class_='_5ptz')['title'], '%d/%m/%y, %H:%M')

        # pinned elements and posts in the comments are skipped
        # also posts out of the time window are not monitored
        if pinned is None and ':' not in id and date >= min_timestamp and date < max_timestamp:
            id_post = id.split(';')[1]

            reactions = self.__get_reactions(p)
            shares = self.__get_shares(p)
            comments = self.__get_comments(p)

            t = datetime.now()
            curr_date = t.strftime('%Y-%m-%d %H:%M:%S')

            # db insert
            id_post = bson.int64.Int64(id_post)
            self.db['comment'].insert_one({'id_mibact': id_mibact, 'id_2': id_2, 'id_post': id_post,
                                           'date': curr_date, 'count': comments, 'timestamp': t})
            self.db['share'].insert_one({'id_mibact': id_mibact, 'id_2': id_2, 'id_post': id_post,
                                        'date': curr_date, 'count': shares, 'timestamp': t})
            self.db['reaction'].insert_one({'id_mibact': id_mibact, 'id_2': id_2, 'id_post': id_post,
                                           'date': curr_date, 'reactions': reactions, 'timestamp': t})

            return 1
        return 0

    def __get_post_data(self, p, metadata):

        pinned = p.find('i', class_='_5m7w img sp_bjbQDwUU8b8 sx_81fd46')

        # id format id="feed_subtitle_57579540619;580620952460311;;9" -> .split(';')[1]
        id = p.find('div', class_='_5pcp _5lel _2jyu _232_')['id'].encode('utf-8')
        date = datetime.strptime(p.find('abbr', class_='_5ptz')['title'], '%d/%m/%y, %H:%M')

        # pinned elements are skipped
        # also posts out of the timespan are not saved, nor the ones already scraped
        if pinned is None and date >= MIN_DATE_REVIEW and ':' not in id:

            id_post = bson.int64.Int64(id.split(';')[1])
            is_old_post = self.db['post'].find_one({'id_post': id_post})
            post = {}
            if is_old_post is None:
                # date and timestamp
                # timestamp = p.find('abbr', class_='_5ptz')['data-utime']
                timestamp = date
                date = str(date)  # db consistency
                post['id_post'] = id_post
                post['date'] = date
                post['timestamp'] = timestamp

                # image url and description
                try:
                    img = p.find('img', class_='scaledImageFitWidth img')
                    img_url = img['src'].encode('utf-8')
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

                id_mibact = int(metadata['id_mibact'])
                id_2 = int(metadata['id_2'])
                fb_profile = metadata['fb_profile']
                post['id_mibact'] = id_mibact
                post['id_2'] = id_2
                post['fb_profile'] = fb_profile

                try:
                    self.db['post'].insert_one(post)
                except Exception as e:
                    self.logger.warn('MongoDB Error: ' + type(e).__name__)
                    return 0

                return 1

        return 0

    # TODO: not working, update
    def __get_post_from_tag(self, p, tag):

        id = re.search("\"id\":(\d+)", p['data-bt']).group(1)
        # id format id="feed_subtitle_580620952460311:9:0"
        # id = p.find('div', class_='_5pcp _5lel _2jyu _232_')['id'].split('_')[2].split(':')[0].encode('utf-8')
        id_post = bson.int64.Int64(id)

        old_post = self.db['tag'].find_one({'id_post': id_post})
        post = {}
        if old_post is None:

            # date and timestamp
            # timestamp = p.find('abbr', class_='_5ptz')['data-utime']
            date = datetime.strptime(p.find('abbr', class_='_5ptz')['title'], '%d/%m/%y, %H:%M')
            timestamp = date
            date = str(date)  # db consistency
            post['id_post'] = id_post
            post['date'] = date
            post['timestamp'] = timestamp

            # image url and description
            try:
                img = p.find('img', class_='scaledImageFitWidth img')
                img_url = img['src'].encode('utf-8')
                img_desc = filterString(img['alt'])

                post['img_url'] = img_url
                post['img_desc'] = img_desc
            except Exception as e:
                # print 'Image not found:', e
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

            # user info
            try:
                username = filterString(p.find('a', class_='profileLink').text)
            except:
                username = filterString(p.find('a', class_=None).text)

            user_url = p.find('a', class_=None)['href']

            post['username'] = username
            post['user_url'] = user_url
            post['hashtag'] = [tag]

            try:
                self.db['tag'].insert_one(post)
            except Exception as e:
                    self.logger.warn('MongoDB Error: ' + type(e).__name__)
                    return 0
            return 1

        else:
            if tag not in old_post['hashtag']:
                res = self.db['tag'].update_one({'id_post': old_post['id_post']}, {'$push': {'hashtag': tag}}, upsert=False)
                self.logger.warn('Post already present: updated hashtag list')

                return 1

    # load review complete text
    def __expand_content(self):
        try:
            expand_bts = self.driver.find_elements_by_xpath('//span[@class=\'see_more_link_inner\']')
            for bt in expand_bts:
                bt.click()

            time.sleep(5)
        except:
            pass

    # return list of review ids in the page
    def __page_ids_r(self):
        ids = []
        for post in self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper'):
            ids.append(int(
                post.find_element_by_css_selector('div._5pcp._5lel._2jyu._232_').get_attribute('id').split(':')[0].split('_')[2]))

        return ids

    # return list of post ids in the page
    def __page_ids_p(self):
        ids = []
        for post in self.driver.find_elements_by_css_selector('div._5pcr.userContentWrapper'):
            try:
                ids.append(int(post.find_element_by_css_selector('div._5pcp._5lel._2jyu._232_').get_attribute('id').split(';')[1]))
            except:
                pass
        return ids

    # check if bottom of the page is reached
    def __is_bottom_page(self):
        try:
            bottom_div = self.driver.find_element_by_xpath('//div[@class=\'phm _64f\']')
            return True

        except NoSuchElementException:
            return False

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
