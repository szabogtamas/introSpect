import os, sys
from typing import Tuple, Union, Callable


def cmdSupport(name: str, package: str, fn: str,) -> Tuple[str, str, bool]:

    """
    Advanced support for command line execution of package components. Fixes import
    from sibling scripts within the package even if invoked from command line.

    Parameters
    ----------
    name
        Name of the script to be referenced during import.
    package
        Parent package of the script.
    fn
        File name of the script.
    
    Returns
    -------
    name
        Name of the script to be referenced during import.
    package
        Parent package of the script.
    invoked_directly
        If the script was invoke via command line or imported from another script.
    """

    invoked_directly = False
    if name == "__main__":
        invoked_directly = True
        dir_path = os.path.dirname(os.path.realpath(fn))
        sys.path.append(os.path.dirname(dir_path))
        package = os.path.basename(dir_path)
        name = package + "." + fn[:-3]
    return name, package, invoked_directly


def hint(verbose: bool, *vargs) -> None:

    """
    Print only if verbosity is desired.

    Parameters
    ----------
    verbose
        If the following inputs need to be printed.
    args
        Strings that need to be printed
    """

    if verbose:
        print("\n", *vargs)
    return
