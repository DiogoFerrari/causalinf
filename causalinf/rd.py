
class estimate():

    def __init__(self, formula):
        """Fit RDD model

        :param formula: A formula that specifies the model
        :type formula: string
        :returns: Object of class RDD
        :rtype: class

        """
        self.formula = formula

    def summary(self):
        """summarize

        :returns: Print summary of RDD estimation
        :rtype: None

        """
        print(self.formula)
        return None
