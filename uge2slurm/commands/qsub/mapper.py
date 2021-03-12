import logging
import os
import pathlib
import getpass
from functools import partialmethod, reduce

from uge2slurm.mapper import CommandMapperBase, bind_to, bind_if_true, not_implemented, not_supported
from uge2slurm.commands import UGE2slurmCommandError

from .squeue import get_running_jobs

logger = logging.getLogger()


class CommandMapper(CommandMapperBase):
    _logger = logger
    _DEFAULT_JOB_NAME = "%x.{}%j"
    _MAIL_OPTION_MAPPER = dict(
        b=("BEGIN", ),
        e=("END", ),
        a=("FAIL", "REQUEUE")
    )

    dry_run = False

    def is_array(self):
        return self._args.t is not None

    def _get_default_filename(self, option_string):
        filename = self._DEFAULT_JOB_NAME.format(option_string)
        if self.is_array():
            filename += ".%a"
        return filename

    def _map_path(self, _value, option_name, bind_to, option_string, is_output=True):
        path = _value[0]
        if len(_value) > 1:
            self._logger.warning('setting multiple paths for "{}" option is not '
                                 'supported. use first one: {}'.format(option_name, path))

        if path.startswith(':'):
            path = path.lstrip(':')
        elif ':' in path:
            self._logger.warning('"hostname" specification in "{}" option is not supported.'.format(option_name))
            path = path.split(':', 1)[1]

        if is_output:
            if os.path.isdir(path):
                filename = self._get_default_filename(option_string)
                path = os.path.join(path, filename)
            elif os.path.isfile(path):
                self._logger.warning('output file specified by "{}" will be overwritten.'.format(option_name))
            else:
                dirname, filename = os.path.split(path)
                if not os.path.exists(dirname):
                    # try:
                    os.makedirs(dirname)

                filename = filename.replace('%', "%%")
                filename = filename.replace("$USER", "%u")
                filename = filename.replace("$JOB_ID", "%j")
                filename = filename.replace("$JOB_NAME", "%x")
                filename = filename.replace("$HOSTNAME", "%N")
                filename = filename.replace("$TASK_ID", "%a")

                path = os.path.join(dirname, filename)

        self.args += [bind_to, path]

    @staticmethod
    def _make_dict_from_kv(values):
        d = {}
        for kv in values:
            kv = kv.split('=', 1)
            k = kv[0]
            v = None if len(kv) == 1 else kv[1]
            d[k] = v
        return d

    _optionfile = not_implemented("-@")

    def a(self, datetime):
        self.args += ["--begin", datetime.isoformat()]

    ac = not_supported("-ac")
    adds = not_implemented("-adds")
    ar = bind_to("--reservation")
    A = bind_to("--account")
    binding = not_implemented("-binding")

    def b(self, value):
        # TODO: use `--wrap` option?
        pass

    c = not_supported("-c")
    ckpt = not_supported("-ckpt")
    clear = not_implemented("-clear")
    clearp = not_implemented("-clearp")
    clears = not_implemented("-clears")

    def cwd(self, value):
        if value is not True:
            return
        self.args += ["--chdir", os.getcwd()]

    # C
    dc = not_supported("-dc")

    def dl(self, datetime):
        self.args += ["--deadline", datetime.isoformat()]

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

    def l(self, value):
        # TODO: map resource request

        # get hard/soft confs (None and "hard" are merged at `self.pre_convert`)
        hard_resources = self._make_dict_from_kv(value[None])
        soft_resources = self._make_dict_from_kv(value["soft"])

        #
        for memkey in self._args.memory:
            if memkey in hard_resources:
                self.args += ["--mem-per-cpu", hard_resources[memkey]]
                break

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
            self.args += ["--mail-type", ','.join(mailtypes)]

    def M(self, _value):
        user = _value[0]
        if len(_value) > 1:
            self._logger.warning('setting multiple paths for "-M" option is not '
                                 'supported. use first one: {}'.format(user))
        self.args += ["--mail-user", user]

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
        # TODO: map resource request

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
                    self.args += ["--cpus-per-task", pe[0][0]]
                    available_pe = None
                    break

        if available_pe is not None:
            min_pe = pe[0][0]
            if min_pe == 0:
                min_pe = 1
            self._logger.warning("Range value for `-pe` is not supported. Use minimum value: {}".format(min_pe))
            self.args += ["--cpus-per-task", min_pe]

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
            self.args += ["--nodelist", ','.join(hosts)]

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
        # TODO: change shell
        pass

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

    def __init__(self, bin):
        super().__init__(bin)

        #
        self.dest2converter['@'] = self._optionfile

        #
        self.env_vars = {}

    def pre_convert(self):
        if self._args.j is True:
            setattr(self._args, 'e', None)

        for d in (self._args.l, self._args.q):
            self._merge_hard_env(d)

    @staticmethod
    def _merge_hard_env(d):
        if d is not None and None in d and "hard" in d:
            d["None"].update(**d["hard"])

    def post_convert(self):
        self._map_dependency()
        self._prepare_output_path()
        self._map_array()

        self._convert_envvars()
        self._map_environ_vars()

        self.args += self._args.command

    def _map_dependency(self):
        dependencies = set()
        for ids in (self._args.hold_jid, self._args.hold_jid_ad):
            if ids is not None:
                dependencies |= set(jobid for jobid in ids if not jobid.isdigit())

        if not dependencies:
            return

        try:
            name2jobid = get_running_jobs()
        except UGE2slurmCommandError:
            if self.dry_run:
                return
            else:
                raise
        running_jids = reduce(lambda a, b: a.update(b), name2jobid.values())

        nonarray_dependencies = []
        array_dependencies = []
        for container, jids in zip((nonarray_dependencies, array_dependencies),
                                   (self._args.hold_jid, self._args.hold_jid_ad)):
            if jids is not None:
                for jobid in jids:
                    if jobid in running_jids:
                        container.append(jobid)
                    elif jobid in name2jobid:
                        container += [i for i in jobid[name2jobid]]
                    else:
                        self._logger.info('Job "{}" is not running.'.format(jobid))

        dependencies = []
        if nonarray_dependencies:
            dependencies.append("afterok:" + ':'.join(nonarray_dependencies))
        if array_dependencies:
            dependencies.append("aftercorr:" + ':'.join(array_dependencies))

        if dependencies:
            self.args += ["--dependency", ','.join(dependencies)]

    def _prepare_output_path(self):
        if self._args.o is None:
            filename = self._get_default_filename('o')
            self.args += ["--output", filename]

        if self._args.j is not True and self._args.e is None:
            filename = self._get_default_filename('e')
            self.args += ["--error", filename]

    def _map_array(self):
        if not self.is_array():
            return

        array = self._args.t
        if self._args.tc:
            array += '%' + self._args.tc

        self.args += ["--array", array]

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

    @staticmethod
    def _get_home():
        return str(pathlib.Path.home())

    @staticmethod
    def _get_hostname():
        return os.uname().nodename

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
        return self._args.command[0]

    def _get_jobname(self):
        if self._args.N:
            return self._args.N
        else:
            return os.path.basename(self._get_jobscript)

    def _map_environ_vars(self):
        export = []
        if self._args.V is True:
            export.append("ALL")

        if self._args.v:
            export += self._args.v

        for k, v in self.env_vars.items():
            export.append("{}={}".format(k, v))

        if not export:
            export.append("NONE")

        self.args += ["--export", ','.join(export)]
