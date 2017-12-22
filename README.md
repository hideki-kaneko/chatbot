# KaiRA-ChatBot
## DataMining-Twitter
ツイッターから会話データを取得するツールです。(試作中)

ツイッター(現在は userstream を使用しています)から会話データを取得し、(質問, 返事) のようなタプルのリストを pickle ファイルで保存します。

使い方は

$ python mining.py --help

で確認してください。

pickle 化された tweepy.OAuthHandler が必要ですが、以下の手順で作成できます。(apps.twitter.com から各種キーを取得してください。)

1. 対話形式で作成

引数に --set-keysを指定すると、対話形式でpickle化されたtweepy.OAuthHandlerを作成できます（カレントディレクトリにauth.pickleが保存されます）。

実行例: キーを作成してから実行

$ python mining.py auth.pickle out.pickle --set-keys

2. 自分で作成

$ python

\>\>\> import pickle

\>\>\> import tweepy

\>\>\> auth = tweepy.OAuthHandler(CONSUMER\_KEY, CONSUMER\_SECRET)

\>\>\> auth.set\_access\_token(ACCESS\_TOKEN, ACCESS\_TOKEN\_SECRET)

\>\>\> f = open('auth.pickle', 'wb')

\>\>\> pickle.dump(auth, f)

\>\>\> f.close()

(カレントディレクトリで OAuthHandler の pickle ファイル 'auth.pickle' を作成)
