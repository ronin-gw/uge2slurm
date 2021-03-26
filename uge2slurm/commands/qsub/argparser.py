import argparse
from collections import defaultdict

from uge2slurm.commands.argparser import set_common_args, parse_ge_datetime
from uge2slurm.utils.py2.argparse import HelpFormatter

parser_args = dict(
    description="Mapping UGE qsub command to slurm",
    add_help=False,
    formatter_class=HelpFormatter
)


class singlearg(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs != 1:
            raise ValueError("`nargs` must be 1 for this action")
        super(singlearg, self).__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string):
        setattr(namespace, self.dest, values[0])


class appendkv(argparse.Action):
    @staticmethod
    def flatten(values):
        return values[0].split(',')

    def __call__(self, parser, namespace, values, option_string):
        kvs = self.flatten(values)

        container = getattr(namespace, self.dest)
        if container is None:
            setattr(namespace, self.dest, kvs)
        else:
            container += kvs


class appendsingle(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        container = getattr(namespace, self.dest)
        if container is None:
            setattr(namespace, self.dest, values)
        else:
            container.append(values[0])


class nargs1or2(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        if not 1 <= len(values) <= 2:
            parser.error(
                'argument {}: expected 1 or 2 arguments'.format(self.dest)
            )
        setattr(namespace, self.dest, values)


class set_resource_state(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        parser.resouce_state = self.dest


class appendresource(appendkv):
    def __call__(self, parser, namespace, values, option_string):
        resource_state = getattr(parser, "resouce_state", None)

        container = getattr(namespace, self.dest)
        if container is None:
            setattr(namespace, self.dest, defaultdict(list))
            container = getattr(namespace, self.dest)

        container[resource_state] += self.flatten(values)


class store_bool(singlearg):
    def __call__(self, parser, namespace, values, option_string):
        value = values[0]
        if value.startswith(('Y', 'y')):
            setattr(namespace, self.dest, True)
        elif value.startswith(('N', 'n')):
            setattr(namespace, self.dest, False)
        else:
            parser.error(
                'Unknown argument passed: "{}" (expect y[es] or n[o])'.format(value)
            )


def _set_parser(parser):
    set_orig_argsuments(parser)

    uge = parser.add_argument_group(
        title="qsub options",
        description="UGE qsub options"
    )
    set_qsub_arguments(uge)


def set_orig_argsuments(parser):
    set_common_args(parser)
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Preview converted slurm command")
    parser.add_argument(
        "--memory", nargs='*', default=["mem_req", "s_vmem"], metavar="resource",
        help="Specify which resource value should be mapped into `--mem-per-cpu` "
             "option. If multiple values are specified, the first valid value "
             "will be used."
    )
    parser.add_argument(
        "--cpus", nargs='*', default=["def_slot"], metavar="parallel_env",
        help="Specify which parallel_environment should be mapped into "
             "`--cpus-per-task` option. If multiple values are specified, the "
             "first valid value will be used. Note that range values are not "
             "supported and its minimum value will be used as the number of cpus."
    )
    parser.add_argument(
        "--partition", nargs='*', metavar="resource=partition", default=[],
        help="Specify which resource name should be mapped into partition "
             "(queue) via `--partition` option. Resource-partition pairs must be "
             "specified by '=' separated strings."
    )


def set_qsub_arguments(uge):
    uge.add_argument("-@", nargs=1, action=singlearg, metavar="optionfile")
    uge.add_argument("-a", nargs=1, action=singlearg, metavar="date_time", type=parse_ge_datetime)
    uge.add_argument("-ac", nargs=1, action=appendkv, metavar="variable[=value],...")
    uge.add_argument("-adds", nargs=3, action="append", metavar="parameter key value")
    uge.add_argument("-ar", nargs=1, action=singlearg, metavar="ar_id")
    uge.add_argument("-A", nargs=1, action=singlearg, metavar="account_string")
    uge.add_argument("-bgio", nargs=1, action=appendkv, metavar="bgio_params")
    uge.add_argument("-binding", nargs='+', action=nargs1or2)
    uge.add_argument("-b", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-c", nargs=1, action=singlearg, metavar="occasion_specifier")
    uge.add_argument("-ckpt", nargs=1, action=singlearg, metavar="ckpt_name")
    uge.add_argument("-clear", action="store_true", default=None)
    uge.add_argument("-clearp", nargs=1, action=appendsingle, metavar="parameter")
    uge.add_argument("-clears", nargs=2, action="append", metavar="parameter")
    uge.add_argument("-cwd", action="store_true", default=None)
    uge.add_argument("-C", nargs=1, action=singlearg, metavar="prefix_string")
    uge.add_argument("-dc", nargs=1, action=appendkv, metavar="variable,...")
    uge.add_argument("-dl", nargs=1, action=singlearg, metavar="date_time", type=parse_ge_datetime)
    uge.add_argument("-e", nargs=1, action=appendkv, metavar="[[hostname]:]file,...")
    uge.add_argument("-hard", nargs=0, action=set_resource_state)
    uge.add_argument("-h", action="store_true", default=None)
    uge.add_argument("-help", action="store_true", default=None)
    uge.add_argument("-hold_jid", nargs=1, action=appendkv, metavar="wc_job_list")
    uge.add_argument("-hold_jid_ad", nargs=1, action=appendkv, metavar="wc_job_list")
    uge.add_argument("-i", nargs=1, action=appendkv, metavar="[[hostname]:]file,...")
    uge.add_argument("-j", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-jc", nargs=1, action=singlearg, metavar="jc_name")
    uge.add_argument("-js", nargs=1, action=singlearg, metavar="job_share")
    uge.add_argument("-jsv", nargs=1, action=singlearg, metavar="jsv_url")
    uge.add_argument("-masterl", nargs=1, action=appendkv, metavar="resource=value,...")
    uge.add_argument("-l", nargs=1, action=appendresource, metavar="resource=value,...")
    uge.add_argument("-m", nargs=1, action=appendkv, metavar="b|e|a|s|n,...")
    uge.add_argument("-masterq", nargs=1, action=appendkv, metavar="wc_queue_list")
    uge.add_argument("-mods", nargs=3, action="append", metavar="param")
    uge.add_argument("-mbind", nargs=1, action=singlearg, metavar="param")
    uge.add_argument("-notify", action="store_true", default=None)
    uge.add_argument("-now", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-N", nargs=1, action=singlearg, metavar="name")
    uge.add_argument("-o", nargs=1, action=appendkv, metavar="[[hostname]:]path,...")
    uge.add_argument("-P", nargs=1, action=singlearg, metavar="project_name")
    uge.add_argument("-p", nargs=1, action=singlearg, metavar="priority")
    uge.add_argument("-par", nargs=1, action=singlearg, metavar="allocation_rule")
    uge.add_argument("-pe", nargs=2, action="append", metavar="parallel_environment")
    uge.add_argument("-pty", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-q", nargs=1, action=appendresource, metavar="qc_queue_list")
    uge.add_argument("-R", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-r", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-row", nargs=1, action=appendkv, metavar="variable,...")
    uge.add_argument("-rdi", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-sc", nargs=1, action=appendkv, metavar="variable[=value],...")
    uge.add_argument("-shell", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-si", nargs=1, action=singlearg, metavar="session_id")
    uge.add_argument("-soft", nargs=0, action=set_resource_state)
    uge.add_argument("-sync", nargs=1, action=singlearg, metavar="y|n|l|r")
    uge.add_argument("-S", nargs=1, action=appendkv, metavar="[[hostname]:]pathname,...")
    uge.add_argument("-t", nargs=1, action=singlearg, metavar="n[-m[:s]]")
    uge.add_argument("-tc", nargs=1, action=singlearg, metavar="max_running_tasks")
    uge.add_argument("-tcon", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("-terse", action="store_true", default=None)
    uge.add_argument("-umask", nargs=1, action=singlearg, metavar="parameter")
    uge.add_argument("-v", nargs=1, action=appendkv, metavar="variable[=value],...")
    uge.add_argument("-verify", action="store_true", default=None)
    uge.add_argument("-V", action="store_true", default=None)
    uge.add_argument("-w", nargs=1, action=singlearg, metavar="e|w|n|p|v")
    uge.add_argument("-wd", nargs=1, action=singlearg, metavar="working_dir")
    uge.add_argument("-xdv", nargs=1, action=singlearg, metavar="docker_volume")
    uge.add_argument("-xd_run_as_image_user", nargs=1, action=store_bool, metavar="y[es]|n[o]")
    uge.add_argument("command", nargs=argparse.REMAINDER)


def get_parser(parser=None):
    if not parser:
        parser = argparse.ArgumentParser(**parser_args)
    _set_parser(parser)
    return parser
