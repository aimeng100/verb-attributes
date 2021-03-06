"""
This file contains methods for loading the dictionary challenge.
"""
import spacy
from config import CHECKPOINT_PATH, DICTIONARY_PATH, GLOVE_PATH, GLOVE_TYPE
import os
from text.torchtext.data import Field, Dataset, Example, BucketIterator
import dill as pkl
from data.attribute_loader import _load_attributes
import random
from torch.autograd import Variable


class DictionaryChallengeDataset(Dataset):
    """ Dataset for the dictionary challenge, where the goal is to predict a word embedding
        from dictionary data"""

    def __init__(self, examples, is_train=True):
        """
        Initializes the list of fields, etc.
        :param examples: List of example tuples
        """
        text_field, label_field = load_vocab()

        fields = [('label', label_field), ('text', text_field)]
        # examples = [Example.fromlist(line, fields) for line in examples]

        self.embeds = Variable(label_field.vocab.vectors, volatile=not is_train)

        super(DictionaryChallengeDataset, self).__init__(examples, fields)

    @classmethod
    def splits(cls, num_val=10000):
        """
        :return: Gets training and validation splits for this.
        """
        with open(DICTIONARY_PATH, 'rb') as f:
            _words, _defns = pkl.load(f)
        examples = [(x, y) for x, y in zip(_words, _defns)]
        random.seed(123456)
        random.shuffle(examples)

        val_data = cls(examples[:num_val], is_train=False)
        train_data = cls(examples[num_val:], is_train=True)
        return train_data, val_data


def load_vocab(vocab_size=30000,
               vocab_path=os.path.join(CHECKPOINT_PATH, 'vocab_pretrained.pkl')):
    """
    Loads the vocab. If the vocab doesn't exist we'll reconstruct it
    :param vocab_size: # words in vocab
    :param vocab_path: Where to cache the vocab. Importantly, it's really
    expensive to build the dictionary from scratch, so we'll cache the dictionary.
    :return: Vocab file
    """

    defns_field = Field(
        tokenize='spacy',
        init_token='<bos>',
        eos_token='<eos>',
        lower=True,
        include_lengths=True,
        preprocessing=lambda x: [tok for tok in x if tok.isalpha()]
    )
    words_field = Field(sequential=False, include_lengths=False)
    if os.path.exists(vocab_path):
        print("Loading the cached vocab from {}".format(vocab_path))
        with open(vocab_path, 'rb') as f:
            defns_vocab, words_vocab = pkl.load(f)
        defns_field.vocab = defns_vocab
        words_field.vocab = words_vocab

        return defns_field, words_field
    print("Building the vocab. This might take a while...")


    def dict_gen(entries_dict=True):
        with open(DICTIONARY_PATH, 'rb') as f:
            _words, _defns = pkl.load(f)

        if entries_dict:
            for w, d in zip(_words, _defns):
                yield defns_field.preprocess(' '.join([w] + d))
            # Hack to make sure that all the verb templates are included.
            # We'll make them appear 100 times...
            verbs = _load_attributes()['template'].tolist()
            for v in verbs:
                for i in range(100 if entries_dict else 1):
                    yield defns_field.preprocess(v)
        else:
            for w in _words:
                yield words_field.preprocess(w)

    defns_field.build_vocab(dict_gen(entries_dict=True), max_size=vocab_size)
    words_field.build_vocab(dict_gen(entries_dict=False))

    defns_field.vocab.load_vectors(wv_dir=GLOVE_PATH, wv_type=GLOVE_TYPE)
    words_field.vocab.load_vectors(wv_dir=GLOVE_PATH, wv_type=GLOVE_TYPE)

    print("Caching the vocab to {}".format(vocab_path), flush=True)
    with open(vocab_path, 'wb') as f:
        pkl.dump((defns_field.vocab, words_field.vocab), f)
    return defns_field, words_field


if __name__ == '__main__':
    from lib.bucket_iterator import DictionaryChallengeIter
    train, val = DictionaryChallengeDataset.splits()
    train_iter = DictionaryChallengeIter(train, batch_size=32)
    blah = next(iter(train_iter))
