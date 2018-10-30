import argparse
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, make_scorer
from sklearn.model_selection import GridSearchCV

from time import time

from falkon import Falkon
from utility.kernel import *


def main(path, semi_supervised, max_iterations, gpu):
    # loading dataset as ndarray
    dataset = np.load(path).astype(np.float32)
    print("Dataset loaded ({} points, {} features per point)".format(dataset.shape[0], dataset.shape[1] - 1))

    # adjusting label's range {-1, 1}
    dataset[:, 0] = (2 * dataset[:, 0]) - 1

    # defining train and test set
    x_train, x_test, y_train, y_test = train_test_split(dataset[:, 1:], dataset[:, 0], test_size=0.2, random_state=None)
    print("Train and test set defined (test: {} + , train: {} +, {} -)".format(np.sum(y_test == 1.), np.sum(y_train == 1.), np.sum(y_train == -1.)))

    # removing some labels (if semi_supervised > 0)
    labels_removed = int(len(y_train) * semi_supervised)
    if labels_removed > 0:
        y_train[np.random.choice(len(y_train), labels_removed, replace=False)] = 0
        print("{} labels removed".format(labels_removed))

    # removing the mean and scaling to unit variance
    scaler = StandardScaler()
    scaler.fit(x_train)
    x_train = scaler.transform(x_train)
    x_test = scaler.transform(x_test)
    print("Standardization done")

    # hyperparameters tuninig
    print("Starting grid search...")
    falkon = Falkon(nystrom_length=None, gamma=None, kernel_fun=gpu_gaussian, kernel_param=None, optimizer_max_iter=max_iterations, gpu=gpu)
    parameters = {'nystrom_length': [10000, ], 'gamma': [1e-6, ], 'kernel_param': [4, ]}
    gsht = GridSearchCV(falkon, param_grid=parameters, scoring=make_scorer(roc_auc_score), cv=3, verbose=3)
    gsht.fit(x_train, y_train)

    # printing some information of the best model
    print("Best model information: {} params, {:.3f} time (sec)".format(gsht.best_params_, gsht.refit_time_))

    # testing falkon
    print("Starting falkon testing routine...")
    y_pred = gsht.predict(x_test)
    accuracy = accuracy_score(y_test, np.sign(y_pred))
    auc = roc_auc_score(y_test, y_pred)
    print("Accuracy: {:.3f} - AUC: {:.3f}".format(accuracy, auc))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("dataset", metavar='path', type=str, help='path of the dataset used for this test')
    parser.add_argument("--semi_supervised", metavar='ss', type=float, default=0., help='percentage of elements [0, 1] to remove the label')
    parser.add_argument("--max_iterations", type=int, default=20, help="specify the maximum number of iterations during the optimization")
    parser.add_argument("--gpu", type=bool, default=False, help='enable the GPU')

    args = parser.parse_args()

    main(path=args.dataset, semi_supervised=args.semi_supervised, max_iterations=args.max_iterations, gpu=args.gpu)
