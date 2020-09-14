import os
from dateutil.parser import parse as dparse
import re
from datetime import datetime, timedelta
from jinja2 import Template,Environment,FileSystemLoader

class Test:
    PASS = 0
    NOTRUN = 1
    FAIL = 2

    def __init__(self, name):
        self.name = name
        self.passes = []
        self.fails = []
        self.notruns = []
        self.times = []

    def add_result(self, run, status):
        if status == self.PASS:
            self.passes.append(run)
        elif status == self.NOTRUN:
            self.notruns.append(run)
        elif status == self.FAIL:
            self.fails.append(run)
        else:
            raise Exception("Invalid test status")

    def sort_results(self):
        self.passes = sorted(self.passes, key=lambda r: r.date)
        self.notruns = sorted(self.notruns, key=lambda r: r.date)
        self.fails = sorted(self.fails, key=lambda r: r.date)

    def __repr__(self):
        return 'name={} passes={} notruns={} fails={}'.format(self.name,
                len(self.passes), len(self.notruns), len(self.fails))

class TestRun:
    def __init__(self, path, username, hostname, config, date):
        self.dir = path
        self.username = username
        self.hostname = hostname
        self.config = config
        self.datestr = date
        self.date = dparse(date)
        self.passes = []
        self.fails = []
        self.notruns = []

    def __repr__(self):
        return 'path={} username={} hostname={} date={}'.format(self.dir,
                self.username, self.hostname, self.date)

    def recent(self):
        delta = datetime.now() - self.date
        return delta.days <= 7

    def add_result(self, test, status):
        if status == Test.PASS:
            self.passes.append(test)
        elif status == Test.NOTRUN:
            self.notruns.append(test)
        elif status == Test.FAIL:
            self.fails.append(test)
        else:
            raise Exception("Invalid test status")

    def _rel_path(self):
        return '/'.join(self.dir.split('/')[-5:])

    def link_path(self):
        return "/" + self._rel_path() + "/index.html"

    def total_run(self):
        return len(self.fails) + len(self.notruns) + len(self.passes)

    def bad_output(self, testname):
        if os.path.exists(self.dir + "/{}.out.bad.html".format(testname)):
            return True
        return False

    def dmesg_output(self, testname):
        if os.path.exists(self.dir + "/{}.dmesg.html".format(testname)):
            return True
        return False

def parse_check_log(run, tests):
    ran = []
    failed = []
    notrun = []
    with open(run.dir + "/check.log") as fp:
        for line in fp:
            v = line.split(' ')
            if v[0] == "Ran:":
                ran = v[1:]
            elif v[0] == "Not":
                notrun = v[2:]
            elif v[0] == "Failures:":
                failed = v[1:]
    for i in ran:
        k = i.rstrip()
        if k not in tests:
            tests[k] = Test(k)
        if i in failed:
            tests[k].add_result(run, Test.FAIL)
            run.add_result(tests[k], Test.FAIL)
        elif i in notrun:
            tests[k].add_result(run, Test.NOTRUN)
            run.add_result(tests[k], Test.NOTRUN)
        else:
            tests[k].add_result(run, Test.PASS)
            run.add_result(tests[k], Test.PASS)

def parse_check_time(filename):
    ret = {}
    with open(filename) as fp:
        for line in fp:
            v = line.split(' ')
            ret[v[0].rstrip()] = int(v[1])
    return ret

env = Environment(loader=FileSystemLoader('.'))
index_template = env.get_template('template.jinja')
run_template = env.get_template('testrun-template.jinja')
test_template = env.get_template('test-template.jinja')

runs = []
for (dirpath, subdirs, filenames) in os.walk(os.environ['RESULTS_DIR']):
    if "check.log" in filenames:
        vals = dirpath.split('/')
        runs.append(TestRun(dirpath, vals[-4], vals[-3], vals[-2], vals[-1]))

runs = sorted(runs, key=lambda r: r.date)
tests = {}
for r in runs:
    times = parse_check_time(r.dir + "/check.time")
    r.times = times
    parse_check_log(r, tests)
    f = open(r.dir + "/index.html", "w")
    f.write(run_template.render(run=r))
    f.close()

fails = []
passes = []
for k,v in tests.items():
    v.sort_results()
    if len(v.fails):
        fails.append(v)
    elif len(v.passes):
        passes.append(v)

    test_runs = v.passes + v.fails
    test_runs = sorted(test_runs, key=lambda r: r.date)

    try:
        os.mkdir(os.environ["RESULTS_DIR"] + "/" + os.path.dirname(k))
    except FileExistsError:
        pass

    f = open(os.environ["RESULTS_DIR"] + "/" + k + ".html", "w")
    f.write(test_template.render(test=v, runs=test_runs))
    f.close()

f = open(os.environ["RESULTS_DIR"] + "/index.html", "w")
f.write(index_template.render(fails=fails, passes=passes, runs=runs))
f.close()
