# KaiRA-ChatBot
## DataMining-Twitter
ツイッターから会話データを取得するツールです。(試作中)

ツイッター(現在は userstream を使用しています)から会話データを取得し、(質問, 返事) のようなタプルのリストを pickle ファイルで保存します。

使い方は

$ python mining.py --help

で確認してください。

pickle 化された tweepy.OAuthHandler が必要ですが、以下の手順で作成できます。(apps.twitter.com から各種キーを取得してください。)

$ python

\>\>\> import pickle

\>\>\> import tweepy

\>\>\> auth = tweepy.OAuthHandler(CONSUMER\_KEY, CONSUMER\_SECRET)

\>\>\> auth.set\_access\_token(ACCESS\_TOKEN, ACCESS\_TOKEN\_SECRET)

\>\>\> f = open('hoge.pickle', 'wb')

\>\>\> pickle.dump(auth, f)

\>\>\> f.close()

(カレントディレクトリで OAuthHandler の pickle ファイル 'hoge.pickle' を作成)
