import logging
import argparse
import os
import getpass
import sys
import shlex
import random
import string
import re
from gettext import gettext
from datetime import datetime
from collections import defaultdict
from functools import reduce
from uge2slurm.utils.py2.functools import partialmethod

from uge2slurm import UGE2slurmError
from uge2slurm.mapper import CommandMapperBase, bind_to, bind_if_true, not_implemented, not_supported, mapmethod
from uge2slurm.commands import UGE2slurmCommandError, WRAPPER_DIR

from .squeue import get_running_jobs
from .sinfo import get_partitions
from .argparser import set_qsub_arguments

logger = logging.getLogger(__name__)


class _ExtraArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs["add_help"] = False
        super(_ExtraArgumentParser, self).__init__(*args, **kwargs)

    def error(self, message):
        args = {'prog': self.prog, 'message': message}
        self.exit(2, self.error_prolog + '\n' + (gettext('%(prog)s: error: %(message)s\n') % args))


class CommandMapper(CommandMapperBase):
    _logger = logger
    _DEFAULT_JOB_NAME = "%x.{}%j"
    _MAIL_OPTION_MAPPER = dict(
        b=("BEGIN", ),
        e=("END", ),
        a=("FAIL", "REQUEUE")
    )
    _HOME = os.path.expanduser('~')

    WRAPPER_PATH = os.path.join(WRAPPER_DIR, "uge2slurm-qsubwrapper.sh")

    dry_run = False

    def is_array(self):
        return self._args.t is not None

    def _get_default_filename(self, option_string):
        filename = self._DEFAULT_JOB_NAME.format(option_string)
        if self.is_array():
            filename += ".%a"
        if self._args.cwd is not True:
            filename = os.path.join(self._HOME, filename)

        return filename

    @classmethod
    def _use_1st_one(cls, value, option_name):
        one = value[0]
        if len(value) > 1:
            cls._logger.warning('setting multiple paths for "{}" option is not '
                                'supported. use first one: {}'.format(option_name, one))
        return one

    @classmethod
    def _remove_host(cls, path, option_name):
        if path.startswith(':'):
            path = path.lstrip(':')
        elif ':' in path:
            cls._logger.warning('"hostname" specification in "{}" option is not supported.'.format(option_name))
            path = path.split(':', 1)[1]
        return path

    def _map_path(self, value, option_name, bind_to, option_string, is_output=True):
        path = self._use_1st_one(value, option_name)
        path = self._remove_host(path, option_name)

        if self._args.cwd is not True and not os.path.isabs(path):
            path = os.path.join(self._HOME, path)

        if is_output:
            if os.path.isdir(path):
                filename = self._get_default_filename(option_string)
                path = os.path.join(path, filename)
            elif os.path.isfile(path):
                self._logger.warning('output file specified by "{}" will be overwritten.'.format(option_name))
            else:
                dirname, filename = os.path.split(path)
                if dirname and not os.path.exists(dirname):
                    self._logger.debug("output log directory does not exist.")
                    if not self.dry_run:
                        try:
                            os.makedirs(dirname)
                        except OSError as e:
                            logger.critical(e)
                            raise UGE2slurmCommandError("failed to create log output directory.")
                        self._logger.info('directory "{}" was created for output.'.format(dirname))

                filename = filename.replace('%', "%%")
                filename = filename.replace("$USER", "%u")
                filename = filename.replace("$JOB_ID", "%j")
                filename = filename.replace("$JOB_NAME", "%x")
                filename = filename.replace("$HOSTNAME", "%N")
                filename = filename.replace("$TASK_ID", "%a")

                path = os.path.join(dirname, filename)

        return [bind_to, path]

    @staticmethod
    def _make_dict_from_kv(values):
        d = {}
        for kv in values:
            kv = kv.split('=', 1)
            k = kv[0]
            v = None if len(kv) == 1 else kv[1]
            d[k] = v
        return d

    # # # option mappings # # #
    _optionfile = not_implemented("-@")

    def a(self, datetime):
        return ["--begin", datetime.isoformat()]

    ac = not_supported("-ac")
    adds = not_implemented("-adds")
    ar = bind_to("--reservation")
    A = bind_to("--account")
    binding = not_implemented("-binding")
    # handle `b` at `run` function in `__init__`
    c = not_supported("-c")
    ckpt = not_supported("-ckpt")
    clear = not_implemented("-clear")
    clearp = not_implemented("-clearp")
    clears = not_implemented("-clears")

    def cwd(self, value):
        if value is not True:
            return
        return ["--chdir", os.getcwd()]

    # C
    dc = not_supported("-dc")

    def dl(self, datetime):
        return ["--deadline", datetime.isoformat()]

    e = partialmethod(_map_path, option_name="-e", bind_to="--error", option_string='e')
    # hard
    h = bind_if_true("--hold")
    # `hold_jid` and `hold_jid_ad` will be solved together
    # hold_jid
    # hold_jid_ad
    i = partialmethod(_map_path, option_name="-i", bind_to="--input", option_string='i', is_output=False)
    # handle `j` at pre_ and post_convert
    # j
    jc = not_supported("-jc")
    js = not_supported("-js")
    jsv = not_supported("-jsv")
    masterl = not_supported("-masterl")

    def l(self, value):  # noqa
        additional_args = []

        # get hard/soft confs (None and "hard" are merged at `self.pre_convert`)
        hard_resources = self._make_dict_from_kv(value[None])
        soft_resources = self._make_dict_from_kv(value["soft"])

        #
        additional_args += self._map_partition(hard_resources, soft_resources)

        #
        for memkey in self._args.memory:
            if memkey in hard_resources:
                additional_args += ["--mem-per-cpu", hard_resources[memkey]]
                break

        return additional_args

    def _map_partition(self, hard_resources, soft_resources):
        #
        try:
            partitions = get_partitions()
        except UGE2slurmCommandError as e:
            if self.dry_run:
                self._logger.warning(e)
                partitions = set()
            else:
                raise e

        #
        resource2part = {}
        for kv in self._args.partition:
            k, v = kv.split('=', 1)
            resource2part[k] = v

        prefix2partition = [
            (p, re.split(r"[!\"#$%&'()*+,./:;<=>?@\[\\\]^`{|}~]", p, maxsplit=1)[0])
            for p in partitions
        ]

        def _map_resource_to_partition(resource_name):
            #
            if resource_name in resource2part:
                return resource2part[resource_name]

            # Split by punctuation charas exclude [-_] then try complete match.
            hits = []
            for partition, prefix in prefix2partition:
                if resource_name == prefix:
                    hits.append(partition)
            if not hits:
                # Try forward-matching
                for partition in partitions:
                    if partition.startswith(resource_name):
                        hits.append(partition)

            if len(hits) > 1:
                self._logger.error('Resource specification "{}" matches multiple partitions.'.format(resource_name))
                self._logger.warning("\t{} -> ".format(resource_name) + ", ".join(hits))
                self._logger.warning("Try to add implicit mapping option like `--partition {}={}`.".format(
                    resource_name, hits[0]
                ))
                raise UGE2slurmCommandError("failed to map resource into partition.")
            elif hits:
                self._logger.debug("partition mapping: {} -> {}".format(resource_name, hits[0]))
                return hits[0]
            else:
                return None

        #
        specified_part = []
        for resource_name in hard_resources:
            candidate = _map_resource_to_partition(resource_name)
            if candidate:
                specified_part.append((resource_name, candidate))

        candidates = set(partition for _, partition in specified_part)
        if len(candidates) > 1:
            self._logger.error("Hard resource specifications match multiple partitions.")
            for resource_name, partition in specified_part:
                self._logger.warning("\t{} -> {}".fprmat(resource_name, partition))
            self._logger.warning('Try to specify single resource or use `-soft` '
                                 'to give "as available" resource list.')
            raise UGE2slurmCommandError("failed to map resource into partition.")
        elif candidates:
            partition = candidates.pop()
            self._logger.info("set partition by hard resource {} -> {}".format(
                ", ".join(resource_name for resource_name, _ in specified_part),
                partition
            ))
            return ["--partition", partition]

        #
        partition2resource_names = defaultdict(list)
        for resource_name in soft_resources:
            candidate = _map_resource_to_partition(resource_name)
            if candidate:
                partition2resource_names[candidate].append(resource_name)

        if partition2resource_names:
            self._logger.info("set partition by soft resource")
            for partition, resource_names in specified_part:
                self._logger.info("\t{} -> {}".format(
                    ", ".join(resource_names),
                    partition
                ))
            return ["--partition", ','.join(p for p in partition2resource_names)]

        return []

    def m(self, value):
        mailtypes = []
        for option in value:
            if option == 'n':
                pass
            if option in self._MAIL_OPTION_MAPPER:
                mailtypes += [t for t in self._MAIL_OPTION_MAPPER[option]]
            else:
                self._logger.warning('Unknown mail type "{}" for "{}" was ignored.'.format(
                    option, "-m"
                ))

        if mailtypes:
            return ["--mail-type", ','.join(mailtypes)]

    def M(self, value):
        user = self._use_1st_one(value, "-M")
        return ["--mail-user", user]

    masterq = not_supported("-masterq")
    mods = not_implemented("-mods")
    mbind = not_implemented("-mbind")
    notify = not_implemented("-notify")  # use `--signal`?
    now = not_implemented("-now")
    N = bind_to("--job-name")
    o = partialmethod(_map_path, option_name="-o", bind_to="--output", option_string='o')
    ot = not_implemented("-ot")
    P = bind_to("--wckey")
    p = bind_to("--nice")
    par = not_implemented("-par")

    def pe(self, value):
        additional_args = []

        #
        parallel_env = {}
        for k, v in value:
            ranges = tuple(sorted(
                tuple((int(i) if i != '' else 0) for i in range.split('-'))
                for range in v.split(',')
            ))
            parallel_env[k] = ranges

        #
        available_pe = None
        for pe_name in self._args.cpus:
            if pe_name in parallel_env:
                if available_pe is None:
                    pe = available_pe = parallel_env[pe_name]
                else:
                    pe = parallel_env[pe_name]
                if len(pe) == 1 and len(pe[0]) == 1:
                    additional_args += ["--cpus-per-task", pe[0][0]]
                    available_pe = None
                    break

        if available_pe is not None:
            min_pe = pe[0][0]
            if min_pe == 0:
                min_pe = 1
            self._logger.warning("Range value for `-pe` is not supported. Use minimum value: {}".format(min_pe))
            additional_args += ["--cpus-per-task", min_pe]

        return additional_args

    pty = not_implemented("-pty")

    def q(self, value):
        hosts = []
        for queue in value:
            text = queue.split('@', 1)
            if len(text) == 1 or text[1].startswith('@'):
                self._logger.error('Queue specification at "-q" option requires host name: ' + queue)
            else:
                hosts.append(text[1])
        if hosts:
            return ["--nodelist", ','.join(hosts)]

    R = not_implemented("-R")

    def r(self, value):
        if value is True:
            self.args.append("--requeue")
        elif value is False:
            self.args.append("--no-requeue")

    rou = not_implemented("-rou")  # map to `--profile`
    rdi = not_supported("-rdi")
    sc = not_supported("-sc")
    shell = not_implemented("-shell")
    si = not_supported("-si")
    # soft
    sync = not_implemented("-sync")  # TODO: use `--wait`

    def S(self, value):
        path = self._use_1st_one(value, "-S")
        path = self._remove_host(path, "-S")
        setattr(self._args, 'S', path)

    # `t` and `tc` will be processed together
    # t
    # tc
    tcon = not_supported("-tcon")
    terse = bind_if_true("--parsable")
    umask = not_supported("-umask")
    # v: processed at post_convert
    verify = bind_if_true("--test-only")
    # V: processed at post_convert
    w = not_supported("-w")
    wd = bind_to("--chdir")
    xd = not_supported("-xd")
    xdv = not_supported("-xdv")
    xd_run_as_image_user = not_supported("-xd_run_as_image_user")

    # # # functions # # #
    def __init__(self, bin, dry_run=False):
        self.dry_run = dry_run
        super(CommandMapper, self).__init__(bin)

        #
        self.dest2converter['@'] = self._optionfile

        #
        self.env_vars = {}
        self.script = None
        self.jobscript_path = None

    # # # pre-convert processing # # #
    def pre_convert(self):
        #
        self._load_script()

        #
        if self._args.j is True:
            if self._args.e is not None:
                self._logger.warning("`-e` is ignored due to `-j` is enabled.")
            setattr(self._args, 'e', None)

        for d in (self._args.l, self._args.q):
            self._merge_hard_env(d)

    def _load_script(self):
        temp_script_required = False  # if `-b` was specified or script was input via stdin

        if not self._args.command:  # input script was read from stdin
            if self._args.b:
                raise UGE2slurmCommandError("command required for a binary job")
            self.script = self._read_stdin()
            if not self.script:
                raise UGE2slurmCommandError("no input read from stdin")

            temp_script_required = True
            if self._args.N is None:
                setattr(self._args, 'N', "STDIN")
        else:
            self.jobscript_path = self._args.command[0]
            if not self._args.b:
                try:
                    with open(self._args.command[0]) as f:
                        self.script = f.read()
                except OSError as e:
                    self._logger.error('Failed to open script "{}"'.format(self._args.command[0]))
                    raise UGE2slurmCommandError(str(e))
            else:
                self.script = ' '.join(self._args.command)
                temp_script_required = True
                if self._args.N is None:
                    setattr(self._args, 'N', self.jobscript_path)

        if temp_script_required:
            temp_script_path = self._write_script()
            self._logger.warning('Write temporary script to "{}"'.format(temp_script_path))
            self.jobscript_path = temp_script_path
            setattr(self._args, "command", [])

        if self.script:
            self._load_extra_args()

    @staticmethod
    def _read_stdin():
        if sys.stdin.isatty():
            return
        return sys.stdin.read()

    def _write_script(self):
        prefix = os.path.join(self._HOME, "uge2slurm-")
        now = None
        population = string.ascii_letters + string.digits

        while True:
            _now = datetime.now()
            if now is None or now.second != _now.second:
                now = _now
                path = prefix + now.strftime("%Y%m%d%H%M%S")
            else:
                path = prefix + now.strftime("%Y%m%d%H%M%S") + '-' + ''.join(
                    random.choice(population) for _ in range(3)
                )
            if os.path.isfile(path):
                continue
            with open(path, 'w') as f:
                f.write(self.script)
            return path

    def _load_extra_args(self):
        prefix_string = "#$" if self._args.C is None else self._args.C
        if not prefix_string:
            return

        args_in_script = []
        for line in self.script.split('\n'):
            if line.startswith(prefix_string):
                args_in_script.append(line[2:].strip())
        args_in_script = ' '.join(args_in_script)

        parser = _ExtraArgumentParser()
        parser.error_prolog = "Invalid argument in the script"
        set_qsub_arguments(parser)
        extra_args = parser.parse_args(shlex.split(args_in_script))

        for dest, value in vars(extra_args).items():
            if getattr(self._args, dest) is None:
                setattr(self._args, dest, value)

    @staticmethod
    def _merge_hard_env(d):
        if d is not None and None in d and "hard" in d:
            d["None"].update(**d["hard"])

    # # # post-convert processing # # #
    def post_convert(self):
        self._map_dependency()
        self._prepare_output_path()
        self._map_array()

        self._convert_envvars()
        self._map_environ_vars()

        self._set_wrapper()
        self._set_interpreter()
        self._set_script()

    @mapmethod("hold_jid", "hold_jid_ad")
    def _map_dependency(self, hold_jid, hold_jid_ad):
        dependencies = set()
        for ids in (hold_jid, hold_jid_ad):
            if ids is not None:
                dependencies |= set(jobid for jobid in ids if not jobid.isdigit())

        if not dependencies:
            return

        try:
            name2jobid = get_running_jobs()
        except UGE2slurmCommandError as e:
            if self.dry_run:
                self._logger.warning(e)
                return
            else:
                raise
        running_jids = reduce(lambda a, b: a | b, name2jobid.values(), set())

        nonarray_dependencies = []
        array_dependencies = []
        for container, jids in zip((nonarray_dependencies, array_dependencies),
                                   (hold_jid, hold_jid_ad)):
            if jids is not None:
                for jobid in jids:
                    if jobid in running_jids:
                        container.append(jobid)
                    elif jobid in name2jobid:
                        ds = [str(i) for i in name2jobid[jobid]]
                        self._logger.debug("dependency: {} -> {}".format(jobid, ', '.join(ds)))
                        container += ds
                    else:
                        self._logger.info('Job "{}" is not running.'.format(jobid))

        dependencies = []
        if nonarray_dependencies:
            dependencies.append("afterok:" + ':'.join(nonarray_dependencies))
        if array_dependencies:
            dependencies.append("aftercorr:" + ':'.join(array_dependencies))

        if dependencies:
            return ["--dependency", ','.join(dependencies)]

    @mapmethod('o', 'e', 'j')
    def _prepare_output_path(self, o, e, j):
        additional_args = []

        if o is None:
            filename = self._get_default_filename('o')
            additional_args += ["--output", filename]

        if j is not True and e is None:
            filename = self._get_default_filename('e')
            additional_args += ["--error", filename]

        return additional_args

    @mapmethod('t', "tc")
    def _map_array(self, t, tc):
        if not self.is_array():
            return

        array = t
        if tc:
            array += '%' + tc

        return ["--array", array]

    def _convert_envvars(self):
        envname2solver = {
            "SGE_O_HOME": self._get_home,
            "SGE_O_HOST": self._get_hostname,
            "SGE_O_LOGNAME": self._get_username,
            "SGE_O_MAIL": self._get_mail,
            "SGE_O_PATH": self._get_path,
            "SGE_O_SHELL": self._get_shell,
            "SGE_O_WORKDIR": self._get_workdir,
            "ENVIRONMENT": self._get_environment,
            "HOME": self._get_home,
            "JOB_SCRIPT": self._get_jobscript,
            "LOGNAME": self._get_username,
            "REQUEST": self._get_jobname,
            "USER": self._get_username
        }

        for envname, solver in envname2solver.items():
            val = solver()
            if val is not None:
                self.env_vars[envname] = val

    @classmethod
    def _get_home(cls):
        return str(cls._HOME)

    @staticmethod
    def _get_hostname():
        return os.uname()[1]  # nodename

    @staticmethod
    def _get_username():
        return getpass.getuser()

    @staticmethod
    def _get_mail():
        return os.environ.get("MAIL", None)

    @staticmethod
    def _get_path():
        return os.environ.get("PATH", None)

    @staticmethod
    def _get_shell():
        return os.environ.get("SHELL", None)

    @staticmethod
    def _get_workdir():
        return os.getcwd()

    @staticmethod
    def _get_environment():
        return "BATCH"

    def _get_jobscript(self):
        return self.jobscript_path

    def _get_jobname(self):
        if self._args.N:
            return self._args.N
        else:
            return os.path.basename(self._get_jobscript())

    @mapmethod('v', 'V')
    def _map_environ_vars(self, v, V):
        export = []
        if V is True:
            export.append("ALL")

        if v:
            export += v

        for _k, _v in self.env_vars.items():
            export.append("{}={}".format(_k, _v))

        if not export:
            export.append("NONE")

        return ["--export", ','.join(export)]

    def _set_wrapper(self):
        if not os.path.exists(self.WRAPPER_PATH):
            raise UGE2slurmError('"uge2slurm-wrapper" is not found. Make sure uge2slurm '
                                 'has been installed correctly and "uge2slurm-wrapper" '
                                 'exists in your path.')
        self.args.append(self.WRAPPER_PATH)

    @mapmethod('b', 'S')
    def _set_interpreter(self, b, S):
        if b:
            return ["/bin/sh"]

        additional_args = []
        interpreter = S
        if interpreter is not None:
            self.args.append(interpreter)
        else:
            self._logger.warning("interpreter for given script is not specified by `-S` option.")
            shebang = self._catch_shebang()
            if shebang is not None:
                additional_args += shebang
            else:
                self._logger.warning("use `/bin/sh` anyway.")
                additional_args.append("/bin/sh")

        return additional_args

    def _catch_shebang(self):
        head = self.script.split('\n')[0]
        if head.startswith('#!'):
            shebang = shlex.split(head[2:])
            if os.path.exists(shebang[0]):
                self._logger.warning("use `{}` as interpreter".format(' '.join(shebang)))
                return shebang

    def _set_script(self):
        if self._args.command:
            self.args += self._args.command
        else:
            self.args.append(self.jobscript_path)
