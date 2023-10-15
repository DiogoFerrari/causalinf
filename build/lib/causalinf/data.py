import os
import pkg_resources
import pandas as pd

class load():

    def __new__(self, data=None):
        path_data = pkg_resources.resource_filename(__name__, 'data/')
        self.files = os.listdir(path_data)
        return self.__load_data__(self, data=data)
    
    def __load_data__(self, data=None):
        """Load a data set if it exists in the package

        :param data: Name of the data set to load
        :type data: str
        :returns: A dataset specified in 'data'
        :rtype: a pandas DataFrame
        """
        if data is not None:
            if data not in self.files:
                print(f"{data} not in the package.\n")
                self.__print_files__(self=self)
                df = None
            else:
                fn = pkg_resources.resource_filename(__name__, f'data/{data}')
                df = pd.read_csv(fn, sep=';')
        else:
            self.__print_files__(self=self)
            df = None
        return df

    def __print_files__(self):
        """Print names of the data files available

        :returns: None
        """
        print("Data files available:")
        for file in self.files:
            print(file)
        print("")
        return None
        
