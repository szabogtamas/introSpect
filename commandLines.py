import argparse, inspect, re, json
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from typing import Union, Callable, Sequence, List, Tuple

class cmdConnect():
    """
    Exposes a Python function by creating command line arguments for function parameters automatically.

    Attributes:
    ----------
    fun
        The function we want to expose to the command line.
    doc
        Parsed docstring of the function (dictionary)
    spect
        Result of the inspection (object)
    params
        Parameters that belong to the master function (list)
    args
        Argparse object created during init (object)
    eval
        Runs the function (function)
    results
        Stores the value(s) returned by the function 
    save
        Saves the result(s) to file(s) if file output was specified. Prints the result as a string otherwise (function) 
    """

    def __init__(
        self,
        fun: Callable,
        paramtune: Union[None, dict] = None,
        ):
        """
        Adds parameters of the function to argparse.
        Sets output files if needed.

        Parameters
        ----------
        fun
            The function we want to expose to the command line.
        paramtune
            A dictionary of tuples for those parameters that need extra settings in argparse.
            Keys are the parameter names in the function if associated with the input.
            First element of the tuple specifies if the argument is associated with the input (`0`) or the output.
            Last element is a dictionary, passed as keyword arguments to argparse.
            The remaining elements inbetween will be passed as positional arguments (alternative names for the parameter).
        """

        finetuned = {"self": (0, "--denied", {"dest": "self", 'default': None, "help": "A mock switch to prevent self of a function defined in an object get exposed.",},)}
        if paramtune is None:
            paramtune = dict()
        finetuned.update(paramtune)
        paramtune = finetuned.copy()
        argreverse = dict()
        
        # Collect information on the master function and its parameters
        doc = self.parseDocstring(fun)
        pars = doc['params']

        spect = inspect.getfullargspec(fun)
        parser = argparse.ArgumentParser(description=doc['description'], formatter_class=argparse.RawTextHelpFormatter)

        arglist = list()
        if isinstance(spect.args, list):
            arglist += spect.args
        if isinstance(spect.varargs, list):
            arglist += spect.varargs
        if isinstance(spect.kwonlyargs, list):
            arglist += spect.kwonlyargs
        pardef = spect.kwonlydefaults
        
        # Add version and an option that shows what is the master function and what other functions are defined in the script
        long_doc = 'The master function:\n\n'
        long_doc += fun.__name__+'\n'
        long_doc += fun.__doc__+'\n\n\n'
        long_doc += 'The helper functions:\n\n'
        for n, f in [o for o in inspect.getmembers(inspect.getmodule(fun)) if inspect.isfunction(o[1])]:
            if n not in ['main', fun.__name__]:
                long_doc += n+'\n'
                dc = f.__doc__
                if dc is None:
                    dc = ''
                long_doc += dc+'\n\n\n'
        
        try:
            parser.add_argument('-version', '--version', action='version', version=inspect.getmodule(fun).__version__, help='Displays script version if supplied')
        except:
            pass
        parser.add_argument('-i', '--inspect', action='version', version=long_doc, help='Shows what functions are defined')

        # Add a switch to peek into the results by printing or saving the first N lines only
        parser.add_argument('-p', '--peek', dest='displayMax', type=lambda s: [x for x in s.split(',')], help='Peek into the results by printing or saving the first N lines only')
        parser.register('action', 'exappend', self.ExtendAction)

        # Add an instance for every parameter of the master function to the main argparse parser
        for p in arglist:
            help_msg = ''
            if p in pars:
                help_msg = pars[p]
            tune = False
            if p in paramtune:
                t = paramtune[p]
                if t[0] == 0:
                    tune = True
            else:
                tune = True
                t = [0, p]
            if tune:
                if type(t[-1]) == dict:
                    kwargs = t[-1]
                    args = t[1:-1]
                else:
                    kwargs = dict()
                    args = t[1:]
                if 'help' not in kwargs:
                    kwargs['help'] = help_msg
                if 'default' not in kwargs:
                    if spect.kwonlydefaults is not None:
                        if p in spect.kwonlydefaults:
                            kwargs['default'] = spect.kwonlydefaults[p]
                if 'type' not in kwargs:
                    if p in spect.annotations:
                        tp = spect.annotations[p]
                        if tp in (int, float, list, tuple):
                            kwargs['type'] = tp
                        else:
                            try:
                                if list in tp.__args__:
                                    kwargs['type'] = list
                            except:
                                pass
                # Solve the comma or space problem
                if 'type' in kwargs:
                    if kwargs['type'] in [list, tuple, 'str_list', 'int_list', 'float_list']:
                        if 'nargs' not in kwargs:
                            kwargs['nargs'] = '*'
                        if 'action' not in kwargs:
                            kwargs['action'] = 'exappend'
                            if 'default' in kwargs:
                                if kwargs['default'] is not None:
                                    kwargs['default'] = []
                        if kwargs['type'] in ['int_list', 'float_list']:
                            if kwargs['type'] == 'int_list':
                                kwargs['type'] = self.intSplitter
                            else:
                                kwargs['type'] = self.floatSplitter
                        else:
                            kwargs['type'] = lambda s: s.split(',')
                if 'default' in kwargs and len(t) < 3:
                    kwargs['dest'] = p
                    args[0] = '--' + p
                if 'dest' in kwargs:
                    argreverse[kwargs['dest']] = args[0] + ' '
                else:
                    argreverse[args[0]] = ''
                parser.add_argument(*args, **kwargs)
            else:
                parser.add_argument(p, help=help_msg)
                argreverse[args[0]] = ''
            
        
        # Parameters defined in the finetune dictionary, but not belonging to the master input, are assumed to belong to the output
        returnlen = 1
        outnames = dict()
        for remaining in set(paramtune.keys()) - set(arglist + ['self']):
            t = paramtune[remaining]
            o = t[0]
            if t[1] is None:
                if o > returnlen:
                    returnlen = o
            else:
                if type(t[-1]) == dict:
                    kwargs = t[-1]
                    args = t[1:-1]
                else:
                    kwargs = dict()
                    args = t[1:]
                if 'dest' in kwargs:
                    outnames[o] = kwargs['dest']
                else:
                    outnames[o] = args[0]
                if o > returnlen:
                    returnlen = o
                parser.add_argument(*args, **kwargs)
        
        rl = []
        for i in range(returnlen):
            rl.append([outnames.pop(i+1, None), None])
            
        # Bind information that might be reused later to the object
        self.fun = fun
        self.doc = doc
        self.spect = spect
        self.params = arglist
        self.cmd_args = parser
        self.argreverse = argreverse
        self.results = rl
    
    class ExtendAction(argparse.Action):
        """
        Redefine the extension module of Argparse to support multiple list notations in command line.
        """
        def __call__(self, parser, namespace, values, option_string=None):
            items = getattr(namespace, self.dest) or []
            if type(items) is not list:
                items = []
            for v in values:
                items += v
            setattr(namespace, self.dest, items)


    def eval(self):
        """
        Run the master function and store its results.
        """
        
        self.args, rest = self.cmd_args.parse_known_args()
        args, kwargs = [], dict()
        spected = self.spect.args
        for p in self.params:
            if p in spected:
                args.append(getattr(self.args, p))
            else:
                kwargs[p] = getattr(self.args, p)
        rs = self.fun(*args, *rest, **kwargs)

        if rs is not None:
            if len(self.results) > 1:
                for i in range(len(rs)):
                    try:
                        resfile = self.results[i][0]
                        if resfile is not None:
                            resfile = getattr(self.args, resfile)
                    except:
                        resfile = None
                    try:
                        self.results[i] = (resfile, rs[i])
                    except:
                        self.results.append((resfile, rs[i]))
            else:
                try:
                    resfile = self.results[0][0]
                    if resfile is not None:
                        resfile = getattr(self.args, resfile)
                except:
                    resfile = None
                self.results = [(resfile, rs)]
        return


    def save(
        self,
        filenames: Union[None, str, list] = None,
        formatfunctions: Union[None, Callable, list] = None,
        formatargs: Union[None, dict, list] = None
        ) -> None:
        """
        Save the output of the master function.

        Parameters
        ----------
        filenames
            Overwrite the default value (None, meaning the string will be printed) of the file names.
        formatfunctions
            Specify how the output should be formatted. Using default formatters, (e.g. every list element in a new line) if not set.
        formatargs
            A dictionary of arguments for each format function that will be passed on.
        """

        N = len(self.results)

        if formatfunctions is not None:
            if type(formatfunctions) is Callable:
                formatfunctions = (formatfunctions)
        else:
            formatfunctions = []
            for i in range(N):
                formatfunctions.append(None)

        if formatargs is not None:
            if type(formatargs) is dict:
                formatargs = (formatargs)
            else:
                for i in range(N):
                    if formatargs[i] is None:
                        formatargs[i] = dict()
        else:
            formatargs = []
            for i in range(N):
                formatargs.append(dict())

        for i in range(N):
            o = ''
            fn, r = self.results[i]
            to_be_written = True
            if fn is not None:
                if fn[-5:] in '.json':
                    to_be_written = False
            if to_be_written:
                if formatfunctions[i] is None:
                    if isinstance(r, (pd.DataFrame, plt.Axes, sns.matrix.ClusterGrid)):
                        pass
                    else:
                        if isinstance(r, (str, int, float, dict, set, list, tuple, np.ndarray)):
                            if isinstance(r, (int, float)):
                                r = str(r)
                            else:
                                if isinstance(r, (set, list, tuple, np.ndarray)):
                                    if isinstance(r, set):
                                        r = list(r)
                                    row = r[0]
                                    if isinstance(row, (str, int, float, set, list, tuple, np.ndarray)):
                                        if isinstance(row, str):
                                            r = '\n'.join(r)+'\n'
                                        else:
                                            if not isinstance(r, np.ndarray):
                                                r = np.array(r)
                                            r = r.astype(str)
                                            if isinstance(row, (int, float)):
                                                r = '\n'.join(r)+'\n'
                                            else:
                                                r = '\n'.join(np.apply_along_axis(lambda x: np.asarray('\t'.join(x),dtype=object), 1, r))+'\n'
                                    else:
                                        if isinstance(row, dict):
                                            colnames = set()
                                            for d in r:
                                                colnames.update(d.keys())
                                            colnames = tuple(colnames)
                                            t = '\t'.join([str(x) for x in colnames]) + '\n'
                                            for d in r:
                                                t += '\t'.join([str(d[x]) for x in colnames]) + '\n'
                                            r = t
                                        else:
                                            try:
                                                r = '\n'.join([str(x) for x in r])+'\n'
                                            except:
                                                print('No built-in method to save result ['+str(i)+'] of type '+type(r).__name__)
                                else:
                                    if isinstance(r, dict):
                                        try:
                                            k, row = r.popitem()
                                            r[k] = row
                                        except:
                                            row = ''
                                        if isinstance(row, (str, int, float)):
                                            r = '\n'.join([str(x) + '\t' + str(y) for x, y in r.items()])+'\n'
                                        else:
                                            if isinstance(row, (set, list, tuple, np.ndarray)):
                                                r = '\n'.join([str(x) + '\t' + '\t'.join([str(z) for z in y]) for x, y in r.items()])+'\n'
                                            else:
                                                if isinstance(row, dict):
                                                    colnames = set()
                                                    for k, d in r.items():
                                                        colnames.update(d.keys())
                                                    colnames = tuple(colnames)
                                                    t = '\t'+'\t'.join([str(x) for x in colnames]) + '\n'
                                                    for k, d in r.items():
                                                        t += k + '\t' + '\t'.join([str(d[x]) for x in colnames]) + '\n'
                                                    r = t
                                                else:
                                                    try:
                                                        r = '\n'.join([str(x) + '\t' + str(y) for x, y in r.items()])+'\n'
                                                    except:
                                                        print('No built-in method to save result ['+str(i)+'] of type '+type(row).__name__)        
                        else:
                            try:
                                r = str(r)
                            except:
                                print('No built-in method to save result ['+str(i)+'] of type '+type(r).__name__)
                else:
                    r = formatfunctions[i](**formatargs[i])
            if self.args.displayMax is not None and not isinstance(r, plt.Axes, sns.matrix.ClusterGrid):
                rN = self.args.displayMax
                if isinstance(r, pd.DataFrame):
                    rN = int(rN[0])
                    if rN > 0:
                        r = r.head(rN)
                    else:
                        r = r.tail(-1*rN)
                else:
                    if len(rN) == 1:
                        rN = rN[0]
                        rC = None
                    else:
                        rN, rC = rN[:2]
                    if rC not in ['', None]:
                        r = r[:int(rC)]
                    if rN not in ['', None]:
                        rN = int(rN)
                        r = r.split('\n')[:rN]
                        r = '\n'.join(r)
                        if r[-1] != '\n':
                            r += '\n'
            if fn is None:
                if isinstance(r, plt.Axes):
                    print('Figure cannot be displayed')
                else:
                    print(r)
            else:
                if isinstance(r, (pd.DataFrame, plt.Axes, sns.matrix.ClusterGrid)):
                    if isinstance(r, pd.DataFrame):
                        r.to_csv(fn, sep='\t')
                    else:
                        if isinstance(r, plt.Axes):
                            if fn.split('.')[-1] in r.figure.canvas.get_supported_filetypes():
                                r.figure.savefig(fn)
                            else:
                                r.figure.savefig(fn+'.png')
                                r.figure.savefig(fn+'.pgf')
                        else:
                            r.savefig(fn)
                else:
                    if fn[-5:] == '.json':
                        with open(fn, 'w') as f:
                            json.dump(r, f)
                    else:
                        with open(fn, 'w') as f:
                            f.write(r)
        return


    def parseDocstring(
        self,
        fun: Callable
        ) -> dict:
        """
        Parse the docstring of a function to extract parameter descriptions.

        Parameters
        ----------
        fun
            The function we need the parsed docstring for.
            
        Returns
        -------
        A dictionary with all the descriptions.
        """

        PARAM_OR_RETURNS_REGEX = re.compile("(?:\s{2,}(Parameters|Returns)\s+-{3,})")
        RETURNS_REGEX = re.compile("\s{2,}Returns\s+-{3,}\s+(?P<doc>.*)", re.S)
        PARAMSTART_REGEX = re.compile("(?:\s{2,}Parameters\s+-{3,})")
        PARAM_REGEX = re.compile("\s+(?P<name>[\*\w]+)\n\s+(?P<doc>.*)", re.M)

        def reindent(string):
            return "\n".join(l.strip() for l in string.strip().split("\n"))

        params = dict()
        returns = ''
        short_description, description = '', ''

        docstring = fun.__doc__
        docstring = docstring.strip()
        if docstring:
            lines = docstring.split("\n", 1)
            short_description = lines[0]

            if len(lines) > 1:
                params_returns_desc = ''

                match = PARAM_OR_RETURNS_REGEX.search(docstring)
                if match:
                    long_desc_end = match.start()
                    params_returns_desc = docstring[long_desc_end:].strip()
                    description = docstring[:long_desc_end].rstrip()

                match = RETURNS_REGEX.search(params_returns_desc)
                if match:
                    returns = reindent(match.group("doc"))
                    long_desc_end = match.start()
                    params_returns_desc = params_returns_desc[:long_desc_end]
                
                match = PARAMSTART_REGEX.search(params_returns_desc)
                if match:
                    long_desc_start = match.end()
                    params_returns_desc = params_returns_desc[long_desc_start:]

                params = dict(PARAM_REGEX.findall(params_returns_desc))
            else:
                description = short_description
        return {
            "description": description,
            "short_description": short_description,
            "params": params,
            "returns": returns
        }


    def intSplitter(
        self,
        s: str
        ) -> list:
        """
        Split a string into list of integers.
        Changes NaN to zero.

        Parameters
        ----------
        s
            The string(s) supplied via command line.
            
        Returns
        -------
        List of integers.
        """

        l = []
        for e in s.split(','):
            try:
                e = int(e)
            except:
                e = 0
            l.append(e)
        return l


    def floatSplitter(
        self,
        s: str
        ) -> list:
        """
        Split a string into list of floats.
        Changes NaN to zero.

        Parameters
        ----------
        s
            The string(s) supplied via command line.
            
        Returns
        -------
        List of floats.
        """

        l = []
        for e in s.split(','):
            try:
                e = float(e)
            except:
                e = 0
            l.append(e)
        return l
