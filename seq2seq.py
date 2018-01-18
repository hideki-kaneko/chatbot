import tensorflow as tf
from tensorflow.python.layers import core
import numpy as np
import pickle
from tqdm import tqdm
import MeCab

tf.reset_default_graph()

isTRAIN = False


with open("dict_id_word.pkl", 'rb') as f:
    _dict = pickle.load(f)
    _l = len(_dict)
    print(_l)
hparams = tf.contrib.training.HParams(
    enc_vocab_size = _l+1,
    enc_len = 60,
    dec_vocab_size = _l+1,
    dec_len = 60,
    batch_size = 100,
    embed_size = 512,
    num_units = 16,
    learning_rate = 0.01,
    num_epochs = 100,
    beam_width = 20
)


UNK_SYMBOL = 0
SOS_SYMBOL = 1
EOS_SYMBOL = 2

def shuffle_data(enc_inputs, dec_inputs, out_labels):
    idx = np.arange(enc_inputs.shape[1])
    np.random.shuffle(idx)
    e = np.array(enc_inputs[:, idx])
    d = np.array(dec_inputs[:, idx])
    o = np.array(out_labels[idx, :])
    return e, d, o

# Encoder
enc_inputs = tf.placeholder(shape=(hparams.enc_len, hparams.batch_size), dtype=tf.int32)
enc_embed_matrix = tf.get_variable("enc_embed_matrix", [hparams.enc_vocab_size, hparams.embed_size])
enc_embed_input = tf.nn.embedding_lookup(enc_embed_matrix, enc_inputs)

enc_cell = tf.nn.rnn_cell.BasicLSTMCell(hparams.num_units)
enc_rnn_outputs, enc_rnn_state = tf.nn.dynamic_rnn(cell=enc_cell, inputs=enc_embed_input, time_major=True, dtype=tf.float32)

# Decoder
dec_inputs = tf.placeholder(shape=(hparams.dec_len, hparams.batch_size), dtype=tf.int32)
dec_embed_matrix = tf.get_variable("dec_embed_matrix", [hparams.dec_vocab_size, hparams.embed_size])
dec_embed_input = tf.nn.embedding_lookup(dec_embed_matrix, dec_inputs)
dec_len = tf.placeholder(shape=(hparams.batch_size), dtype=tf.int32) #ベクトルじゃないと怒られる

dec_cell = tf.nn.rnn_cell.BasicLSTMCell(hparams.num_units)
dec_helper = tf.contrib.seq2seq.TrainingHelper(inputs=dec_embed_input, sequence_length=dec_len, time_major=True)
dec_projection = core.Dense(units=hparams.dec_vocab_size, use_bias=False)
dec = tf.contrib.seq2seq.BasicDecoder(cell=dec_cell, helper=dec_helper, initial_state=enc_rnn_state, output_layer=dec_projection)
dec_rnn_output, dec_rnn_state,dec_seq_len = tf.contrib.seq2seq.dynamic_decode(decoder=dec)

# Loss
output_labels = tf.placeholder(shape=(hparams.batch_size, hparams.dec_len), dtype=tf.int32)
loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=output_labels, logits=dec_rnn_output.rnn_output)
global_step = tf.Variable(initial_value=0, name="global_step", trainable=False)
optimizer = tf.train.AdamOptimizer(hparams.learning_rate)
# optimizer = tf.train.GradientDescentOptimizer(hparams.learning_rate)
train_op = optimizer.minimize(loss, global_step=global_step)

# Inference
max_iterations = tf.round(tf.reduce_max(hparams.enc_len)*2)
inf_helper = tf.contrib.seq2seq.GreedyEmbeddingHelper(embedding=dec_embed_matrix, start_tokens=tf.fill([hparams.batch_size], SOS_SYMBOL), end_token=EOS_SYMBOL)
inf_dec = tf.contrib.seq2seq.BasicDecoder(cell=dec_cell, helper=inf_helper, initial_state=enc_rnn_state, output_layer=dec_projection)
inf_out, _, _ = tf.contrib.seq2seq.dynamic_decode(decoder=inf_dec, maximum_iterations=max_iterations)
reply_basic = inf_out.sample_id
inf_dec_init_state = tf.contrib.seq2seq.tile_batch(enc_rnn_state, multiplier=hparams.beam_width)
inf_beam = tf.contrib.seq2seq.BeamSearchDecoder(
    cell=dec_cell,
    embedding=dec_embed_matrix,
    start_tokens=tf.fill([hparams.batch_size], SOS_SYMBOL),
    end_token=EOS_SYMBOL,
    initial_state = inf_dec_init_state,
    beam_width=hparams.beam_width,
    output_layer=dec_projection,
    length_penalty_weight = 0.0
)
inf_beam_out, _, _ = tf.contrib.seq2seq.dynamic_decode(inf_beam, maximum_iterations=10)
reply = inf_beam_out.predicted_ids

# Run

if isTRAIN:
    train = np.load("train.npz")
    num_train_data = train["train_enc_inputs"].shape[1]
    train_enc_inputs = train["train_enc_inputs"]
    train_out_labels = train["train_out_labels"]
    train_dec_inputs = train["train_dec_inputs"]
    train = None
    print(train_dec_inputs.shape)


    print("Start training...")
    with tf.Session() as sess:
        saver = tf.train.Saver()
        sess.run(tf.global_variables_initializer())

        for epoch in range(hparams.num_epochs):
            for idx in tqdm(range(0, num_train_data, hparams.batch_size)):
                if idx + hparams.batch_size < num_train_data:
                    batch_enc_inputs = train_enc_inputs[:,idx:idx+hparams.batch_size]
                    batch_output_labels= train_out_labels[idx:idx+hparams.batch_size,:]
                    batch_dec_inputs= train_dec_inputs[:60,idx:idx+hparams.batch_size]
                else:
                    # print("Dismiss remaining", num_train_data - idx, " data.")
                    pass
                feed_dict = {
                    enc_inputs: batch_enc_inputs,
                    output_labels: batch_output_labels,
                    dec_inputs: batch_dec_inputs,
                    dec_len: np.ones((hparams.batch_size), dtype=int) * hparams.dec_len
                }
                _, loss_value = sess.run([train_op, loss], feed_dict=feed_dict)


            print("epoch:", epoch, " loss:", np.mean(loss_value))
            with open("log.txt", 'a') as log:
                log.write("epoch:" + str(epoch) + " loss:" + str(np.mean(loss_value)) + "\n")
            saver.save(sess, "./model/model.ckpt")
            print("Shuffling data...")
            train_enc_inputs, train_dec_inputs, train_out_labels = shuffle_data(train_enc_inputs, train_dec_inputs, train_out_labels)
            
else:
    with open("dict_id_word.pkl", 'rb') as f:
        dict_id_word = pickle.load(f)
    with open("dict_word_id.pkl", 'rb') as f:
            dict_word_id = pickle.load(f)
    mecab = MeCab.Tagger("-Owakati -d /usr/lib/mecab/dic/mecab-ipadic-neologd/")
    
    def encodeTweets(word):
        if word not in dict_word_id.keys():
            return UNK_SYMBOL
        else:
            return dict_word_id[word]
    text_encoder = np.vectorize(encodeTweets)

    def decodeTweets(id):
        if id not in dict_id_word.keys():
            return "<UNK>"
        else:
            return dict_id_word[id]
    text_decoder = np.vectorize(decodeTweets)

    with tf.Session() as sess:
        saver = tf.train.Saver()
        saver.restore(sess, "./model/model.ckpt")
        
        while True:
            say_final_vec = np.zeros((hparams.enc_len, hparams.batch_size))
            say = mecab.parse(input(">")).split()
            say.insert(0, "<SOS>")
            say.append("<EOS>")
            say_vec = np.tile(text_encoder(say)[:,np.newaxis], (1, hparams.batch_size))
            say_final_vec[:say_vec.shape[0]] = say_vec
            feed_dict = {
                enc_inputs: say_final_vec
            }
            # print(say_vec)
            replies = sess.run([reply_basic], feed_dict=feed_dict)
            print(text_decoder(replies[0][0]))
            # print(text_decoder(replies[0][0][:,0]))
            # print(replies[0][0][:,0])
#     feed_dict = {
#         enc_inputs: train_encoder_inputs,
#         output_labels: training_target_labels,
#         dec_inputs: training_decoder_inputs,
#         dec_len: np.ones((hparams.batch_size), dtype=int) * hparams.dec_len
#     }
#     replies = sess.run([reply], feed_dict=feed_dict)
#     print(replies)