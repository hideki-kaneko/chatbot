""" this is a program to collect chat data on twitter
"""
import argparse
import pickle
import re

import tweepy


class DialogueListener(tweepy.StreamListener):
    """会話を取得するための Listener。
    """
    REPLY_PATTERN = r'(@[a-zA-Z0-9_]+\s)*(?P<text>.*)'
    URL_PATTERN = r'https?://[\w/:%#\$&\?\.=\+\-]+'

    def __init__(self, twitter_api: tweepy.API, output_path: str, api=None):
        """コンストラクタ。

        :param twitter_api: tweepy.API のインスタンス。
        :param output_path: 出力パス。
        :param api: 不明。
        """
        super(DialogueListener, self).__init__(api)

        self.twitter_api = twitter_api
        self.output_file = open(output_path, 'a')

    def on_status(self, status):
        """Called when a new status arrives.
        """
        tweet = status._json
        if tweet['in_reply_to_status_id']:
            # リプライである場合、オリジナルツイートを取得する
            # TODO: オリジナルツイートを取得する際の例外処理
            origin_tweet = self.twitter_api.get_status(
                tweet['in_reply_to_status_id'])._json

            # 改行文字の置換
            reply_text = tweet['text'].replace('\n', '。')
            origin_text = origin_tweet['text'].replace('\n', '。')

            # screen_id の除去
            match = re.match(self.REPLY_PATTERN, origin_text)
            origin_text = match.group('text')
            match = re.match(self.REPLY_PATTERN, reply_text)
            reply_text = match.group('text')

            # URL の除去
            rex = re.compile(self.URL_PATTERN)
            origin_text = rex.sub('', origin_text)
            reply_text = rex.sub('', reply_text)

            # 空白のみからなる文でないなら出力に追加する
            if not (re.match(r'\s*$', origin_text) or
                    re.match(r'\s*$', reply_text)):
                self.output_file.write(
                    'A: %s\nB: %s\n' % (origin_text, reply_text))
                self.output_file.flush()


def load_object_from_pickle(path: str) -> object:
    """pickle ファイルからオブジェクトを読み取る。

    :param path: pickle ファイルのパス。
    :return: pickle ファイルに格納されているオブジェクト。
    """
    with open(path, 'rb') as pickle_file:
        obj = pickle.load(pickle_file)
    return obj

def create_auth_pickle():
    print("https://apps.twitter.com/ で取得したキーを入力してください")
    CONSUMER_KEY = str(input("CONSUMER KEY:"))
    CONSUMER_SECRET = str(input("CONSUMER SECRET:"))
    ACCESS_TOKEN = str(input("ACCESS TOKEN:"))
    ACCESS_TOKEN_SECRET = str(input("ACCESS TOKEN SECRET:"))
    try:
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        with open('auth.pickle', 'wb') as f:
            pickle.dump(auth, f)
        print("auth.pickle を保存しました")
    except :
        print("エラー")

def main():
    """main 関数。
    """
    # コマンドライン引数解析
    parser = argparse.ArgumentParser(
        description='ツイッターから会話データを収集するためのツール。')
    parser.add_argument('auth_file', type=str,
                        help='pickle で直列化された OAuthHandler のパス')
    parser.add_argument('output', type=str, help='出力ファイルのパス')
    parser.add_argument('--set-keys', action='store_true', help='対話形式で認証用ファイルを生成します')

    args = parser.parse_args()

    if args.set_keys:
        create_auth_pickle()

    # TwitterAPI のラッパー
    auth = load_object_from_pickle(args.auth_file)
    api = tweepy.API(auth)

    # リスナーとストリームの用意
    listener = DialogueListener(api, output_path=args.output)
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # 会話の収集
    stream.sample(languages=['ja'])


if __name__ == '__main__':
    main()
