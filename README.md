# introSpect
Shortcuts to inspect features of Python functions from within to support a personal flavor of analysis workflow. 
**Under development**

## Motivation
The central idea behind this package is to be able to conveniently run Python functions via Nextflow, thus facilating development process and prototyping.  
Key issues adressed are:  
- converting the function into a command line tool  
- adding help to argparse from the docstrings  
- converting scripts into notebook-style markdown file  
- providing a prototype class in Python that can easily be converted into a Nextflow proccess  
- automatically generating a nextflow pipeline from process objects

## commandLines
Inspired by [Python fire](https://github.com/google/python-fire), but tailored to personal needs. Ensures that documentation is added to every reincarnation of the script, let it be imported, called from command line or integrated into a Nextflow pipeline.  
A minimal example below involves a function that is to be executed when the script is called from command line and the `main` function specifying what should be exposed to the commannd line and how to handle outputs.

```python
import introSpect

def example_function(my_name: str) -> str:
    """
    An example.

    Parameters
    ----------
    my_name
        Person to greet.
    
    Returns
    -------
    Greeting
    """
    
    return "Hello" + my_name

def main():

    """
    Define what should be executed when invoked from command line.
    """
    modified_kws = {
        "verbose": (
            0,
            "-v",
            "--verbose",
            {"dest": "verbose", "default": False, "action": "store_true"},
        ),
        "outFile": (
            1,
            "-o",
            "--outFile",
            {
                "dest": "outFile",
                "help": "Location where results should be saved. If not specified, STDOUT will be used.",
            },
        ),
    }
    mainFunction = introSpect.commandLines.cmdConnect(example_function, modified_kws)
    mainFunction.eval()
    mainFunction.save()
    return
```

## flowNodes
Similar to [FlowCraft](https://github.com/assemblerflow/flowcraft), but focuses on integrating custom Python functions instead of ready-made modules into the pipeline.  
Each process has to be defined as a Python class, setting input and output channels, directives and other parameters as features of this class. In a minimal example case, one only needs to define channel specifications and the function to be executed:

```python
import introSpect
nextflowProcess = introSpect.flowNodes.nextflowProcess

class exampleProcess(nextflowProcess):
  """
  Nextflow process to execute the function below.
  """

  def dependencies(self):
      return {
          'imports': ['import os'],
      }

  def channel_specifications(self):
      return {
          'example_input': ('val', 'example_input', 'my_name', None, True),
          'example_output':  ('file', "'greet.txt'", 'outFile', None, False),
      }
      
  def process(self, my_name: str) -> str:
      """
      An example.

      Parameters
      ----------
      my_name
          Person to greet.

      Returns
      -------
      Greeting
      """

      return "Hello" + my_name
```

The Nextflow pipeline is then compiled from the defined proccesses.

```python

conda = 'PATH_TO_A_CONDA_ENV'
location = 'PATH_TO_WHERE_PIPELINE_SHOULD_RESIDE'

main_kws = {
    'example_input': "Anonymous",
}
nodes = [exampleProcess(inchannels=['example_input'], outchannels=['example_output'], conda=conda),]
introSpect.flowNodes.channelNodes(*nodes, main_kws=main_kws, location=location+'/pipeline')
```

## captureIntoNotebook
A modul that converts a given function into a notebook in markdown format. The motivation beind this is that figures often have to be modified slightly: change colorpalette, size or the order of categories. If this is requested, the easiest way is to go back to an analysis step where the data is already processed and only the plotting function has to be rerun.  
Keeping datatable, the code for plotting and the figure together in markdown is inspired by both R markdown and [Reportsrender](https://github.com/grst/reportsrender), but in this case the notebook is not being run during pipeline execution, just saved for the record and the main report file is also not derived from the notebook. 

