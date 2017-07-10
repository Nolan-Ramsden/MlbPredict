import argparse
import numpy as np
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from model_interface import (
    create_model, load_model, save_model, predict_with_model, split_xy, preprocess_data, grid_search
)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--load', action='store_true')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--create', action='store_true')
    parser.add_argument('--balance', action='store_true')
    parser.add_argument('--grid', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('-r', '--random', default=0, type=int)
    parser.add_argument('-m', '--model', default='./data/v2/model.pkl')
    parser.add_argument('-v', '--testdata',
                        default=['./data/v2/2016-all.csv'], type=str, nargs='+')
    parser.add_argument('-t', '--trainingdata',
                        default=['./data/v2/2015-all.csv'], type=str, nargs='+')
    return parser.parse_args()


def _load_csv(filepath):
    print 'Loading Data From {0}'.format(filepath)
    data = np.asarray(np.genfromtxt(filepath, delimiter=',', dtype=None))
    return shuffle(preprocess_data(data))


def _load_multiple(files):
    master_extra = None
    for extra_data_file in files:
        extra_data = _load_csv(extra_data_file)
        if master_extra is None:
            master_extra = extra_data
        else:
            master_extra = np.vstack((master_extra, extra_data))
    return master_extra


def do_grid_search(training_data_files):
    print'\n=========== BEGIN GRIDCV ============='
    training_data = _load_multiple(training_data_files)
    grid_search(training_data)
    print'\n============ END GRIDCV =============='


def cross_val_model(model, training_data_files):
    print'\n=========== BEGIN CROSSVAL ============='
    print ''
    num_folds = 5
    training_data = _load_multiple(training_data_files)
    print 'Cross validating with {} rows, {} folds'.format(
        training_data.shape[0], num_folds
    )
    training_data = shuffle(training_data)
    X_train, y_train = split_xy(training_data)
    scores = cross_val_score(model, X_train, y_train.ravel(), cv=num_folds)
    str = '%0.2f (+/- %0.2f)' % (scores.mean(), scores.std() * 2)
    print 'Cross-Val Model Accuracy: {}'.format(str)
    print'\n============ END CROSSVAL =============='


def test_model(model, training_data_files, test_data_files):
    print'\n=========== BEGIN TESTING ============='

    print '\nComputing training details'
    training_data = _load_multiple(training_data_files)

    X_train, y_train = split_xy(training_data)
    print 'Training Error ({} rows): {}'.format(
        X_train.shape[0], model.score(X_train, y_train)
    )

    print '\nTesting model against {} data sets'.format(len(test_data_files))
    if len(test_data_files) == 0:
        return

    master_test = None
    for data_file in test_data_files:
        print ''
        test_data = _load_csv(data_file)
        if master_test is None:
            master_test = test_data
        else:
            master_test = np.vstack((master_test, test_data))

        print 'Testing against {}'.format(data_file)
        X_test, y_test = split_xy(test_data)
        print 'Testing Error ({} rows): {}'.format(
            X_test.shape[0], model.score(X_test, y_test)
        )

    if len(test_data_files) > 1:
        print '\nTesting against all test data'
        master_test = shuffle(master_test)
        X_test, y_test = split_xy(master_test)
        print 'Testing Error ({} rows): {}'.format(
            X_test.shape[0], model.score(X_test, y_test)
        )
    print'\n============ END TESTING =============='


def get_model(args):
    if args.create:
        training_data = _load_multiple(args.trainingdata)
        return create_model(training_data, args.random, args.balance)
    elif args.load:
        print 'Loading model from {}'.format(args.model)
        return load_model(args.model)


if __name__ == '__main__':
    args = _parse_args()

    model = get_model(args)

    if args.save:
        print 'Saving model to {}'.format(args.model)
        save_model(model, args.model)

    if args.grid:
        do_grid_search(args.trainingdata)

    if args.test:
        test_model(model, args.trainingdata, args.testdata)

    if args.validate:
        cross_val_model(model, args.trainingdata)