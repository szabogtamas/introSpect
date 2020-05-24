#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
) 

import textwrap, re, inspect
import introSpect

__name__, __package__, invoked_directly = introSpect.cmdSupport(
    __name__, __package__, __file__
)

def turnInNotebook(function_to_capture: str,
    *argv,
    notebooktitle: str = ''
    ) -> str:
    """
    Convert a Pythonic Nextflow process into a notebook, registering the parameters
    passed over for reproducibility. Designed primarily to capture plotting functions.

    Parameters
    ----------
    function_to_capture
        File name of the script that is to be converted into a notebook.
    argv
        Passthrough arguments that will be recorded.
    notebooktitle
        Title to be displayed in the notebook.

    Returns
    -------
    A mapped list.
    """

    ### Get source code of the target function and parameters that were called
    target = __import__(function_to_capture.replace('.py', ''), globals(), locals(), level=1)
    fullsource = inspect.getsource(target)
    imports, definitions = fullsource.split('\ndef process(')
    argvals = introSpect.commandLines.cmdConnect(target.process)
    argvals, rest = argvals.cmd_args.parse_known_args(argv)
    argvals = vars(argvals)

    ### Create a header for the notebook with title and basic settings, like imports
    s = '# '+ notebooktitle + '  \n  \n'
    s += textwrap.dedent(target.process.__doc__.replace('\n', '  \n'))
    s += '\n  ## Imports and parameters  \n  \n'
    importblock = '```python\n%matplotlib notebook\n\nimport matplotlib.pyplot as plt\n'
    imports = ' '.join(imports.split(' '))
    imports = imports.split('\n')
    for i in imports:
        if i != '':
            if i[0] != '#':
                if i in ['import matplotlib', "matplotlib.use('Agg')", 'import matplotlib.pyplot as plt', 'from matplotlib import pyplot as plt'] or i[:6] == 'plt =':
                    i = '# ' + i
                importblock += i + '\n'
    importblock += '\n```\n'
    s += importblock

    ### State the definition of parameters that were passed to the function
    paramblock = '```python\n'
    for k, v in argvals.items():
        if isinstance(v, str):
            if os.path.isfile(v):
                if os.path.realpath(v).find('/pipeline/work/') > 0:
                    v = '../tables/' + os.path.basename(v)
            v ="'"+v+"'"
        paramblock += k + ' = ' + str(v) + '\n'
    paramblock += '```\n'
    s += paramblock + '\n  \n'

    ### Find the source of the target function inside the script and strip off extras
    definitions = definitions.split('"""')[2]
    match = re.search("(\sreturn\s|\sdef\s\S+\(\)\:)", definitions)
    definitions = definitions[:match.start()]
    definitions = textwrap.dedent(definitions)
    definitions = definitions.split('### ')

    ### Add the source as plain lines of code
    s += '\n  ## Body of the process  \n  \n'
    definitionblock = ''
    for e in definitions [1:]:
        if e not in ['', '\n', '\n\n', '\n\n\n', '\n\n\n\n', '\n\n\n\n\n\n']:
            deflines = e.split('\n')
            deflines[0] = '### ' + deflines[0] + '\n'
            funtext = []
            for d in deflines:
                if d != '':
                    funtext.append(d)
            lastwords = funtext[-1]
            if len(lastwords.split(' = ')) > 1:
                lastwords = lastwords.split(' = ')[0]
                lastwords = " ".join(lastwords.split())
                if len(lastwords.split(' ')) < 2:
                    funtext.append(lastwords) # The last defined variable gets printed
            e = '\n'.join(funtext)
            definitionblock += '```python\n ' + e +'\n```\n  \n'
    s += definitionblock
    return s

def main():
    mainFunction = introSpect.commandLines.cmdConnect(turnInNotebook, {'capturednotebook': (1, '--capturednotebook', {'dest': 'capturednotebook', 'help': 'Location where results should be saved. If not specified, STDOUT will be used.'}),})
    mainFunction.eval()
    mainFunction.save()
    return

__doc__ = turnInNotebook.__doc__
if invoked_directly:
    main()
