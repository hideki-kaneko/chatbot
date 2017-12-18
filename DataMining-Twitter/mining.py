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
        # mining.py で生成したファイルであることを証明する
        self._dialogues.append(('ほげほげ', 'ふがふが'))
        return self._dialogues

    @property
    def dialogues_json(self):
        # mining.py で生成したファイルであることを証明する
        self._dialogues_json.append(('ほげほげ', 'ふがふが'))
        return self._dialogues_json

    @dialogues.setter
    def dialogues(self, dialogues):
        if dialogues[-1] == ('ほげほげ', 'ふがふが'):
            self._dialogues = dialogues[:-1]
        else:
            raise Exception('指定した出力ファイルはこのツールで出力した'
                            'ファイルではありません。')

    @dialogues_json.setter
    def dialogues_json(self, dialogues_json):
        if dialogues_json[-1] == ('ほげほげ', 'ふがふが'):
            self._dialogues_json = dialogues_json[:-1]
        else:
            raise Exception('指定した出力ファイル (JSON) はこのツールで'
                            '出力したファイルではありません。')

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


def load_object_from_pickle(path: str) -> object:
    """pickle ファイルからオブジェクトを読み取る。

    :param path: pickle ファイルのパス。
    :return: pickle ファイルに格納されているオブジェクト。
    """
    with open(path, 'rb') as pickle_file:
        obj = pickle.load(pickle_file)
    return obj


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

    # TwitterAPI のラッパー
    auth = load_object_from_pickle(args.auth_file)
    api = tweepy.API(auth)

    # リスナーとストリームの用意
    listener = DialogueListener(api, hold_json=bool(args.output_json))
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # 指定した出力ファイルのパスにすでにファイルが存在している場合には、
    # 既存のファイルにデータを追加する
    # ※  通常の出力と json の出力ファイルと整合性が取れているかどうかの確認は
    #    していない
    if os.path.exists(args.output):
        existing_dialogues = load_object_from_pickle(args.output)
        listener.dialogues = existing_dialogues
    if args.output_json and os.path.exists(args.output_json):
        existing_dialogues_json = load_object_from_pickle(args.output_json)
        listener.dialogues_json = existing_dialogues_json

    # 会話の収集
    try:
        stream.userstream()
    except KeyboardInterrupt:
        print('\nKeyboardInterrupt.')
        if existing_dialogues:
            data_got_num = len(listener.dialogues) - len(existing_dialogues)
        else:
            data_got_num = len(listener.dialogues) - 1

        with open(args.output, 'wb') as output_file:
            pickle.dump(listener.dialogues, output_file)
            print('%d 組の会話を取得し、"%s" に保存しました。'
                  % (data_got_num, args.output))

        if args.output_json:
            with open(args.output_json, 'wb') as output_file:
                pickle.dump(listener.dialogues_json, output_file)
                print('[DEBUG] JSON 形式のデータを "%s" に保存しました。'
                      % args.output_json)


if __name__ == '__main__':
    main()
