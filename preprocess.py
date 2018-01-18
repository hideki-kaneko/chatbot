import MeCab
import numpy as np
from tqdm import tqdm
import pickle
from collections import Counter

mecab = MeCab.Tagger("-Owakati -d /usr/lib/mecab/dic/mecab-ipadic-neologd/")

UNK_SYMBOL = 0
SOS_SYMBOL = 1
EOS_SYMBOL = 2

flatten = lambda lst: [item for sublist in lst for item in sublist]

MAX_VOCAB = 60
MAX_WORD_LEN = 'U20'
MAX_VOCAB_TOTAL = 100000

mecab_tweets = []
skip_flag = False
print("Tokenizing...")
with open("tweets.txt") as f:
    entire_tweets = f.readlines()
    for i, tweet in enumerate(tqdm(entire_tweets)):
        if skip_flag:
            skip_flag = False
            continue
        parsed = mecab.parse(tweet[3:]).split()
        parsed.append("<EOS>")
        length = len(parsed)
        if length == MAX_VOCAB:
            mecab_tweets.append(parsed)
        elif length < MAX_VOCAB:
            pad = ["<UNK>" for i in range(MAX_VOCAB-length)]
            parsed.extend(pad)
            mecab_tweets.append(parsed)
        else:
            skip_flag = True
print("Converting to numpy array...")
mecab_tweets = np.asarray(mecab_tweets)
num_tweets = mecab_tweets.shape[0]

entire_tweets = None

print("Creating dicts...")
word_all = flatten(mecab_tweets)
corpus = set(word_all)
if len(corpus) > MAX_VOCAB_TOTAL:
    counter = Counter(word_all)
    tmp = [i for i,j in tqdm(counter.most_common(MAX_VOCAB_TOTAL))]
    corpus = tmp


dict_id_word = {i+3:j for i,j in enumerate(tqdm(corpus)) if j!='' and j!='<EOS>' and j!='<UNK>'}
dict_id_word[SOS_SYMBOL] = "<SOS>"
dict_id_word[EOS_SYMBOL] = "<EOS>"
dict_id_word[UNK_SYMBOL] = "<UNK>"
dict_word_id = {i:j+3 for j,i in enumerate(tqdm(corpus)) if i!='' and i!='<EOS>' and i!='<UNK>'}
dict_word_id["<SOS>"] = SOS_SYMBOL
dict_word_id["<EOS>"] = EOS_SYMBOL
dict_word_id["<UNK>"] = UNK_SYMBOL
corpus = None

print("Encoding...")
def encodeTweets(word):
    if word not in dict_word_id.keys():
        return UNK_SYMBOL
    else:
        return dict_word_id[word]

entire_tweets_vec = np.vectorize(encodeTweets)(mecab_tweets)
mecab_tweets = None


a_idx = [bool(i%2) for i in range(num_tweets)]
b_idx = np.logical_not(a_idx)

train_enc_inputs = entire_tweets_vec[a_idx].T
# train_enc_inputs = np.vstack((np.tile(SOS_SYMBOL, (1,a.shape[1])), a))

train_out_labels = entire_tweets_vec[b_idx]
train_dec_inputs = np.vstack((np.tile(SOS_SYMBOL, (1,train_out_labels.shape[0])), train_out_labels.T))

print("saving...")
np.savez_compressed("train.npz",
                    train_enc_inputs=train_enc_inputs,
                    train_out_labels=train_out_labels,
                    train_dec_inputs=train_dec_inputs,
                   )
with open("dict_id_word.pkl", 'wb') as f:
    pickle.dump(dict_id_word, f)

with open("dict_word_id.pkl", 'wb') as f:
    pickle.dump(dict_word_id, f)
