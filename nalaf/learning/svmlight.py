import os
import sys
import subprocess
from random import random
import tempfile
from nalaf import print_warning, print_verbose, print_debug


class SVMLightTreeKernels:
    """
    Base class for interaction with Alessandro Moschitti's Tree Kernels in SVM Light
    """

    def __init__(self, svmlight_dir_path='', model_path=tempfile.NamedTemporaryFile().name, use_tree_kernel=True):
        self.svmlight_dir_path = svmlight_dir_path
        """
        The directory where the executables svm_classify and svm_learn are located.
        Defaults to the empty string '', which then means that the svmlight executables must be in your binary path
        """

        executables_extension = '' if sys.platform.startswith('linux') or sys.platform.startswith('darwin') else '.exe'
        self.svm_learn_call = os.path.join(self.svmlight_dir_path, ('svm_learn' + executables_extension))
        self.svm_classify_call = os.path.join(self.svmlight_dir_path, ('svm_classify' + executables_extension))

        self.model_path = model_path
        """the model (path) to read from / write to"""
        print_debug("SVM model file path: " + model_path)

        self.use_tree_kernel = use_tree_kernel
        """whether to use tree kernels or not"""


    def create_input_file(self, dataset, mode, features, minority_class=None, majority_class_undersampling=1.0):
        string = ''

        num_positive_instances = 0
        num_negative_instances = 0
        num_unlabeled_instances = 0

        allowed_features_keys = set(features.values())

        for edge in dataset.edges():
            if mode != 'train' or minority_class is None or edge.target == minority_class or random() < majority_class_undersampling:
                if edge.target == 1:
                    num_positive_instances += 1
                elif edge.target == -1:
                    num_negative_instances += 1
                else:
                    num_unlabeled_instances += 1

                # http://svmlight.joachims.org "A class label of 0 indicates that this example should be classified using transduction"
                instance_label = '0' if mode == 'predict' else str(edge.target)

                string += instance_label

                if self.use_tree_kernel:
                    string += ' |BT| '
                    string += edge.part.sentence_parse_trees[edge.sentence_id]
                    string += ' |ET|'

                for key in sorted(edge.features.keys()):
                    if key in allowed_features_keys:
                        value = edge.features[key]
                        string += ' ' + str(key) + ':' + str(value)

                string += '\n'

        instancesfile = tempfile.NamedTemporaryFile('w', delete=False)
        print_debug("{}: svmlight instances file: {}".format(mode, instancesfile.name))
        instancesfile.write(string)
        instancesfile.flush()
        # Note, we do not close the file

        total = (num_positive_instances + num_negative_instances + num_unlabeled_instances)
        print_debug("{}: svmlight instances, total: {} == #P: {} + #N: {} + #?: {}".format(mode, total, num_positive_instances, num_negative_instances, num_unlabeled_instances))

        return instancesfile


    def learn(self, instancesfile, c=0.5):

        with instancesfile:

            if self.use_tree_kernel:
                subprocess.call([
                    self.svm_learn_call,
                    '-v', '0',
                    '-t', '5',
                    '-T', '1',
                    '-W', 'S',
                    '-V', 'S',
                    '-C', '+',
                    '-c', str(c),
                    instancesfile.name,
                    self.model_path
                ])

            else:
                subprocess.call([
                    self.svm_learn_call,
                    '-c', str(c),
                    '-v', '0',
                    instancesfile.name,
                    self.model_path
                ])

            return self.model_path


    def tag(self, instancesfile):

        predictionsfile = tempfile.NamedTemporaryFile('r+', delete=False)
        print_debug("predict: svm predictions file: " + predictionsfile.name)

        call = [
            self.svm_classify_call,
            '-v', '0',
            instancesfile.name,
            self.model_path,
            predictionsfile.name
        ]
        exitcode = subprocess.call(call)

        if exitcode != 0:
            raise Exception("Error when tagging: " + ' '.join(call))

        predictionsfile.flush()
        # Note, we do not close the file

        return predictionsfile


    def read_predictions(self, dataset, predictionsfile, threshold=0):
        values = []
        with predictionsfile:
            predictionsfile.seek(0)

            for line in predictionsfile:
                prediction = float(line.strip())
                print_debug("  pred: " + str(prediction))

                # http://svmlight.joachims.org For classification, the sign of this value determines the predicted class -- CAUTION, relna (Ashish), had it set before to exactly: '-0.1' (was this a bug or a conscious decision to move the threshold of classification?)
                # See more information in: https://github.com/Rostlab/relna/issues/21
                if prediction > threshold:
                    values.append(+1)
                else:
                    values.append(-1)

            if (len(values) > 1):
                for index, edge in enumerate(dataset.edges()):
                    edge.target = values[index]
            else:
                raise Exception("EMPTY PREDICTIONS FILE -- This may be due to too small dataset or too few of features. Predictions file: " + predictionsfile.name)

        return dataset.form_predicted_relations()
