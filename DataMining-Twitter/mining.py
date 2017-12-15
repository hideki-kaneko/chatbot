import argparse
import pickle
import re

import tweepy


class DialogueListener(tweepy.StreamListener):
    """会話を取得するための Listener。
    """
    REPLY_PATTERN = r'(@[a-zA-Z0-9_]+\s)*(?P<text>.*)'

    def __init__(self, twitter_api: tweepy.API, api=None):
        """コンストラクタ。

        :param twitter_api: tweepy.API のインスタンス。
        :param api: 不明。
        """
        super(DialogueListener, self).__init__(api)

        self.twitter_api = twitter_api
        self.dialogues = []

    def on_status(self, status):
        """Called when a new status arrives.
        """
        tweet = status._json
        if tweet['in_reply_to_status_id']:
            # リプライである場合、オリジナルツイートを取得し、
            # (オリジナルツイート, リプライ) の組を会話として保存する
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

            print('Origin: %s\nReply: %s' % (origin_text, reply_text))
            self.dialogues.append((origin_text, reply_text))


def get_twitter_api_wrapper(path: str) -> tweepy.API:
    """pickle で直列化された OAuthHandler を取り出し、tweepy.API の
    インスタンスを生成して返す。

    :param path: 直列化された OAuth ハンドラのパス。
    :return: TwitterAPI のラッパー。
    """
    with open(path, 'rb') as pickle_file:
        auth = pickle.load(pickle_file)
    api = tweepy.API(auth)
    return api


def main():
    """main 関数。
    """
    # コマンドライン引数解析
    parser = argparse.ArgumentParser(
        description='ツイッターから会話データを収集するためのツール。')
    parser.add_argument('auth_file', type=str,
                        help='pickle で直列化された OAuthHandler のパス')
    parser.add_argument('output', type=str, help='出力ファイルのパス')

    args = parser.parse_args()

    # TwitterAPI のラッパー
    api = get_twitter_api_wrapper(args.auth_file)

    # リスナーとストリームの用意
    listener = DialogueListener(api)
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # 会話の収集
    try:
        stream.userstream()
    except KeyboardInterrupt:
        print('\nKeyboardInterrupt.')
        with open(args.output, 'wb') as output_file:
            pickle.dump(listener.dialogues, output_file)
            print('%d 組の会話を取得し、"%s" に保存しました。'
                  % (len(listener.dialogues), args.output))


if __name__ == '__main__':
    main()
