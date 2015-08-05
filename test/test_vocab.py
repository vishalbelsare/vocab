
import unittest
import numpy as np

from vocab import vocab


class TestTokenize(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(['k', 'd', 'iphone', 'kw', 'yo'],
                    vocab.alpha_tokenize(' %8k_d iPhone   \t  \n kw231 yo!'))

        self.assertEqual([], vocab.alpha_tokenize("1 + 1 = 2"))

        self.assertEqual(
            ['registered', 'trademark', '\xc3\xa9t\xc3\xa9'],
            vocab.alpha_tokenize(
                u'Registered Trademark \xae \u03b4\u03bf\u03b3 \xe9t\xe9'))


class TestVocabulary(unittest.TestCase):
    def setUp(self):
        ngrams = [
            {'new': 0, 'york': 1, 'city': 2, 'brooklyn': 3, 'jersey': 4},
            {'new_york': 5, 'new_jersey': 6, 'is_new': 7},
            {'new_york_city': 8}
        ]
        ngrams_sw = [
            {'new': 0, 'york': 1, 'city': 2, 'brooklyn': 3, 'jersey': 4,
             'is': 9, 'in': 10},
            {'new_york': 5, 'new_jersey': 6, 'is_new': 7},
            {'new_york_city': 8}
        ]
        counts = [3, 2, 1, 1, 1, 2, 1, 1, 1, 2, 2]
        self.vocab = vocab.Vocabulary(ngrams)
        self.vocab_sw = vocab.Vocabulary(ngrams_sw, counts=counts)

    def test_word2id(self):
        self.assertEqual(self.vocab.word2id('city'), 2)
        self.assertEqual(self.vocab.word2id('is_new'), 7)
        self.assertEqual(self.vocab.word2id('new_york_city'), 8)
        self.assertRaises(KeyError, self.vocab.word2id, 'not found')

    def test_id2word(self):
        self.assertEqual(self.vocab.id2word(0), 'new')
        self.assertEqual(self.vocab.id2word(5), 'new_york')
        self.assertRaises(IndexError, self.vocab.id2word, 9)

    def test_tokenize1(self):
        doc = 'New York City is in New York.'
        self.assertEqual(self.vocab.tokenize(doc),
            ['new_york_city', 'new_york'])

    def test_tokenize2(self):
        doc = 'Brooklyn sadfs is new'
        self.assertEqual(self.vocab.tokenize(doc),
            ['brooklyn', 'is_new'])

    def test_tokenize3(self):
        doc = u'Brooklyn is in new yOrk1!'
        self.assertEqual(self.vocab.tokenize(doc),
            ['brooklyn', 'new_york'])

    def test_tokenize4(self):
        self.assertEqual(self.vocab.tokenize('new'), ['new'])

    def test_tokenize5(self):
        self.assertEqual(self.vocab.tokenize(''), [])

    def test_tokenize6(self):
        doc = 'New York City is in New York.'
        self.assertEqual(self.vocab_sw.tokenize(doc),
            ['new_york_city', 'is', 'in', 'new_york'])

    def test_tokenize7(self):
        doc = 'New York City is in New York. Yay!'
        self.assertEqual(self.vocab_sw.tokenize(doc, remove_oov=False),
            ['new_york_city', 'is', 'in', 'new_york', 'OOV'])

    def test_tokenize8(self):
        doc = 'New York City is in New York. Yay!'
        ids = self.vocab_sw.tokenize_ids(doc, remove_oov=False)
        self.assertEqual(list(ids), [8, 9, 10, 5, 4294967295])

    def test_random_id(self):
        np.random.seed(123)
        self.assertEqual(self.vocab_sw.random_id(), 8)

    def test_random_ids(self):
        np.random.seed(123)
        ids = self.vocab_sw.random_ids(5)
        self.assertEqual(list(ids), [8,  2,  0,  0,  1])

    def test_save_load(self):
        """
        We should be able to save and then load the vocab
        """
        import tempfile

        (fid, fname) = tempfile.mkstemp()
        self.vocab.save(fname)
        vocab_loaded = vocab.Vocabulary.load(fname, build_table=False)

        self.assertEqual(len(self.vocab), len(vocab_loaded))
        for k in xrange(len(self.vocab)):
            self.assertEqual(self.vocab.id2word(k), vocab_loaded.id2word(k))
            token = self.vocab.id2word(k)
            self.assertEqual(
                self.vocab.word2id(token), vocab_loaded.word2id(token))


class TestVocabularyUpdate(unittest.TestCase):
    """
    Test the updating functionality of the vocabulary
    """
    def setUp(self):
        self.corpus = [
            'new york city is in new york',
            'brooklyn is in new york city',
            'he bought a new phone',
            'he bought a new computer'
        ]

        self.expected_unigrams = ['new', 'york', 'city', 'brooklyn',
                                  'bought', 'phone', 'computer']
        self.expected_bigrams = ['new_york', 'bought_a', 'york_city']
        self.expected_trigrams = ['new_york_city', 'bought_a_new']

    def test_update_unigrams(self):
        """
        We should be able to update corpus with unigram counts
        """
        v = vocab.Vocabulary()
        for doc in self.corpus:
            v.accumulate(doc)
        v.update()

        actual = sorted(
            [v.id2word(k) for k in xrange(len(self.expected_unigrams))])
        self.assertEqual(actual, sorted(self.expected_unigrams))

        self.assertRaises(IndexError, v.id2word,
                          len(self.expected_unigrams))

    def test_update_ngrams(self):
        """
        The Vocabulary should find n-grams
        """
        # learn up to tri-grams
        v = vocab.Vocabulary()
        for nkeep, min_count in [(1000, 1), (3, 1), (2, 2)]:
            for doc in self.corpus:
                v.accumulate(doc)
            v.update(nkeep, min_count)

        tokenid = 0
        for expected in [self.expected_unigrams,
                         self.expected_bigrams, self.expected_trigrams]:
            # check id2word
            actual = [v.id2word(k)
                      for k in xrange(tokenid, tokenid + len(expected))]
            self.assertEqual(sorted(actual), sorted(expected))

            # check word2id
            for k, token in enumerate(actual):
                self.assertEqual(v.word2id(token), k + tokenid)

            tokenid += len(expected)

    def test_empty(self):
        """
        We should handle empty or short docs gracefully
        """
        for k in xrange(3):
            v = vocab.Vocabulary()
            # for i in xrange(k):
            #     for doc in self.corpus:
            #         v.accumulate(doc)
            #     v.update()
            v.accumulate('')
            v.accumulate(' '.join(['computer'] * (k - 1)))
            v.update()
        # if we made it to here with out raising an error or seg faulting
        # the test passes
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()