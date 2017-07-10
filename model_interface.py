import pickle
import random
import numpy as np
from sklearn.svm import SVC
from sklearn.utils import shuffle
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, VotingClassifier


def load_model(model_file):
    return pickle.load(open(model_file, 'rb'))


def balance_data(training_data):
    mode = 'CUT'

    N, D = training_data.shape
    num_ones = np.count_nonzero(training_data[:, D - 1])
    num_zeros = N - num_ones
    minimum = min(num_ones, num_zeros)
    minimizer = 1 if num_ones < num_zeros else 0

    if mode == 'CUT':
        new_data = np.zeros((minimum * 2, D))
        cursor = 0
        max_count = 0
        for i in range(N):
            if training_data[i][D - 1] == minimizer:
                new_data[cursor] = training_data[i]
            elif max_count < minimum:
                new_data[cursor] = training_data[i]
                max_count += 1
            else:
                cursor -= 1
            cursor += 1
        training_data = new_data

    elif mode == 'FLIP':
        difference = max(num_ones, num_zeros) - minimum
        flip_max = difference / 2
        max_count = 0
        for i in range(N):
            if training_data[i][D - 1] != minimizer and max_count < flip_max:
                max_count += 1
                training_data[i] = invert_symetrical_row(training_data[i])

    return training_data


def invert_symetrical_row(row):
    d = len(row)
    middle = (d - 1) / 2
    first_half = row[:middle]
    second_half = row[middle:-1]
    solution = row[d-1]

    row[:middle] = second_half
    row[middle:-1] = first_half

    if solution == 1:
        row[d-1] = 0
    elif solution == 0:
        row[d-1] = 1

    return row


def create_random_layers(num_layers, min_layers, max_layers):
    layers = []
    for _ in range(num_layers):
        layer = []
        for size in range(random.randint(min_layers, max_layers)):
            layer.append(random.randint(100, 250))
        layers.append(tuple(layer))
    return layers


def grid_search(data):
    # organize data
    training_data = preprocess_data(data)
    training_data = shuffle(training_data)
    #training_data = balance_data(training_data)
    X, y = split_xy(training_data)

    param_grid = [
        {
            'criterion': ['friedman_mse'],
            'max_depth': [3],
            'learning_rate': [0.03],
            'max_features': [35],
            'n_estimators': [50],
            'min_impurity_split': [1e-5],
            'subsample': [0.9],
            'random_state': [4812135, 4214135, 5812135, 222816138, 14816136]
        },
    ]

    estimator = GradientBoostingClassifier(
        criterion='friedman_mse',
        max_depth=3,
        learning_rate=0.03,
        max_features=35,
        n_estimators=50,
        min_impurity_split=1e-5,
        subsample=0.9,
        random_state=4816135
    )

    # build model pipeline
    grid = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        verbose=3,
        cv=3,
        n_jobs=1,
        error_score=0
    )
    model_pipe = Pipeline(
        [
            ('scaler', StandardScaler()),
            ('predictor', grid)
        ]
    )

    # fit and output data
    print 'Fitting grid'
    model_pipe.fit(X, y.ravel())

    core_model = model_pipe.named_steps['predictor']

    print 'Best Params: ({})'.format(core_model.best_score_)
    print core_model.best_params_
    stds = core_model.cv_results_['std_test_score']
    means = core_model.cv_results_['mean_test_score']
    results = []
    for mean, std, params in zip(means, stds, core_model.cv_results_['params']):
        results.append((mean, "%0.3f (+/-%0.03f) for %r" % (mean, std * 2, params)))
    results.sort(key=lambda tup: tup[0], reverse=True)
    for res in results:
        print res[1]


def predict_with_model(model, X, removeLast=False):
    X = preprocess_data(X)
    if removeLast:
        X, _ = split_xy(X)
    return model.predict_proba(X)


def save_model(model, model_file):
    pickle.dump(model, open(model_file, 'wb'))


def create_model(training_data, random_seed, balance=False):
    print 'Creating new model'
    if random_seed == 0:
        random_seed = random.randint(0, 10000000)
    print 'Using model random seed: {}'.format(random_seed)

    training_data = preprocess_data(training_data)
    training_data = shuffle(training_data)
    if balance:
        training_data = balance_data(training_data)
    X, y = split_xy(training_data)
    
    modelPipe = Pipeline(
        [
            ('scaler', StandardScaler()),
            ('predictor', _create_model(random_seed))
        ]
    )
    model_pipe = _fit_model(modelPipe, X, y)
    model = model_pipe.named_steps['predictor']
    return model_pipe


def preprocess_data(data):
    n, d = data.shape[0], len(data[0])
    treated = np.zeros((n, d))
    for i in range(n):
        for j in range(d):
            if data[i][j] in ['"Home"', '"RIGHT"', '"AMERICAN"', '""', '']:
                treated[i, j] = 1
            elif data[i][j] in ['"Away"', '"LEFT"', '"NATIONAL"']:
                treated[i, j] = 0
            else:
                treated[i, j] = data[i][j]

    return treated


def split_xy(data):
    return np.split(data, [-1], 1)


def _create_model(random_seed):
    return MLPClassifier(
                activation='relu',
                alpha=2.4, hidden_layer_sizes=(250, 300, 250, 200, 50),
                random_state=random_seed,
            )

    return VotingClassifier(estimators=[
            ('svc-rbf', SVC(
                probability=True,
                kernel='rbf',
                C=2.2, gamma=0.001,
                random_state=random_seed,
            )),
            ('svc-sigmoid', SVC(
                probability=True,
                kernel='sigmoid',
                C=3.9, gamma=0.0011,
                random_state=random_seed,
            )),
            ('mlp', MLPClassifier(
                activation='relu',
                alpha=6, hidden_layer_sizes=(250, 150),
                random_state=random_seed,
            )),
            ('ada', AdaBoostClassifier(
                n_estimators=30
            )),
            ('forest', RandomForestClassifier(
                n_estimators=8,
                max_features='log2',
                max_depth=5,
            )),
            ('grad', GradientBoostingClassifier(
                criterion='friedman_mse',
                max_depth=4,
                learning_rate=0.03,
                max_features=35,
                n_estimators=50,
                min_impurity_split=1e-5,
                subsample=0.9,
                random_state=4816135
            )),
            ('logi', LogisticRegression(
                solver='liblinear',
                C=13, penalty='l1',
                random_state=random_seed,
            )),
        ],
        voting='soft',
    )


def _fit_model(model, X, y):
    X = preprocess_data(X)
    y = preprocess_data(y)
    print 'Fitting model on {} examples'.format(X.shape[0])
    model.fit(X, y.ravel())
    return model
