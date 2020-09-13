import os
from dateutil.parser import parse as dparse
import re
from datetime import datetime, timedelta

PASS = 0
NOTRUN = 1
FAIL = 2
DMESG = 3

class Test:
    PASS = 0
    NOTRUN = 1
    FAIL = 2

    def __init__(self, name):
        self.name = name
        self.passes = []
        self.fails = []
        self.notruns = []

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
    def __init__(self, path, username, hostname, date):
        self.dir = path
        self.username = username
        self.hostname = hostname
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

    def link(self):
        rel_path = '/'.join(self.dir.split('/')[-4:]) + "/index.html"
        return '<a href="{}">{}</a>'.format(rel_path, self.date)

    def total_run(self):
        return len(self.fails) + len(self.notruns) + len(self.passes)

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
        if i not in tests:
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

def empty_table(cols):
    return '<tr><td colspan="{}">Empty, congrats?</td></tr>'

def create_test_table(instr, label, thname):
    if instr == "":
        instr = empty_table(2)
    ret = '<table class="results"><tr><th class="{}" colspan="2">{}</th></tr>'.format(
            thname, label)
    ret += "<tr><th>Name</th><th>Date</th></tr>"
    ret += instr
    ret += "</table>"
    return ret

def create_test_table_time(instr, label, thname):
    if instr == "":
        instr = empty_table(3)
    ret = '<table class="results_time"><tr><th class="{}" colspan="3">{}</th></tr>'.format(
            thname, label)
    ret += "<tr><th>Name</th><th>Date</th><th>Run time</th></tr>"
    ret += instr
    ret += "</table>"
    return ret

def create_runs_table(instr, label):
    if instr == "":
        instr = empty_table(4)
    ret = '<table class="runs"><tr><th class="runs" colspan="4">{}</th></tr>'.format(label)
    ret += "<tr><th>Username</th><th>Hostname</th><th>Tests Run</th><th>Date</th></tr>"
    ret += instr
    ret += "</table>"
    return ret

def test_result_entry(name, date):
    return "<tr><td>{}</td><td>{}</td></tr>".format(name, date)

def test_result_entry_time(name, date, time):
    return "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(name, date, time)

def test_run_entry(r):
    return "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                r.username, r.hostname, r.total_run(), r.link())

def create_index(tests, runs):
    fail_table = ""
    pass_table = ""
    runs_table = ""

    fail_cnt = 0
    pass_cnt = 0

    for k,v in tests.items():
        v.sort_results()
        if len(v.fails) and v.fails[0].recent():
            fail_cnt += 1
            if fail_cnt >= 10:
                continue
            fail_table += test_result_entry(v.name, v.fails[0].link())
        elif len(v.passes):
            pass_cnt += 1
            if pass_cnt >= 10:
                continue
            pass_table += test_result_entry(v.name, v.passes[0].link())

    runs_cnt = 0
    for r in runs:
        if runs_cnt >= 10:
            break
        runs_table += test_run_entry(r)
        runs_cnt += 1

    f = open("template.html")
    template = f.read()
    f.close()

    fail_table = create_test_table(fail_table, "Failures ({} total)".format(fail_cnt),
            "failing")
    pass_table = create_test_table(pass_table, "Passing ({} total)".format(pass_cnt),
            "passing")
    runs_table = create_runs_table(runs_table, "Runs ({} total)".format(len(runs)))

    template = template.replace('FAILURE_TABLE', fail_table)
    template = template.replace('PASS_TABLE', pass_table)
    template = template.replace('RUNS_TABLE', runs_table)

    f = open(os.environ["RESULTS_DIR"] + "/index.html", "w")
    f.write(template)
    f.close()

def create_summary(run):
    ret = '<table class="summary"><tr><th colspan="2">Summary</th></tr>'
    ret += '<tr><th>Status</th><th>Count</th></tr>'
    ret += '<tr><td>Pass</td><td>{}</td></tr>'.format(len(run.passes))
    ret += '<tr><td>Fail</td><td>{}</td></tr>'.format(len(run.fails))
    ret += '<tr><td>Not Run</td><td>{}</td></tr>'.format(len(run.notruns))
    ret += '</table>'
    return ret

def create_run_page(run, times):
    fail_table = ""
    pass_table = ""
    notruns_table = ""

    f = open("testrun-template.html")
    template = f.read()
    f.close()

    template = template.replace('SUMMARY_TABLE', create_summary(run))

    for t in run.passes:
        time = "unknown"
        if t.name in times:
            time = times[t.name]
        pass_table += test_result_entry_time(t.name, r.date, time)
    for t in run.fails:
        fail_table += test_result_entry(t.name, r.date)
    for t in run.notruns:
        notruns_table += test_result_entry(t.name, r.date)

    fail_table = create_test_table(fail_table,
        "Failures ({} total)".format(len(r.fails)), "failing")
    pass_table = create_test_table_time(pass_table,
        "Passing ({} total)".format(len(run.passes)), "passing")
    notruns_table = create_test_table(notruns_table,
        "Not run ({} total)".format(len(run.notruns)), "notrun")

    template = template.replace('FAILURE_TABLE', fail_table)
    template = template.replace('PASS_TABLE', pass_table)
    template = template.replace('NOTRUNS_TABLE', notruns_table)

    f = open(run.dir + "/index.html", "w")
    f.write(template)
    f.close()


runs = []
for (dirpath, subdirs, filenames) in os.walk(os.environ['RESULTS_DIR']):
    if "check.log" in filenames:
        vals = dirpath.split('/')
        runs.append(TestRun(dirpath, vals[-3], vals[-2], vals[-1]))

runs = sorted(runs, key=lambda r: r.date)

tests = {}
for r in runs:
    times = parse_check_time(r.dir + "/check.time")
    parse_check_log(r, tests)
    create_run_page(r, times)

create_index(tests, runs)
