import argparse
import os
import pickle
import re

import tweepy


class DialogueListener(tweepy.StreamListener):
    """会話を取得するための Listener。
    """
    REPLY_PATTERN = r'(@[a-zA-Z0-9_]+\s)*(?P<text>.*)'
    URL_PATTERN = r'https?://[\w/:%#\$&\?\.=\+\-]+'

    def __init__(self, twitter_api: tweepy.API, hold_json: bool, api=None):
        """コンストラクタ。

        :param twitter_api: tweepy.API のインスタンス。
        :param hold_json: 処理されていない JSON 形式で会話を保持するかどうか。
        :param api: 不明。
        """
        super(DialogueListener, self).__init__(api)

        self.twitter_api = twitter_api
        self._dialogues = []
        self.hold_json = hold_json
        self._dialogues_json = []

    @property
    def dialogues(self):
        return self._dialogues

    @property
    def dialogues_json(self):
        return self._dialogues_json

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

            # hold_json フラグが立っていればツイートの JSON データをそのまま
            # 保存しておく
            if self.hold_json:
                self._dialogues_json.append((origin_tweet, tweet))

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
                del self._dialogues_json[-1]
                print('Origin: %s\nReply: %s' % (origin_text, reply_text))
                self._dialogues.append((origin_text, reply_text))


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
    parser.add_argument('--output-json', type=str, default=None,
                        help='DEBUG')

    args = parser.parse_args()

    # 指定した出力ファイルのパスにすでにファイルが存在しているかどうかのチェック
    # TODO: 例外を投げるのではなく、既存のファイルにデータを追加するようにしたい
    if os.path.exists(args.output):
        raise Exception('%s はすでに存在しています。' % args.output)
    if args.output_json and os.path.exists(args.output_json):
        raise Exception('%s はすでに存在しています。' % args.output_json)

    # TwitterAPI のラッパー
    api = get_twitter_api_wrapper(args.auth_file)

    # リスナーとストリームの用意
    listener = DialogueListener(api, hold_json=bool(args.output_json))
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

        if args.output_json:
            with open(args.output_json, 'wb') as output_file:
                pickle.dump(listener.dialogues_json, output_file)
                print('[DEBUG] JSON 形式のデータを "%s" に保存しました。'
                      % args.output_json)


if __name__ == '__main__':
    main()
