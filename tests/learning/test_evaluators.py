import unittest
from nalaf.structures.data import Dataset, Document, Part, Entity
from nalaf.learning.evaluators import Evaluator, MentionLevelEvaluator
from nalaf.utils import MUT_CLASS_ID


class TestMentionLevelEvaluator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # create a sample dataset to test
        cls.dataset = Dataset()
        doc_1 = Document()

        text = '.... aaaa .... bbbb .... cccc .... dddd .... eeee .... ffff .... gggg .... hhhh .... jjjj'
        part_1 = Part(text)

        cls.dataset.documents['doc_1'] = doc_1
        doc_1.parts['part_1'] = part_1

        exact_1 = Entity(MUT_CLASS_ID, 5, 'aaaa')
        exact_1.subclass = 1
        exact_2 = Entity(MUT_CLASS_ID, 55, 'ffff')
        exact_2.subclass = 2
        exact_3 = Entity(MUT_CLASS_ID, 75, 'hhhh')
        exact_3.subclass = 2

        overlap_1_1 = Entity(MUT_CLASS_ID, 25, 'cccc')
        overlap_1_1.subclass = 1
        overlap_1_2 = Entity(MUT_CLASS_ID, 26, 'cc')
        overlap_1_2.subclass = 1

        overlap_2_1 = Entity(MUT_CLASS_ID, 32, '.. ddd')
        overlap_2_1.subclass = 2
        overlap_2_2 = Entity(MUT_CLASS_ID, 36, 'ddd ...')
        overlap_2_2.subclass = 2

        overlap_3_1 = Entity(MUT_CLASS_ID, 65, 'gggg')
        overlap_3_1.subclass = 1
        overlap_3_2 = Entity(MUT_CLASS_ID, 62, '.. gggg ..')
        overlap_3_2.subclass = 2

        missing_1 = Entity('e2', 45, 'eeee')
        missing_1.subclass = 1
        missing_2 = Entity('e2', 84, 'jjjj')
        missing_2.subclass = 1

        spurios = Entity('e2', 15, 'bbbb')
        spurios.subclass = 1

        part_1.annotations = [exact_1, exact_2, exact_3, overlap_1_1, overlap_2_1, overlap_3_1, missing_1, missing_2]
        part_1.predicted_annotations = [exact_1, exact_2, exact_3, overlap_1_2, overlap_2_2, overlap_3_2, spurios]

    def test_implements_evaluator_interface(self):
        self.assertIsInstance(MentionLevelEvaluator(), Evaluator)

    def test_exact_strictness(self):
        evaluator = MentionLevelEvaluator()
        evaluation = (evaluator.evaluate(self.dataset))(MentionLevelEvaluator.TOTAL_LABEL)

        self.assertEqual(evaluation.tp, 3)  # the 3 exact matches
        self.assertEqual(evaluation.fp, 4)  # the 3 overlapping + 1 spurious
        self.assertEqual(evaluation.fn, 5)  # the 3 overlapping + 2 missing

        ret = evaluation.compute('exact')

        self.assertEqual(ret.precision, 3 / 7)
        self.assertEqual(ret.recall, 3 / 8)
        self.assertEqual(ret.f_measure, 2 * (3 / 7 * 3 / 8) / (3 / 7 + 3 / 8))

    def test_overlapping_strictness(self):
        evaluator = MentionLevelEvaluator()
        evaluation = (evaluator.evaluate(self.dataset))(MentionLevelEvaluator.TOTAL_LABEL)

        self.assertEqual(evaluation.tp, 3)  # the 3 exact matches
        self.assertEqual(evaluation.fp - evaluation.fp_ov, 1)  # the 1 spurious
        self.assertEqual(evaluation.fn - evaluation.fn_ov, 2)  # the 2 missing
        self.assertEqual(evaluation.fp_ov, 3)  # the 3 overlapping
        self.assertEqual(evaluation.fn_ov, 3)  # the 3 overlapping

        ret = evaluation.compute('overlapping')

        self.assertEqual(ret.precision, 9 / 10)
        self.assertEqual(ret.recall, 9 / 11)
        self.assertAlmostEqual(ret.f_measure, 2 * (9 / 10 * 9 / 11) / (9 / 10 + 9 / 11), places=5)

    def test_half_overlapping_strictness(self):
        evaluator = MentionLevelEvaluator()
        evaluation = (evaluator.evaluate(self.dataset))(MentionLevelEvaluator.TOTAL_LABEL)

        self.assertEqual(evaluation.tp, 3)  # the 3 exact matches
        self.assertEqual(evaluation.fp - evaluation.fp_ov, 1)  # the 1 spurious
        self.assertEqual(evaluation.fn - evaluation.fn_ov, 2)  # the 2 missing
        self.assertEqual(evaluation.fp_ov, 3)  # the 3 overlapping
        self.assertEqual(evaluation.fn_ov, 3)  # the 3 overlapping

        ret = evaluation.compute('half_overlapping')

        self.assertEqual(ret.precision, (3 + 6 / 2) / 10)
        self.assertEqual(ret.recall, (3 + 6 / 2) / 11)
        self.assertEqual(ret.f_measure, 2 * ((3 + 6 / 2) / 10 * (3 + 6 / 2) / 11) / ((3 + 6 / 2) / 10 + (3 + 6 / 2) / 11))

    def test_exception_on_equality_operator(self):
        ann_1 = Entity(MUT_CLASS_ID, 1, 'text_1')
        ann_2 = Entity(MUT_CLASS_ID, 2, 'text_2')

        Entity.equality_operator = 'not valid'
        self.assertRaises(ValueError, lambda: ann_1 == ann_2)

    def test_exception_on_strictness(self):
        evaluator = MentionLevelEvaluator()  # this is fine
        evaluation = (evaluator.evaluate(self.dataset))(MentionLevelEvaluator.TOTAL_LABEL)  # this is fine

        self.assertRaises(ValueError, evaluation.compute, 'strictness not valid')

    def test_subclass_analysis(self):
        evaluator = MentionLevelEvaluator(subclass_analysis=True)
        evaluations = evaluator.evaluate(self.dataset)

        self.assertEqual(evaluations(1).tp, 1)
        self.assertEqual(evaluations(2).tp, 2)

        self.assertEqual(evaluations(1).fp, 3)
        self.assertEqual(evaluations(2).fp, 1)

        self.assertEqual(evaluations(1).fn, 4)
        self.assertEqual(evaluations(2).fn, 1)

        self.assertEqual(evaluations(1).fp_ov, 2)
        self.assertEqual(evaluations(1).fn_ov, 2)
        self.assertEqual(evaluations(2).fp_ov, 1)
        self.assertEqual(evaluations(2).fn_ov, 1)

if __name__ == '__main__':
    unittest.main()
