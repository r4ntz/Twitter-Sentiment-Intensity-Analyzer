'''
Twitter Sentiment Intensity Analyzer

Rantz Marion
Last Edited : December 16th, 2020
---
Analyze content words of replies from famous political figures
in order to analyze the overall postitive and negative response.


DOCUMENTATION

TwitterAPI - Used to access the Twitter API, check how
how many calls the user has remaining, and fetch tweets/replies

TextAnalysis - Here the Tweets are analyzed using NLTK's sentiment
intensity analyzer. We generate a score for each reply and take the average
of all the replies for that one tweet.

TweetInformation - Holds the username of the Tweet author, the original
tweet text, and the replies to that tweet.

PoliticalFigures - Here the Twitter handles are held and a dictionary
containing TweetInformation objects. We also read and save data to a JSON
file here. The JSON file can be used as a different means to do analysis
or as a backup if it exists.


'''
import tweepy
from datetime import datetime
from time import sleep
import os
import json
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import tokenize
from nltk import corpus
from prettytable import PrettyTable



class TwitterAPI:
    def __init__(self):
        self._access_token = ""
        self._access_token_secret = ""
        self._consumer_key = ""
        self._consumer_secret = ""

        try:
            self._auth = tweepy.OAuthHandler(self._consumer_key, self._consumer_secret)
            self._auth.set_access_token(self._access_token, self._access_token_secret)
            #Did not use wait_on_rate_limit since I found it less efficient than manually checking.
            self._api = tweepy.API(self._auth)
        except tweepy.error.TweepError as err:
            print(str(datetime.now().time()) + " - Encountered error while authenticating.\n")
            print(err)
            quit()
        except Exception as err:
            print(str(datetime.now().time()) + " - Encountered error while authenticating.\n")
            print(err)
            quit()


    def check_calls_remaining(self, timeline_bool):
        """
        We can make a total of 180 requests per 15 minutes. If the number of
        calls drops below 27 then sleep
        """
        limit = self._api.rate_limit_status()

        if timeline_bool:
            remaining = limit['resources']['statuses']['/statuses/user_timeline']['remaining']
            if (remaining < 5):
                print(str(datetime.now().time()) + ' - statuses/user_timeline calls remaining: ' + str(remaining) + ' - sleeping for 15 minutes\n')
                sleep(60*15)
            else:
                print(str(datetime.now().time()) + ' - statuses/user_timeline calls remaining: ' + str(remaining) + '\n')
        else:
            remaining = limit['resources']['search']['/search/tweets']['remaining']
            if (remaining < 1):
                print(str(datetime.now().time()) + ' - search/tweets calls remaining: ' + str(remaining) + ' - sleeping for 15 minutes\n')
                sleep(60*15)
            else:
                print(str(datetime.now().time()) + ' - search/tweets calls remaining: ' + str(remaining) + '\n')

    def fetch_replies(self, tweetObj, tweetID):
        tweeter = tweetObj._author
        print(str(datetime.now().time()) + ' - Attempting to fetch replies from tweet '+ tweetID + ' (' + tweeter + ')...\n')
        try:
            #Retrieving a hundred items because a lot of Tweets end up being filtered
            for reply_tweet in self._api.search(q='to:@'+ tweeter, lang='en', result_type='recent', count=200, tweet_mode='extended', timeout=99999):
                if hasattr(reply_tweet, 'in_reply_to_status_id_str'):
                    if (reply_tweet.in_reply_to_status_id_str == tweetID):
                        tweetObj.add_tweet(False, reply_tweet.full_text)
                        print(str(datetime.now().time()) + ' - Reply found!\n')

        except tweepy.error.TweepError as err:
            print(str(datetime.now().time()) + " - Encountered error fetching reply.\n")
            print(err)
            return False
        except Exception as err:
            print(str(datetime.now().time()) + " - Encountered error fetching reply.\n")
            print(err)
            return False

        return True

    def fetch_tweets(self, tweeters, tweeter_dict):
        """
        Each Tweeter will have a list of TweetInformation objects
        containing the original tweet and the replies associated with it.
        These objects are storied within tweeter_dict
        """
        print(str(datetime.now().time()) + ' - Attempting to fetch tweets...\n')


        try:
            for author in tweeters:
                #check and sleep if calls are insufficient
                self.check_calls_remaining(True)

                tweets = self._api.user_timeline(screen_name=author, count=5, lang='en', tweet_mode='extended', include_rts=False, exclude_replies=True)

                for tweet in tweets:
                    print(str(datetime.now().time()) + ' - Tweet found!\n')

                    #create TweetInformation obj and insert username + tweet
                    someTweet = TweetInformation()
                    someTweet.set_author(author)
                    someTweet.add_tweet(True, tweet.full_text)

                    if author in tweeter_dict:
                        tweeter_dict[author].append(someTweet)
                    else:
                        tweeter_dict[author] = [someTweet]

                    #check and sleep if calls are insufficient
                    self.check_calls_remaining(False)

                    #Search for replies to the tweet above and append to list
                    #in TweetInformation

                    tweetID = tweet.id_str
                    if not self.fetch_replies(someTweet, tweetID):
                        return False
                    else:
                        continue

        except tweepy.error.TweepError as err:
            print(str(datetime.now().time()) + " - Encountered error fetching author's tweet.\n")
            print(err)
            return False

        except Exception as err:
            print(str(datetime.now().time()) + " - Encountered error fetching author's tweet.\n")
            print(err)
            return False

        return True


class TextAnalysis:
    def __init__(self):
        self._sentiment = SentimentIntensityAnalyzer()
        self._avg_sentiment_dict = dict()

    def calculate_avg_sentiment(self, sd):
        for tweet in sd.keys():
                positive = 0
                negative = 0
                neutral = 0

                for replyScore in sd[tweet]:
                    positive += (replyScore['pos'] * 100)
                    negative += (replyScore['neg'] * 100)
                    neutral += (replyScore['neu'] * 100)

                #sd[tweet] contains all the filtered replies
                avgPositive = positive/len(sd[tweet])
                avgNegative = negative/len(sd[tweet])
                avgNeutral = neutral/len(sd[tweet])

                self._avg_sentiment_dict[tweet] = [avgPositive, avgNeutral, avgNegative]

    def analyze_tweets(self, tweets):
        #Analayze sentiment intensity by utilizing information
        #provided by TweetInformation object
        sentimentDict = dict()

        for twitterUser in tweets.keys():
            for tweet in tweets[twitterUser]:
                for reply in tweet._replies:
                    #This will create and add the polarity score of a reply
                    #for each tweet
                    textUsername = '@' + twitterUser + ' ' + tweet._original_tweet
                    if textUsername not in sentimentDict:
                        sentimentDict[textUsername] = [self._sentiment.polarity_scores(reply)]
                    else:
                        sentimentDict[textUsername].append(self._sentiment.polarity_scores(reply))

        self.calculate_avg_sentiment(sentimentDict)

    def generate_analysis(self):
        tbl = PrettyTable()
        tbl.field_names = ["Tweet", "Avg. Positive Score", "Avg. Neutral Score", "Avg. Negative Score"]
        for tweet in self._avg_sentiment_dict.keys():
            avgPos = str(self._avg_sentiment_dict[tweet][0])
            avgNeu = str(self._avg_sentiment_dict[tweet][1])
            avgNeg = str(self._avg_sentiment_dict[tweet][2])

            tbl.add_row([tweet, avgPos, avgNeu, avgPos])

        try:
            newHTML = open('data_table.html', 'w')
            newHTML.seek(0) #in case it's not empty- just overwrite
            newHTML.write("<title>Twitter Sentiment Intensity Analysis</title>")
            newHTML.write('<head><link rel="stylesheet" href="table_style.css"></head>')
            newHTML.write("<body>")
            newHTML.write("<p><b>Date Generated: " + str(datetime.today()) + "</b></p>")
            newHTML.write(tbl.get_html_string())
            newHTML.write("</body>")
            newHTML.close()
        except OSError:
            print(str(datetime.now().time()) + " - Encountered error generating HTML file.\n")
            quit()
        except Exception as err:
            print(str(datetime.now().time()) + err + "\n")
            quit()


class TweetInformation:
    """Designed for individual tweets """
    def __init__(self):
        self._author = ''
        self._original_tweet = []
        self._replies = []

    def set_author(self, author):
        self._author = author

    def add_tweet(self, author_bool, tweet):
        if author_bool:
            self._original_tweet = tweet
        else:
            self._replies.append(tweet)



class PoliticalFigures:
    def __init__(self):
        self._political_figures = ['BarackObama', 'realDonaldTrump', 'JoeBiden', 'AOC']
        self._user_dict = dict()

    def get_user_dict(self):
        return self._user_dict

    def search_tweets(self, api):
        if not api.fetch_tweets(self._political_figures, self._user_dict):
            print(str(datetime.now().time()) + " - Attempting to read the JSON file.\n")
            analysis = TextAnalysis()
            if not self.read_data(analysis):
                print(str(datetime.now().time()) + " - Failed to read the JSON file.\n")
                quit()


    def read_data(self, analysis):
        """
        In the case where the user does not possess the credentials or
        does not wish to access the Twitter API; or they encounter an
        error while fetching the Tweets and thus must resort to using this.
        """
        analysis = TextAnalysis()
        data = dict()

        try:
            with open('./data.json', 'r') as readFile:
                data = json.load(readFile)
        except:
                #In the case where api fails and attempt to read json fails
                #return false
                return False

        #grab data from json file
        fileSize = os.path.getsize('./data.json')
        if (fileSize > 2):
            for tweetDetails in data['tweets']:
                #create TweetInformation obj and add auth, tweet, and replies
                tweetObj = TweetInformation()
                name = tweetDetails['username']
                tweetObj.set_author(name)
                tweetObj.add_tweet(True, tweetDetails['tweet'])
                for reply in tweetDetails['replies']:
                    tweetObj.add_tweet(False, reply)

                #add the TweetInformation obj to our dictionary
                if name in self._user_dict:
                    self._user_dict[name].append(tweetObj)
                else:
                    self._user_dict[name] = [tweetObj]
        else:
            print(str(datetime.now().time()) + ' - Encountered error: .json is empty! (size = ' + str(fileSize) + ')\n')
            return False

        print(str(datetime.now().time()) + " - JSON file read succesfully.\n")

        #perform analysis
        analysis.analyze_tweets(self._user_dict)

        #generate table
        analysis.generate_analysis()

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
            }] .. etc
        }
        """
        data = {}
        data['tweets'] = []

        userIndex = 0 #to properly place the replies


        for user in self._user_dict.keys():
            for tweet in self._user_dict[user]:
                data['tweets'].append({
                    'username': user,
                    'tweet': tweet._original_tweet,
                    'replies': []})

                for reply in tweet._replies:
                    #add reply to json data
                    data['tweets'][userIndex]['replies'].append(reply)

                userIndex += 1

        #we've already checked for errors in main()
        try:
            newJSON = open('data.json', 'w')
            newJSON.seek(0) #in case it's not empty- just overwrite
            json.dump(data, newJSON)
            newJSON.close()
        except IOError:
            print(str(datetime.now().time()) + " - Encountered error generating JSON file.\n")
            quit()
        except Error as err:
            print(str(datetime.now().time()) + err + "\n")
            quit()

        print(str(datetime.now().time()) + ' - File "data.json" created.\n')



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
    analysis = TextAnalysis()

    if (not TWITTER_API and os.path.isfile('./data.json') and os.access('./data.json', os.R_OK)):
        print(str(datetime.now().time()) + ' - Reading JSON File...\n')
        if not politicalFigures.read_data(analysis):
            print(str(datetime.now().time()) + ' - Attempt to read JSON file failed.\n')
            quit()

    elif not TWITTER_API:
        print(str(datetime.now().time()) + ' - Attempt to read JSON file failed.\n')
        quit()
    else:
        #attempt to access the api and fetch tweets
        print(str(datetime.now().time()) + ' - Attempting to access Twitter API...\n')
        twitter = TwitterAPI()
        politicalFigures.search_tweets(twitter)

        #begin to analyze the tweets
        print(str(datetime.now().time()) + ' - Setting up text analysis...\n')
        allTweets = politicalFigures.get_user_dict()
        analysis.analyze_tweets(allTweets)

        # --
        analysis.generate_analysis()

        #save data to json file
        politicalFigures.save_data()


if __name__ == '__main__':
    main()
