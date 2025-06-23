import abc

class TrainValTestSplitter(abc.ABC):

    @abc.abstractmethod
    def split(self, start, val_delta, test_delta, seed):
        pass