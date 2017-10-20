# coding: utf-8

from fabric.api import run, env, roles, cd

env.parallel = True
env.use_ssh_config = True

env.roledefs = {
    "spiders": ["node2", "a1", "a2"],
    "app": ["node2"],
    "test": ["node2"],
}


COMMANDS = {"start", "stop", "restart", "status"}


@roles("spiders")
def pull():
    """pull spider code to all hosts"""
    with cd("~/github/Spiders"):
        run("git pull")


@roles("spiders")
def command(cmd):
    """部署 spiders 的机器在 shell 执行命令, cmd: str, shell 要执行的指令"""
    run(cmd)


def _supervisor_pipeline(pipeline, command):
    project = pipeline + ":*"
    run("supervisorctl %s %s" % (command, project))


@roles("spiders")
def spider(cmd, name):
    """通过 supervisorctl 命令管理该任务, cmd:start, stop, restart, status; name:long, middle, short, all"""
    _names = ["long", "middle", "short", "all"]
    assert cmd in COMMANDS
    assert name in _names
    if name == "all":
        names = ["spider-"+name for name in _names[:3]]
    else:
        names = ["spider-" + name]
    for name in names:
        _supervisor_pipeline(name, cmd)


@roles("app")
def app(cmd, name):
    """通过 supervisorctl 命令管理该任务, cmd:start, stop, restart, status; name: service, weibo, weixin"""
    names = ["service", "weibo", "weixin"]
    assert cmd in COMMANDS
    assert name in names
    name = "app-" + name
    _supervisor_pipeline(name, cmd)


@roles("test")
def test(cmd):
    """通过 supervisorctl 命令管理该任务, cmd:start, stop, restart, status;"""
    assert cmd in COMMANDS
    name = "test-service"
    _supervisor_pipeline(name, cmd)
