""" this is a program to collect chat data on twitter
"""
import argparse
import logging
import pickle
import re
import time
from urllib3.exceptions import ProtocolError

import tweepy


class DialogueListener(tweepy.StreamListener):
    """会話を取得するための Listener。
    """
    REPLY_PATTERN = r'(@[a-zA-Z0-9_]+\s)*(?P<text>.*)'
    URL_PATTERN = r'https?://[\w/:%#\$&\?\.=\+\-]+'
    # 一回の出力で書き込む会話の数
    BUF_MAX = 30

    def __init__(self, twitter_api: tweepy.API, output_path: str, api=None):
        """コンストラクタ。

        :param twitter_api: tweepy.API のインスタンス。
        :param output_path: 出力パス。
        :param api: 不明。
        """
        super(DialogueListener, self).__init__(api)

        self.twitter_api = twitter_api
        self.output_file = open(output_path, 'a')
        self.tweet_counter = 0
        self.buf = ''

    def on_status(self, status):
        """Called when a new status arrives.
        """
        tweet = status._json
        if tweet['in_reply_to_status_id']:
            # リプライである場合、オリジナルツイートを取得する
            try:
                origin_tweet = self.twitter_api.get_status(
                    tweet['in_reply_to_status_id'])._json
            except Exception as ex:
                if ex.api_code == 179:
                    # 鍵アカウントへのリプライの場合
                    pass
                else:
                    logging.warning('[on_status] Exception raised. msg: %s'
                                    % ex.reason)
                # プログラムの中止を避けるため
                return

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
                self.buf += 'A: %s\nB: %s\n' % (origin_text, reply_text)
                self.tweet_counter += 1
                if self.tweet_counter >= self.BUF_MAX:
                    self.output_file.write(self.buf)
                    self.tweet_counter = 0
                    self.buf = ''
                    self.output_file.flush()

    def on_error(self, status_code):
        logging.error('[on_error] Error occurred. '
                      'Status code: %s' % status_code)
        # プログラムの中止を避けるため
        return True


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
    parser.add_argument('--log', type=str, default='log',
                        help='ログの出力先\nデフォルトは ./log に出力する')

    args = parser.parse_args()

    # logging の設定
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        filename=args.log, level=logging.WARNING)

    if args.set_keys:
        create_auth_pickle()

    # TwitterAPI のラッパー
    auth = load_object_from_pickle(args.auth_file)
    api = tweepy.API(auth)

    # リスナーとストリームの用意
    listener = DialogueListener(api, output_path=args.output)
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # 会話の収集
    while True:
        try:
            stream.sample(languages=['ja'])
        except ProtocolError as ex:
            logging.warning('[main] ProtocolError raised. msg: %s' % str(ex))
            # DialogueListener.on_status 内のオリジナルツイートを取得する処理が
            # タイムアウトした場合に発生することを確認した
        except Exception as ex:
            logging.warning('[main] Exception raised. msg: %s' % str(ex))
            logging.warning('[main] time.sleep(120)')
            time.sleep(120)


if __name__ == '__main__':
    main()
