#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, subprocess, inspect, textwrap, shutil
from typing import Union, Tuple, Callable
from . import commandLines, captureIntoNotebook, hint


class nextflowProcess:
    """
    Prototype object for hybrid python code that will be split up into a nextfow process
    and an executable Python script.
    """

    def __init__(
        self,
        command=None,
        params=None,
        inchannels=None,
        outchannels=None,
        inputs=None,
        outputs=None,
        conda=None,
        container=None,
        process_settings=None,
        capture=False,
        capturepars=["notebooktitle", "capturednotebook"],
        modified_kws={
            "outFile": (
                1,
                "-o",
                "--outFile",
                {
                    "dest": "outFile",
                    "help": "Location where results should be saved. If not specified, STDOUT will be used.",
                },
            ),
        },
        manualDoc=None,
    ):
        self.processname = self.__class__.__name__
        self.command = command
        if inchannels is None:
            inchannels = []  # Channel names that are used as input for the process
        self.inchannels = inchannels
        if outchannels is None:
            outchannels = []  # Channel names that are used as output for the process
        self.outchannels = outchannels
        if params is None:
            params = dict()  # Default parameters for the python function under the hood
        self.params = params
        self.inputs = inputs
        self.outputs = outputs
        self.conda = conda
        self.container = container
        self.process_settings = process_settings
        if manualDoc is None:
            manualDoc = (
                ""  # If anything is to be added to the description of the process
            )
        self.manualDoc = manualDoc
        if modified_kws is None:
            modified_kws = (
                dict()
            )  # Parameters added to argparse of the function. Output file names, for example.
        self.capture = capture  # Converts the process into markdown of a notebook (easily modify plots)
        self.capturepars = capturepars
        self.modified_kws = (
            modified_kws  # Keywords controling the outputs of the process function
        )
        self.cmdpars = None
        self.cmdouts = None
        self.cmdpreset = dict()
        self.addedparams = []
        self.customize_features()

        if container is not None:
            self.process_settings = dict()
            self.process_settings["container"] = container

    def dependencies(self):
        return dict()

    def directives(self):
        return dict()

    def directives(self):
        return dict()

    def channel_pretreat(self):
        """
        Dictionary key is the channel name, values are:
            channel type
            nextflow variables
            python variables
            channel operations
            if channel should be prefixed with params
        """
        return list()

    def process(self):
        return None

    def customize_features(self):
        return None

    def compile_directives(self):
        directives = self.directives()
        dirs = "\n"
        if self.conda not in [None, ""]:
            directives["conda"] = self.conda
        for k, v in directives.items():
            dirs += k + " " + v + "\n"
        return textwrap.indent(dirs, "            ")

    def compile_inputs(self):
        flags, lazy, positionals = [], [], {}
        inputs = "\n"
        if self.inputs is None:
            specified_channels = self.channel_specifications()
            if self.cmdpars is None:
                self.cmdpars = dict()
                params = dict()
                for k, v in self.params.items():
                    if isinstance(k, tuple):
                        for i, q in enumerate(k):
                            if q not in [None, ""]:
                                params[q] = v[i]
                                self.cmdpars[q] = q + " "
                    else:
                        if k not in [None, ""]:
                            params[k] = v
                            self.cmdpars[k] = k + " "
                self.params = params
                remainder = dict()
                spc = self.inchannels + self.outchannels
                for k, v in specified_channels.items():
                    if k not in spc:
                        self.inchannels.append(k)
            else:
                for k, v in self.cmdpars.items():
                    if k not in self.params:
                        if k in self.cmdpreset:
                            self.params[k] = self.cmdpreset[k]
                        else:
                            self.params[k] = None
                remainder = self.params.copy()
            for k, v in specified_channels.items():
                if v[0] is None:
                    pass
                else:
                    if k in self.inchannels:
                        if type(v[1]) is tuple:
                            channelVariables = []
                            for e in v[1]:
                                if e[0] == "*":
                                    channelVariables.append(e[1:])
                                else:
                                    channelVariables.append(e)
                            channelVariable = ", ".join(channelVariables)
                        else:
                            channelVariables = v[1].split(", ")
                            channelVariable = v[1]
                            for i, e in enumerate(channelVariables):
                                if e[0] == "*":
                                    channelVariables[i] = e[1:]
                                else:
                                    channelVariables[i] = e
                        if channelVariable[0] == "*":
                            channelVariable = channelVariable[1:]
                        if type(v[2]) is not tuple:
                            pyVariable = (v[2],)
                        else:
                            pyVariable = v[2]
                        for i in range(len(pyVariable)):
                            cd = channelVariables[i]
                            if cd[:5] == "file(":
                                cd = cd.replace("file(", "")
                                cd = cd[:-1]
                            if cd[0] in ["'", '"', "\n"]:
                                if cd[0] == "*":
                                    cd = '"${' + cd[1:] + '}"'
                                else:
                                    cd = cd.replace("'", "")
                                    cd = cd.replace('"', "")
                                    cd = " " + cd
                            else:
                                cd = "$" + cd
                            e = pyVariable[i]
                            if e not in [None, "None"]:
                                remainder.pop(e, None)
                                if e in self.cmdpars:
                                    cm = self.cmdpars[e]
                                    if cm == "":
                                        positionals[e] = cd
                                    else:
                                        flags.append(cm + cd)
                                else:
                                    if e == "":
                                        lazy.append(cd)
                                    else:
                                        if e[0] == "*":
                                            lazy.append(cd)
                                        else:
                                            pass  # flags.append("--" + e + " $" + cd)
                            else:
                                if e in self.cmdpars:
                                    cm = self.cmdpars[e]
                                    if cm == "":
                                        positionals[e] = cd
                                    else:
                                        flags.append(cm + cd)
                        if v[4]:
                            channelSource = " from params." + k
                            self.addedparams.append(k)
                        else:
                            channelSource = " from " + k
                        if v[3] is None:
                            channelTransform = ""
                        else:
                            channelTransform = v[3]
                        inputs += (
                            v[0]
                            + " "
                            + channelVariable
                            + channelSource
                            + channelTransform
                            + "\n"
                        )
            for k, v in remainder.items():
                inputs += "val " + k + " from params." + k + "\n"
                self.addedparams.append(k)
                if k in self.cmdpars:
                    cm = self.cmdpars[k]
                    if cm == "":
                        positionals[k] = "$" + k
                    else:
                        flags.append(cm + "$" + k)
                else:
                    flags.append("--" + k + " $" + k)
            self.flags, self.positionals, self.lazy = flags, positionals, lazy
        else:
            for e in self.inputs:
                inputs += e + "\n"
        return textwrap.indent(inputs, "                ")

    def compile_outputs(self):
        out = "\n"
        if self.outputs is None:
            specified_channels = self.channel_specifications()
            remainder = self.cmdouts.copy()
            for k, v in specified_channels.items():
                if k in self.outchannels:
                    if type(k) is tuple:
                        channelName = "; ".join(k)
                        channelName = " into{" + channelName + "}"
                    else:
                        channelName = " into " + k
                    if type(v[1]) is tuple:
                        channelVariables = v[1]
                        channelVariable = ", ".join(channelVariables)
                    else:
                        channelVariables = v[1].split(", ")
                        channelVariable = v[1]
                    if type(v[2]) is not tuple:
                        pyVariable = (v[2],)
                    else:
                        pyVariable = v[2]
                    for i in range(len(pyVariable)):
                        e = pyVariable[i]
                        if e is not None:
                            remainder.pop(e, None)
                            cd = channelVariables[i]
                            if cd[0] in ["'", '"']:
                                cd = cd.replace("'", "")
                                cd = cd.replace('"', "")
                                cd = " " + cd
                            else:
                                cd = " $" + cd
                            if e in self.cmdpars:
                                cm = self.cmdpars[e]
                                if cm == "":
                                    self.positionals[e] = cd
                                else:
                                    self.flags.append(cm + cd)
                            else:
                                if e != "":
                                    self.flags.append("--" + e + cd)
                        else:
                            if e in self.cmdpars:
                                cm = self.cmdpars[e]
                                if cm == "":
                                    positionals[e] = cd
                                else:
                                    flags.append(cm + cd)
                    if v[3] is None:
                        channelTransform = ""
                    else:
                        channelTransform = v[3]
                    out += (
                        v[0]
                        + " "
                        + channelVariable
                        + channelName
                        + channelTransform
                        + "\n"
                    )
            for k, v in remainder.items():
                out += "val " + k + " into " + k + "\n"
                if k in self.cmdpars:
                    cm = self.cmdpars[k]
                    if cm == "":
                        self.positionals[k] = "$" + k
                    else:
                        self.flags.append(cm + "$" + k)
                else:
                    self.flags.append("--" + k + " $" + k)
        else:
            for e in self.outputs:
                out += e + "\n"
        return textwrap.indent(out, "                ")

    def compile_process(self, dr):
        if self.command is None:
            script_name = self.processname + ".py"
            script_file = dr + "/bin/" + script_name
            arguments = commandLines.cmdConnect(self.process, self.modified_kws)
            self.cmdpars = arguments.argreverse
            self.cmdpars.pop("self", None)
            self.cmdouts = dict()
            self.cmdpreset = arguments.spect.kwonlydefaults
            if self.cmdpreset is None:
                self.cmdpreset = dict()
            self.cmdorder = arguments.spect.args
            for v, t in arguments.results:
                if v in self.cmdpars:
                    self.cmdouts[v] = self.cmdpars.pop(v)
            conda = self.generate_py(script_file, dr)
            os.chmod(script_file, 0o775)
            if self.manualDoc in [None, ""]:
                if self.process.__doc__ is None:
                    self.manualDoc = ""
                else:
                    self.manualDoc = self.process.__doc__
        else:
            if self.__doc__ is None:
                self.manualDoc = ""
            else:
                self.manualDoc = self.__doc__
            if self.inputs is None:
                raise ValueError(
                    "The command does not seem to be a python function, so we cannot guess its inputs. Please supply a list of inputs channel statements!!!"
                )
        dependencies = self.dependencies()
        if self.conda in [None, ""]:
            if "conda" in dependencies and dependencies[conda] not in [None, ""]:
                self.conda = dependencies[conda]
        if self.container in [None, ""]:
            if "container" in dependencies and dependencies[container] not in [
                None,
                "",
            ]:
                self.container = dependencies[container]

    def compile_command(self):
        positionals = " "
        for k in self.cmdorder:
            if k in self.positionals:
                positionals += self.positionals[k] + " "
        command = (
            self.processname
            + ".py "
            + " ".join(self.flags)
            + positionals
            + " "
            + " ".join(self.lazy)
        )
        notebooktitle, capturednotebook = self.capturepars
        if self.capture:
            command += (
                "\n            captureIntoNotebook.py --notebooktitle $"
                + notebooktitle
                + " --capturednotebook $"
                + capturednotebook
                + " "
                + command
            )
        return command

    def check_container(self, containers, dr):
        if self.container in [None, ""]:
            if self.process_settings is not None:
                if "container" in self.process_settings:
                    self.container = self.process_settings["container"]
        else:
            if self.process_settings is None:
                self.process_settings = dict()
            self.process_settings["container"] = self.container

        if self.container in [
            None,
            "",
        ]:  # Might seem odd to check twice, but could be set to None in the previous step.
            pass
        else:
            if os.path.isfile(self.container):
                self.process_settings["container"] = self.container
            else:
                if self.container in containers:
                    fn = containers[self.container]
                else:
                    fn = self.container.split("://")[1]
                    fn = fn.replace("/", "_")
                    fn = fn.replace(":", "_")
                    fn = dr + "/" + fn + ".sif"
                    subprocess.run(["singularity", "build", fn, self.container])
                    containers[self.container] = fn
                self.container = fn
                self.process_settings["container"] = fn
        return containers

    def generate_py(self, fn, dr):
        # TODO reuse the commandLines version
        dependencies = {
            "conda": "",
            "container": "",
            "imports": [],
            "helpers": [],
            "git_packages": [],
            "inhouse_packages": [],
        }
        dependencies.update(self.dependencies())
        nonCondaCopy(
            dependencies["git_packages"],
            dependencies["inhouse_packages"],
            dr + "/packages",
        )
        recipe = textwrap.dedent(commandLines.startScriptConneted(dr + "/packages"))
        recipe += "\n" + "\n".join(dependencies["imports"]) + "\n\n"
        recipe += textwrap.dedent(inspect.getsource(self.process).replace("self,", ""))
        for helper_fun in dependencies["helpers"]:
            recipe += "\n" + textwrap.dedent(inspect.getsource(helper_fun)) + "\n"
        recipe += commandLines.endScriptConneted(
            self.process.__name__, self.modified_kws
        )
        with open(fn, "w") as f:
            f.write(recipe)
        return dependencies["conda"]

    def generate_nf(self):
        inputs = "hi"
        body = (
            """
        /*
        """
            + textwrap.indent(textwrap.dedent(self.manualDoc[:-1]), "        *")
            + """
        */
        """
            + textwrap.dedent(
                "\n        ".join(
                    ["\n            .".join(x) for x in self.channel_pretreat()]
                )
                + "\n    "
            )
            + """
        process """
            + self.processname
            + """ {
            """
            + self.compile_directives()
            + """
            input:"""
            + self.compile_inputs()
            + """
            output:"""
            + self.compile_outputs()
            + """
            """
            + '"""'
            + """
            """
            + self.compile_command()
            + """
            """
            + '"""'
            + """
        } 

        """
        )
        return textwrap.dedent(body)


class helloWorld(nextflowProcess):
    """
    A Pythonized version of the hello.nf (https://github.com/nextflow-io/hello/blob/master/main.nf).
    """

    def directives(self):
        return {
            "echo": "true",
        }

    def channel_pretreat(self):
        return [
            ["Channel", "from('Bonjour', 'Ciao', 'Hello', 'Hola')", "set{cheers}"],
        ]

    def channel_specifications(self):
        return {
            "cheers": ("val", "x", "x", None, False),
        }

    def process(
        self,
        x: str,
    ) -> None:
        """
        Print something on screen.

        Parameters
        ----------
        x
            The string to print.
        """

        print(x)
        return


def channelNodes(
    *args,
    location="",
    main_kws=None,
    queueRestriction=None,
    generalClusterProfile=None,
    generalSettings=None,
    containerPaths=None,
    labelSettings=None,
    returnFolder=False,
    verbose=True,
):
    os.makedirs(location + "/bin", exist_ok=True)
    os.makedirs(location + "/packages", exist_ok=True)

    if generalClusterProfile is None:
        generalClusterProfile = """
        profiles {
            standard {
                process.executor = 'local'
            }
            cluster {
                process.executor = 'sge'
                process.cpus = 1
                process.penv = 'smp'
                process.errorStrategy = 'ignore'
                process.clusterOptions = { '-V -S /bin/bash -q all.q@apollo-*' }
            }
        }
        """

    if queueRestriction is not None:
        generalClusterProfile += textwrap.dedent(
            """
        executor {
            $sge {
                queueSize = """
            + str(queueRestriction)
            + """
                pollInterval = '30sec'
            }
        }
        """
        )

    if generalSettings is None:
        generalSettings = """
        singularity {
            enabled = true
            autoMounts = true
        }
        """
    if containerPaths is None:
        containerPaths = dict()
    if labelSettings is None:
        labelSettings = dict()

    with open(location + "/bin/captureIntoNotebook.py", "w") as f:
        capturer = inspect.getsource(captureIntoNotebook)
        capturer = capturer.split("sys.path.append")
        capturer[0] += '\nsys.path.append("' + location + '/packages")\n'
        capturer = "sys.path.append".join(capturer)
        f.write(capturer)
    os.chmod(location + "/bin/captureIntoNotebook.py", 0o775)

    date_helper = '\n\nimport java.text.SimpleDateFormat\ndef date = new Date()\ndef sdf = new SimpleDateFormat("dd/MM/yyyy")\n'

    if main_kws is None:
        main_kws = dict()
    paramlist = dict()
    process_settings = dict()
    addedparams = []
    flowBody = ""
    if len(args) < 1:
        args = [helloWorld(inchannels=["cheers"])]
    for process in args:
        hint(verbose, "Adding process node:", process.processname)
        process.compile_process(location)
        flowBody += process.generate_nf()
        addedparams += process.addedparams
        paramlist.update(process.params)
        containerPaths = process.check_container(containerPaths, location)
        process_settings[process.processname] = process.process_settings
    mainparams = []
    if main_kws is None:
        main_kws = dict()
    for k, v in main_kws.items():
        if isinstance(v, tuple):
            if len(v) == 1:
                v = v[0]
            else:
                v = list(v)
        if isinstance(v, str):
            v = "'" + v + "'"
        if type(v) is dict:
            v = [[q, w] for q, w in v.items()]
        mainparams.append("params." + k + " = " + str(v))
    for k, v in paramlist.items():
        if type(v) is tuple:
            k, v = v
        if k not in main_kws and k in addedparams:
            if isinstance(v, str):
                v = "'" + v + "'"
            if type(v) is dict:
                v = [[q, w] for q, w in v.items()]
            if v is None:
                v = "'None'"
            if type(v) is tuple:
                if len(v) == 1:
                    v = v[0]
                else:
                    v = list(v)
            mainparams.append("params." + k + " = " + str(v))
    flowBody = "#!/usr/bin/env nextflow\n\n" + date_helper + "\n\n" + flowBody
    with open(location + "/main.nf", "w") as f:
        f.write(flowBody)
    processSettings = "process {\n"
    for k, v in labelSettings.items():
        s = "    withLabel:" + k + "     {\n"
        for w in v:
            s += "        " + w + "\n"
        processSettings += s + "    }\n"
    for k, v in process_settings.items():
        if v is not None:
            s = "    withName:" + k + "     {\n"
            for q, w in v.items():
                if isinstance(w, str):
                    w = "'" + w + "'"
                s += "        " + q + " = " + str(w) + "\n"
            processSettings += s + "    }\n"
    processSettings += "}\n"
    configBody = (
        "\n".join(mainparams)
        + "\n\n"
        + textwrap.dedent(generalClusterProfile)
        + processSettings
        + textwrap.dedent(generalSettings)
    )
    with open(location + "/nextflow.config", "w") as f:
        f.write(configBody)
    if returnFolder:
        return location
    return


def createChannelSpecification(
    channel_type: str,
    name_in_nextflow: Union[None, str] = None,
    name_in_python: Union[None, str] = None,
    channel_transformation: Union[None, str] = None,
    derive_from_params: bool = False,
    mapNFpy: Union[None, dict] = None,
) -> Tuple[Union[str, tuple], Union[str, tuple], str, bool]:
    """
    Maps arguments of python functions to NextFlow names, to help channel specificatins.

    Parameters
    ----------
    channel_type
        Type of the channel in the NextFlow (var, file, tuple, etc.).
    name_in_nextflow
        Name of the variable to be used in the nextflow script.
    name_in_python
        Naem of the argument used in the python function.
    channel_transformation
        If the nextflow collecting channel should be transformed (Groovy).
    derive_from_params
        If the channel derives form a parameter in the config file.
    mapNFpy
        If the NF variable is aof tuple type, it might be more convenient to add a mapping as a dictionary.

    Returns
    -------
    A tuple, used in channel specifications with channel_type, name_in_nextflow, name_in_python, channel_transformation, derive_from_params.
    """

    if mapNFpy is not None:
        name_in_nextflow, name_in_python = [], []
        for k, v in mapNFpy.items():
            name_in_nextflow.append(k)
            name_in_python.append(v)
        name_in_nextflow, name_in_python = (
            tuple(name_in_nextflow),
            tuple(name_in_python),
        )

    return (
        channel_type,
        name_in_nextflow,
        name_in_python,
        channel_transformation,
        derive_from_params,
    )


def checkNodeReplacements(
    nodes: Union[None, list],
    default_nodes: Union[None, dict],
    replacement_nodes: Union[None, dict],
) -> list:
    """
    Checks a list of initialized process node objects against a dictionary of custom
    nodes and replaces the predefined ones with th user supplied nodes. Best used to
    replace only some nodes in a predefined pipeline.

    Parameters
    ----------
    nodes
        Objects that define processes as nodes linked by Nextflow. If None is supplied,
        the pipeline will consist of the nodes defined here.
    replacement_nodes
        A predefined pipeline in the form of initialized process node objects.
    replacement_nodes
        Custom process nodes that should be used instead of predefined ones with the same
        name (dictionary with [name_in_default_list]:[custom node] key: value pairs).

    Returns
    -------
    List of initialized process objects.
    """

    if nodes is None:
        if replacement_nodes is None:
            replacement_nodes = dict()
        final_nodes = []
        for node in default_nodes:
            object_name = node.__class__.__name__
            if object_name in replacement_nodes:
                final_nodes.append(replacement_nodes[object_name])
            else:
                final_nodes.append(node)
        return final_nodes
    else:
        return nodes


def nonCondaCopy(
    git_packages: list,
    inhouse_packages: list,
    dr: str,
) -> None:
    """
    Inhouse (developmental) packages that are not yet available via Conda will be
    copied to `pipeline/packages` or something similar to be available for scripts.

    Parameters
    ----------
    git_packages
        Developmental packages available via GitHub.
    inhouse_packages
        Not (yet) public packages.
    dr
        The directory where to copy packages.

    Returns
    -------
    List of initialized process objects.
    """

    # TODO: Also add a procedure that handles download from GitHub
    for p in inhouse_packages:
        packdir = p.split("/")[-1]
        shutil.copytree(
            p,
            dr + "/" + packdir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".*"),
        )
    return


def cleanup(
    *,
    location: str = os.getcwd(),
    nameblacklist: list = [
        "work",
        "notebook_files",
        "notebook.run.xml",
        "report.run.xml",
    ],
    extensionblacklist: list = [
        ".log",
        ".aux",
        ".toc",
        ".bbl",
        ".bcf",
        ".blg",
        ".tex",
        ".out",
        "pynb",
    ],
    pipeline: bool = True,
) -> str:
    """
    Adds a heading to autogenerated scripts with shebang and import of introSpect.

    Parameters
    ----------
    dr
        The directory where to develompental packages live.

    Returns
    -------
    A heading for scripts (in Nextflow bin).
    """

    locations = [location]
    if pipeline:
        locations.append(location + "/pipeline")
    for location in locations:
        for e in os.listdir(location):
            if e[0] == "." or e in nameblacklist or e[-4:] in extensionblacklist:
                try:
                    os.remove(location + "/" + e)
                except:
                    shutil.rmtree(location + "/" + e)
    return


def init_sge(envlist=None, disable_ansi=True):
    """
    Add env vars needed to submit SGE scripts by Nextflow.

    Parameters
    ----------
    envlist
        The file (typically in the root) containing env vars for SGE.
    disable_ansi
        If ANSI log is not disabled, a new set of status reports are shown for every
        Nextflow task each time they are updated. The output is more concise if disabled.
    """

    if envlist is None:
        envlist = os.path.expanduser("~") + "/.sge_env"
    with open(envlist, "r") as f:
        for line in f:
            a, b = line.split("\n")[0].split("=")
            os.environ[a] = b
    if disable_ansi:
        os.environ["NXF_ANSI_LOG"] = "false"
    return


def run_pipeline(
    pipeline_folder,
    mainfile="main.nf",
    needs_sge_init=True,
    with_timeline=True,
    with_graph=True,
    runprofile="cluster",
    in_background=False,
):
    """
    Run a nextflow pipeline compiled by flowNodes.

    Parameters
    ----------
    pipeline_folder
        Folder containing the main nextflow script.
    mainfile
        The main script is usually called main.nf; set this, if not.
    needs_sge_init
        If SGE-related variables are not saved in the env, initialize it.
    with_timeline
        Register a (html format) timeline.
    with_graph
        Draw a graph representation of the pipeline.
    runprofile
        The name of the profile that should be run. Use ´None´ for local run.
    in_background
        Run pipeline in background.
    """

    crdir = os.getcwd()
    os.chdir(pipeline_folder)
    if needs_sge_init:
        init_sge()
    cmd = ["nextflow", "run", mainfile]
    if with_timeline:
        cmd += ["-with-timeline", "../timeline.html"]
    if with_graph:
        cmd += ["-with-dag", "../pipeline_chart.png"]
    if runprofile is not None:
        cmd += ["-profile", "cluster"]
    if in_background:
        cmd.appemd("-bg")
    # Inspired by https://github.com/fabianlee/blogcode/blob/master/python/runProcessWithLiveOutput.py
    process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
    running = True
    while running:
        msg = process.stdout.readline()
        if process.poll() is not None:
            running = False
        if msg:
            print(msg.strip().decode())
    os.chdir(crdir)
    return
