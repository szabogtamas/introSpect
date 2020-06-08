#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, inspect, textwrap, shutil
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
        flags, positionals = [], {}
        inputs = "\n"
        if self.inputs is None:
            specified_channels = self.channel_specifications()
            if self.cmdpars is not None:
                for k, v in self.cmdpars.items():
                    if k not in self.params:
                        if k in self.cmdpreset:
                            self.params[k] = self.cmdpreset[k]
                        else:
                            self.params[k] = None
            remainder = self.params.copy()
            for k, v in specified_channels.items():
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
                        e = pyVariable[i]
                        if e not in [None, "None"]:
                            remainder.pop(e, None)
                            cd = channelVariables[i]
                            if cd[0] in ["'", '"', "\n"]:
                                if cd[0] == "*":
                                    cd = '"${' + cd[1:] + '}"'
                                else:
                                    cd = cd.replace("'", "")
                                    cd = cd.replace('"', "")
                                    cd = " " + cd
                            else:
                                cd = "$" + cd
                            if e in self.cmdpars:
                                cm = self.cmdpars[e]
                                if cm == "":
                                    positionals[e] = cd
                                else:
                                    flags.append(cm + cd)
                            else:
                                flags.append("--" + e + " $" + cd)
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
            self.flags, self.positionals = flags, positionals
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
                                self.flags.append("--" + e + cd)
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
                self.manualDoc = self.process.__doc__
        else:
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
        command = self.processname + ".py " + " ".join(self.flags) + positionals
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

        if self.container in [None, ""]:
            pass
        else:
            if os.path.isfile(self.container):
                self.process_settings["container"] = self.container
            else:
                if self.container in containers:
                    fn = containers[self.container]
                else:
                    fn = self.container.split(["://"])[1]
                    fn = fn.replace("/", "_")
                    fn = fn.replace(":", "_")
                    fn = dr + "/" + fn + ".sif"
                    subprocess.run(["singularity", "build", fn, self.container])
                    containers[self.container] = fn
                self.container = fn
                self.process_settings["container"] = fn
        return containers

    def generate_py(self, fn, dr):
        dependencies = {
            "conda": "",
            "container": "",
            "imports": [],
            "git_packages": [],
            "inhouse_packages": [],
        }
        dependencies.update(self.dependencies())
        nonCondaCopy(
            dependencies["git_packages"],
            dependencies["inhouse_packages"],
            dr + "/packages",
        )
        recipe = textwrap.dedent(startScriptConneted(dr + "/packages"))
        recipe += "\n" + "\n".join(dependencies["imports"]) + "\n\n"
        recipe += textwrap.dedent(inspect.getsource(self.process).replace("self,", ""))
        recipe += endScriptConneted(self.process.__name__, self.modified_kws)
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


def channelNodes(
    *args,
    location="",
    main_kws=None,
    generalSettings=None,
    containerPaths=None,
    verbose=True
):
    os.makedirs(location + "/bin", exist_ok=True)
    os.makedirs(location + "/packages", exist_ok=True)

    general_cluster_profile = """
    profiles {
        standard {
            process.executor = 'local'
        }
        cluster {
            process.executor = 'sge'
            process.cpus = 1
            process.penv = 'smp'
            process.errorStrategy = 'retry'
            process.clusterOptions = { '-V -S /bin/bash -q all.q@apollo-*' }
        }
    }
    """

    if generalSettings is None:
        generalSettings = """
        singularity {
            enabled = true
            autoMounts = true
        }
        """
    if containerPaths is None:
        containerPaths = dict()

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
            mainparams.append("params." + k + " = " + str(v))
    flowBody = "#!/usr/bin/env nextflow\n\n" + date_helper + "\n\n" + flowBody
    with open(location + "/main.nf", "w") as f:
        f.write(flowBody)
    processSettings = "process {\n"
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
        + textwrap.dedent(general_cluster_profile)
        + processSettings
        + textwrap.dedent(generalSettings)
    )
    with open(location + "/nextflow.config", "w") as f:
        f.write(configBody)
    return


def nonCondaCopy(git_packages, inhouse_packages, dr):
    for p in inhouse_packages:
        packdir = p.split("/")[-1]
        shutil.copytree(
            p,
            dr + "/" + packdir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".*"),
        )
    return


def startScriptConneted(dr):
    connected = (
        """
    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    import sys
    sys.path.append('"""
        + dr
        + """')

    import introSpect
    
    """
    )
    return connected[1:]


def endScriptConneted(f, modified_kws):
    connected = (
        """
    def main():
        mainFunction = introSpect.commandLines.cmdConnect("""
        + f
        + """, """
        + str(modified_kws)
        + """)
        mainFunction.eval()
        mainFunction.save()
        return

    if __name__ == '__main__':
        main()
    """
    )
    return textwrap.dedent(connected)


def cleanup(
    location=os.getcwd(),
    nameblacklist=["work", "notebook_files"],
    extensionblacklist=[
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
    pipeline=True,
):
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
