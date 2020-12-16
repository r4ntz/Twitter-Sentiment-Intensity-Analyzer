'''
Twitter Sentiment Intensity Analyzer

Rantz Marion
Last Edited : December 10th, 2020
---
Analyze content words of replies from famous political figures
in order to analyze the overall postitive and negative response.


TODO:

-do the analysis
-test read json file
-perhaps add larger data set for better analysis

'''
import tweepy
from datetime import datetime
from time import sleep
import os
import json
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import tokenize



class TwitterAPI:
    def __init__(self):
        self._access_token = ''
        self._access_token_secret = ''
        self._consumer_key = ''
        self._consumer_secret = ''

        self._api = self.check_access()


    def check_access(self):
        try:
            auth = tweepy.OAuthHandler(self._consumer_key, self._consumer_secret)
            auth.set_access_token(self._access_token, self._access_token_secret)
            return tweepy.API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)
        except:
            return None

    def check_calls_remaining(self):
        """
        We can make a total of 180 requests per 15 minutes. If the number of
        calls drops below 101 then sleep
        """
        limit = self._api.rate_limit_status()
        remaining = limit['resources']['search']['/search/tweets']['remaining']
        if (remaining < 101):
            print(str(datetime.utcnow()) + ' - Calls remaining: ' + str(remaining) + ' - sleeping for 15 minutes\n')
            sleep(60*15)
        else:
            print(str(datetime.utcnow()) + ' - Calls remaining: ' + str(remaining) + '\n')

    def fetch_replies(self, tweetObj, tweetID):
        tweeter = tweetObj._author
        print(str(datetime.utcnow()) + ' - Attempting to fetch replies from tweet '+ tweetID + ' (' + tweeter + ')...\n')
        try:
            #changed from recent to popular 7:47pm
            for reply_tweet in tweepy.Cursor(self._api.search, q='to:@'+ tweeter, lang='en', result_type='mixed', tweet_mode='extended', timeout=99999).items(100):
                if hasattr(reply_tweet, 'in_reply_to_status_id_str'):
                    if (reply_tweet.in_reply_to_status_id_str == tweetID):
                        #print(reply_tweet.full_text)
                        tweetObj.tokenize_reply(False, reply_tweet.full_text)

        except tweepy.error.TweepError as err:
            print(str(datetime.utcnow()) + " - Encountered error fetching reply.\n")
            print(err)
            return False
        except Exception as err:
            print(str(datetime.utcnow()) + " - Encountered error fetching reply.\n")
            print(err)
            return False

        return True

    def fetch_tweets(self, tweeters, tweeter_dict):
        """
        Each Tweeter will have a list of TweetInformation objects
        containing the original tweet and the replies associated with it.
        These objects are storied within tweeter_dict
        """
        print(str(datetime.utcnow()) + ' - Attempting to fetch tweets...\n')


        try:
            for author in tweeters:
                tweets = self._api.user_timeline(screen_name=author, count=5, lang='en', tweet_mode='extended', include_rts=False, exclude_replies=True)
                for tweet in tweets:
                    #check and sleep if calls are insufficient
                    self.check_calls_remaining()

                    #create TweetInformation obj and insert username + tweet
                    someTweet = TweetInformation()
                    someTweet.set_author(author)
                    someTweet.tokenize_reply(True, tweet.full_text)
                    if author in tweeter_dict:
                        tweeter_dict[author].append(someTweet)
                    else:
                        tweeter_dict[author] = [someTweet]

                    #Search for replies to the tweet above and append to list
                    #in TweetInformation

                    tweetID = tweet.id_str
                    if not self.fetch_replies(someTweet, tweetID):
                        return False
                    else:
                        continue

        #no need to handle RateLimitError because wait_on_rate_limit = True
        #and check_calls_remaining() is called every loop inside fetch_tweets

        except tweepy.error.TweepError as err:
            print(str(datetime.utcnow()) + " - Encountered error fetching author's tweet.\n")
            print(err)
            return False

        except Exception as e:
            print(str(datetime.utcnow()) + " - Encountered error fetching author's tweet.\n")
            print(e)
            return False

        return True


class TextAnalysis:
    def __init__(self):
        self._sentiment = SentimentIntensityAnalyzer()

    def analyze_tweets(self, tInfo):
        #Analayze sentiment intensity by utilizing information
        #provided by TweetInformation object
        pass


class TweetInformation:
    """Designed for individual tweets """
    def __init__(self):
        self._author = ''
        self._original_tweet = []
        self._replies = []

    def set_author(self, author):
        self._author = author

    def tokenize_reply(self, author_bool, tweet):
        tweet_tokenized = tokenize.sent_tokenize(tweet)
        if author_bool:
            self._original_tweet = tweet_tokenized
        else:
            self._replies.append(tweet_tokenized)



class PoliticalFigures:
    def __init__(self):
        #self._political_figures = ['BarackObama', 'realDonaldTrump', 'JoeBiden', 'AOC']
        self._political_figures = ['BarackObama', 'AOC']
        self._user_dict = dict()

    def search_tweets(self, api):
        if not api.fetch_tweets(self._political_figures, self._user_dict):
            print(str(datetime.utcnow()) + " - Attempting to read the JSON file.\n")
            if not self.read_data():
                print(str(datetime.utcnow()) + " - Failed to read the JSON file.\n")
                quit()

        self.print_data()
        self.save_data()

    def read_data(self):
        """
        In the case where the user does not possess the credentials or
        does not wish to access the Twitter API; or they encounter an
        error while fetching the Tweets and thus must resort to using this.
        """
        data = dict()

        try:
            with open('./data.json', 'r') as readFile:
                data = json.load(readFile)
        except:
                return False

        if (os.path.getsize('./data.json') <= 2):
            for politicalFigure in data['political figures']:
                someTweet = TweetInformation()
                name = politicalFigure['username']

                someTweet.set_author(name)

                for reply in politicalFigure['replies']:
                    someTweet._replies.append(reply)

                if name in self._user_dict:
                    self._user_dict[name].append(someTweet)
                else:
                    self._user_dict[name] = [someTweet]

        else:
            print('Encountered error: .json is empty!\n')
            return False

        return True


    def save_data(self):
        """
        Read data we saved to user_dict and save it to a json file
        to analyze later.

        data.json format:
        {
        "tweets": [{
            "username": "username",
            "tweet": "hello world",
            "replies": ["@otherperson hello to you too."]
            }]
        }
        """
        data = {}
        data['tweets'] = []

        userIndex = 0 #to properly place the replies

        for user in self._user_dict.keys():
            for tweet in self._user_dict[user]:
                parentTweet = ' '.join(tweet._original_tweet)
                data['tweets'].append({
                    'username': user,
                    'tweet': parentTweet,
                    'replies': []})
                for reply in tweet._replies:
                    replyText = ' '.join(reply)
                    data['tweets'][userIndex]['replies'].append(replyText)

                userIndex += 1

        with open('data.json', 'w') as newFile:
                newFile.seek(0) #in case it's not empty- just overwrite
                json.dump(data, newFile)

        print(str(datetime.utcnow()) + ' - File "data.json" created.\n')


    def print_data(self):
        print("\nTWEETS AND REPLIES")
        print("-------------------\n\n")

        for user in self._user_dict.keys():
            for tweet in self._user_dict[user]:
                parentTweet = ' '.join(tweet._original_tweet)
                print(tweet._author + ": " + parentTweet + "\n\nREPLIES\n")
                if tweet._replies:
                    for reply in tweet._replies:
                        replyText = ' '.join(reply)
                        print(replyText + '\n')
                else:
                    print('\nNone (limit likely reached)\n')
            print('\n')



def main():
    print('\nTwitter Sentiment Intensity Analyzer')

    print('Author: Rantz Marion')
    print('Last edited: December 2020')
    print('------------------------------------')
    print("\nNOTE: if you wish to disable use of the")
    print("Twitter API, please disable the functionality")
    print("within main().\n\n")

    TWITTER_API = True

    txtAnalysis = TextAnalysis()
    politicalFigures = PoliticalFigures()

    if (not TWITTER_API and os.path.isfile('./data.json') and os.access('./data.json', os.R_OK)):
        print(str(datetime.utcnow()) + ' - Reading JSON File...\n')
        politicalFigures.read_data()
    elif not TWITTER_API:
        print(str(datetime.utcnow()) + ' - Attempt to access JSON file failed.\n')
        quit()
    else:
        print(str(datetime.utcnow()) + ' - Attempting to access Twitter API...\n')
        twitter = TwitterAPI()
        politicalFigures.search_tweets(twitter)


if __name__ == '__main__':
    main()
