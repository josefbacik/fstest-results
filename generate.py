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
        self.passes = sorted(self.passes, key=lambda r: r.date, reverse=True)
        self.notruns = sorted(self.notruns, key=lambda r: r.date, reverse=True)
        self.fails = sorted(self.fails, key=lambda r: r.date, reverse=True)

    def regression(self):
        if len(self.fails) == 0:
            return False
        if not self.fails[0].recent():
            return False
        if len(self.passes) == 0:
            return False
        combined = self.passes + self.fails
        combined = sorted(combined, key=lambda r: r.date, reverse=True)

        start_date = None
        for r in combined:
            if r in self.fails:
                if start_date:
                    return False
                continue
            if not start_date:
                start_date = r.date
                continue
            delta = start_date - r.date
            if delta.days >= 7:
                return True
        return True

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

runs = sorted(runs, key=lambda r: r.date, reverse=True)
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
regressions = []
dmesg_fails = []
for k,v in tests.items():
    v.sort_results()
    if len(v.fails) and v.fails[0].recent():
        fails.append(v)
        if v.regression():
            regressions.append(v)
        for f in v.fails:
            if not f.recent():
                break
            if f.dmesg_output():
                dmesg_fails.append(v)
                break
    elif len(v.passes):
        passes.append(v)

    test_runs = v.passes + v.fails
    test_runs = sorted(test_runs, key=lambda r: r.date, reverse=True)

    try:
        os.mkdir(os.environ["RESULTS_DIR"] + "/" + os.path.dirname(k))
    except FileExistsError:
        pass

    f = open(os.environ["RESULTS_DIR"] + "/" + k + ".html", "w")
    f.write(test_template.render(test=v, runs=test_runs))
    f.close()

recent_runs = []
for r in runs:
    if r.recent():
        recent_runs.append(r)

f = open(os.environ["RESULTS_DIR"] + "/index.html", "w")
f.write(index_template.render(fails=fails, passes=passes, runs=recent_runs,
                              regressions=regressions, dmesg_fails=dmesg_fails))
f.close()
