from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import numpy as np

import tensorflow as tf

np.random.seed(71)


class LogisticRegression(object):
    """Numpy implementation of Logistic Regression."""
    def __init__(self, batch_size=64, lr=0.01, n_epochs=1000):
        self._batch_size = batch_size
        self._lr = lr
        self._n_epochs = n_epochs

    def get_dataset(self, X_train, y_train, shuffle=True):
        """Get dataset and information."""
        self._X_train = X_train
        self._y_train = y_train

        # Get the numbers of examples and inputs.
        self._n_examples = self._X_train.shape[0]
        self._n_inputs = self._X_train.shape[1]

        if shuffle:
            idx = list(range(self._n_examples))
            random.shuffle(idx)
            self._X_train = self._X_train[idx]
            self._y_train = self._y_train[idx]

    def _create_weights(self):
        """Create model weights and bias."""
        self._w = np.zeros(self._n_inputs).reshape(self._n_inputs, 1)
        self._b = np.zeros(1).reshape(1, 1)

    def _logit(self, X):
        """Logit: unnormalized log probability."""
        return np.matmul(X, self._w) + self._b

    def _sigmoid(self, logit):
        """Sigmoid function by stabilization trick.

        sigmoid(z) = 1 / (1 + exp(-z)) 
                   = exp(z) / (1 + exp(z)) 
                   = exp(z - z_max) / (exp(-z_max) + exp(z - z_max)),
        where z is the logit, and z_max is z - max(0, z).
        """
        logit_max = np.maximum(0, logit)
        logit_stable = logit - logit_max
        return np.exp(logit_stable) / (np.exp(-logit_max) + np.exp(logit_stable))
    
    def _model(self, X):
        """Logistic regression model."""
        logit = self._logit(X)
        return self._sigmoid(logit)

    def _loss(self, y, logit):
        """Cross entropy loss by stabilizaiton trick.

        cross_entropy_loss(y, z) 
          = - 1/n * \sum_{i=1}^n y_i * p(y_i = 1|x_i) + (1 - y_i) * p(y_i = 0|x_i)
          = - 1/n * \sum_{i=1}^n y_i * (z_i - log(1 + exp(z_i))) + (1 - y_i) * (-log(1 + exp(z_i))),
        where z is the logit, z_max is z - max(0, z), and log(1 + exp(z)) is the 
          logsumexp(z) = log(exp(0) + exp(z))
                       = log((exp(0) + exp(z)) * exp(z_max) / exp(z_max))
                       = z_max + log(exp(-z_max) + exp(z - z_max)).
        """
        logit_max = np.maximum(0, logit)
        logit_stable = logit - logit_max
        logsumexp_stable = logit_max + np.log(np.exp(-logit_max) + np.exp(logit_stable))
        self._cross_entropy = -(y * (logit - logsumexp_stable) + (1 - y) * (-logsumexp_stable))
        return np.mean(self._cross_entropy)

    def _optimize(self, X, y):
        """Optimize by stochastic gradient descent."""
        m = X.shape[0]

        y_hat = self._model(X) 
        dw = -1 / m * np.matmul(X.T, y - y_hat)
        db = -np.mean(y - y_hat)
        
        for (param, grad) in zip([self._w, self._b], [dw, db]):
            param[:] = param - self._lr * grad
            
    def _fetch_batch(self):
        """Fetch batch dataset."""
        idx = list(range(self._n_examples))
        for i in range(0, self._n_examples, self._batch_size):
            idx_batch = idx[i:min(i + self._batch_size, self._n_examples)]
            yield (self._X_train.take(idx_batch, axis=0), self._y_train.take(idx_batch, axis=0))

    def fit(self):
        """Fit model."""
        self._create_weights()

        for epoch in range(self._n_epochs):
            total_loss = 0
            for X_train_b, y_train_b in self._fetch_batch():
                y_train_b = y_train_b.reshape((y_train_b.shape[0], -1))
                self._optimize(X_train_b, y_train_b)
                train_loss = self._loss(y_train_b, self._logit(X_train_b))
                total_loss += train_loss * X_train_b.shape[0]

            if epoch % 100 == 0:
                print('epoch {0}: training loss {1}'.format(epoch, total_loss))

        return self

    def get_coeff(self):
        return self._b, self._w.reshape((-1,))

    def predict(self, X_test):
        return self._model(X_test).reshape((-1,))


# Reset default graph.
def reset_tf_graph(seed=71):
    tf.reset_default_graph()
    tf.set_random_seed(seed)
    np.random.seed(seed)


class LogisticRegressionTF(object):
    """A TensorFlow implementation of Logistic Regression."""
    def __init__(self, batch_size=64, learning_rate=0.01, n_epochs=1000):
        self._batch_size = batch_size
        self._n_epochs = n_epochs
        self._learning_rate = learning_rate

    def get_dataset(self, X_train, y_train, shuffle=True):
        """Get dataset and information."""
        self._X_train = X_train
        self._y_train = y_train

        # Get the numbers of examples and inputs.
        self._n_examples = self._X_train.shape[0]
        self._n_inputs = self._X_train.shape[1]

        idx = list(range(self._n_examples))
        if shuffle:
            random.shuffle(idx)
        self._X_train = self._X_train[idx]
        self._y_train = self._y_train[idx]
    
    def _create_placeholders(self):
        """Create placeholder for features and labels."""
        self._X = tf.placeholder(tf.float32, shape=(None, self._n_inputs), name='X')
        self._y = tf.placeholder(tf.float32, shape=(None, 1), name='y')
    
    def _create_weights(self):
        """Create and initialize model weights and bias."""
        self._w = tf.get_variable(shape=(self._n_inputs, 1), 
                                  initializer=tf.random_normal_initializer(0, 0.01), 
                                  name='weights')
        self._b = tf.get_variable(shape=(1, 1), 
                                  initializer=tf.zeros_initializer(), name='bias')
    
    def _create_model(self):
        # Create logistic regression model.
        self._logit = tf.add(tf.matmul(self._X, self._w), self._b, name='logit')
        self._logreg = tf.math.sigmoid(self._logit, name='logreg')

    def _create_loss(self):
        # Create cross entropy loss.
        self._cross_entropy = tf.nn.sigmoid_cross_entropy_with_logits(
            labels=self._y,
            logits=self._logit,
            name='y_pred')   
        self._loss = tf.reduce_mean(self._cross_entropy, name='loss')

    def _create_optimizer(self):
        # Create gradient descent optimization.
        self._optimizer = (
            tf.train.GradientDescentOptimizer(learning_rate=self._learning_rate)
            .minimize(self._loss))

    def build_graph(self):
        """Build computational graph."""
        self._create_placeholders()
        self._create_weights()
        self._create_model()
        self._create_loss()
        self._create_optimizer()

    def _fetch_batch(self):
        """Fetch batch dataset.s"""
        idx = list(range(self._n_examples))
        for i in range(0, self._n_examples, self._batch_size):
            idx_batch = idx[i:min(i + self._batch_size, self._n_examples)]
            yield (self._X_train[idx_batch, :], self._y_train[idx_batch, :])

    def fit(self):
        """Fit model."""
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())

            for epoch in range(self._n_epochs):
                total_loss = 0
                for X_train_b, y_train_b in self._fetch_batch():
                    feed_dict = {self._X: X_train_b, self._y: y_train_b}
                    _, batch_loss = sess.run([self._optimizer, self._loss],
                                             feed_dict=feed_dict)
                    total_loss += batch_loss * X_train_b.shape[0]

                if epoch % 100 == 0:
                    print('Epoch {0}: training loss: {1}'
                          .format(epoch, total_loss / self._n_examples))


def main():
    from sklearn.datasets import load_breast_cancer
    from sklearn.preprocessing import StandardScaler

    from metrics import accuracy

    breast_cancer = load_breast_cancer()
    data = breast_cancer.data
    label = breast_cancer.target.reshape(-1, 1)

    # Normalize features first.
    scaler = StandardScaler()
    data = scaler.fit_transform(data)

    # Split data into training/test data.
    test_ratio = 0.2
    test_size = int(data.shape[0] * test_ratio)

    X_train = data[:-test_size]
    X_test = data[-test_size:]
    y_train = label[:-test_size]
    y_test = label[-test_size:]

    # Train Numpy linear regression model.
    logreg = LogisticRegression(batch_size=64, lr=1, n_epochs=1000)
    logreg.get_dataset(X_train, y_train, shuffle=True)
    logreg.fit()

    p_pred_train = logreg.predict(X_train)
    y_pred_train = (p_pred_train > 0.5) * 1
    accuracy(y_train, y_pred_train)
    p_pred_test = logreg.predict(X_test)
    y_pred_test = (p_pred_test > 0.5) * 1
    accuracy(y_test, y_pred_test)

    # Train TensorFlow logistic regression model.
    reset_tf_graph()
    logreg_tf = LogisticRegressionTF()
    logreg_tf.get_dataset(X_train, y_train)
    logreg_tf.build_graph()
    logreg_tf.fit()

    p_pred_train = logreg_tf.predict(X_train)
    y_pred_train = (p_pred_train > 0.5) * 1
    accuracy(y_train, y_pred_train)
    p_pred_test = logreg_tf.predict(X_test)
    y_pred_test = (p_pred_test > 0.5) * 1
    accuracy(y_test, y_pred_test)


if __name__ == '__main__':
    main()
