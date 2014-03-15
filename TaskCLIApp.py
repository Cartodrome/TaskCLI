from flask import Flask, render_template, url_for, request
from TaskCLI import get_cli, format_seconds, get_sub_tasks, run_unit_tests, \
                    start_cli
from collections import namedtuple
import thread
import traceback
import utils
import os
import argparse
import time
import logging
import re
import pickle
import math

log = utils.get_logger(name=__name__)
CLI_NUM = 0
app = Flask(__name__)

r_file = re.compile("(?P<day>[0-3][0-9])-(?P<month>[0-1][0-9])-"
                    "(?P<year>[1-2][0-9]{3}).p")

MESSAGE_HEADERS  = ("Time", "Task", "Message")
TASK_HEADERS     = ("Task", "Date", "Start", "Stop", "Total", "Status") 
ITEMS_PER_PAGE   = 15

@app.route("/")
def home_page():
    urls = get_urls()
    log.debug("Found following URLS: %s", "\n".join([url[1] for url in urls]))
    return render_template("home.html", urls=urls)

@app.route("/example")
def example():
    return render_template("example.html")

@app.route("/messages")
def messages():
    log.debug("Loading /messages")
    if cli.messages:
        return render_template("messages.html", messages=cli.messages, 
            message_headers=MESSAGE_HEADERS)
    else:
        return render_template("empty.html", text="No message to display.")

@app.route("/historical_tasks")
def historical_tasks():
    page = int(request.args.get("page")) if request.args.get("page") else 1 
    tasks = []
    for f in os.listdir("."):
        r = r_file.match(f)
        if r:
            d = r.groupdict()
            tasks.append((d["day"], d["month"], d["year"]))
    if len(tasks) == 0:
        return render_template("empty.html", text="No historical tasks")

    tasks = sorted(tasks, key=lambda x: (x[2] * 365 + x[1] * 31 + x[0]))
    tasks.reverse()

    prev_page, pages, next_page = get_pages(requested_page=page, 
        items_per_page=ITEMS_PER_PAGE, num_items=len(tasks), num_options=5)

    return render_template("historical_tasks.html", 
        tasks=tasks[(page -1) * ITEMS_PER_PAGE: page * ITEMS_PER_PAGE], 
        prev_page=prev_page, pages=pages, current_page=page, 
        next_page=next_page)


@app.route("/tasks/")
def tasks():
    cli_name = request.args.get("cli_name")
    task_name = request.args.get("task_name")
    # Show the current cli by default but allow historical views
    if cli_name is not None and cli_name != "None":
        task_cli = pickle.load(open(cli_name + ".p", "rb"))
    else:
        task_cli = cli   

    log.debug("Loading /tasks") 
    entry   = namedtuple("Entry", TASK_HEADERS)
    tasks = task_cli.get_tasks(parent="None")
    if not tasks:
        return render_template("empty.html", text="No tasks to display.")

    if task_name:
        for task in tasks:
            if task.name == task_name:
                task = task
                break
        else:
            return render_template("empty.html", text="Task does not exist.")  
    else:
        # If not specified default to first task in list.
        task = tasks[0]
    log.debug("Displaying task: %s", task.name)

    # Get associated sub tasks.
    sub_tasks = get_sub_tasks(cli, task)
    log.debug("Found subtasks: %s", ", ".join([t.name for t in sub_tasks]))
    sub_tasks.append(task)
    sub_tasks.sort(key=lambda task: task.name)

    entries = []
    total_time = 0
    for sub_task in sub_tasks:
        for timer in sub_task.timers:

            date, start = timer.start_time()
            dummy, stop = timer.stop_time()
            time_secs   = timer.total_time().total_seconds()
            time_str    = format_seconds(time_secs)
            status      = timer.status

            entries.append(entry(Task=sub_task.name.lstrip(
                                                    task.name).lstrip("-"),
                                 Date=date,
                                 Start=start,
                                 Stop=stop,
                                 Total=time_str,
                                 Status=status))

            if sub_task.name == task.name:
                if time_secs:
                    total_time += time_secs

    # Add a summary to the end.
    entries.append(entry(Task="Summary",
                         Date="",
                         Start="",
                         Stop="",
                         Total=format_seconds(total_time),
                         Status=task.status))

    log.debug("%s entry(s) for task", len(entries))

    messages = [message for message in cli.messages if message[1] in 
                [task.name for sub_task in sub_tasks]]

    return render_template("tasks.html",
                           current_task=task,
                           tasks=tasks,
                           messages=messages,
                           entries=entries,
                           task_headers=TASK_HEADERS,
                           message_headers=MESSAGE_HEADERS,
                           cli_name=cli_name)

def get_urls():
    links = []
    for rule in app.url_map.iter_rules():
        try: 
            links.append((rule.endpoint, url_for(rule.endpoint)))
        except Exception:
            log.debug(traceback.format_exc())

    return links

def get_pages(requested_page, items_per_page, num_items, num_options):
    first_page = requested_page - (num_options/2)
    total_pages =  int(math.ceil(num_items / float(items_per_page))) 
    
    if first_page < 1:
        first_page = 1
    if first_page == requested_page:
        prev = requested_page
    else:
        prev = requested_page - 1 

    last_page = first_page + num_options

    if last_page > total_pages:
        first_page += total_pages - last_page
        if first_page < 1:
            first_page = 1
        last_page = total_pages
    if last_page == requested_page:
        next = requested_page
    else:
        next = requested_page + 1

    return prev, range(first_page, last_page + 1), next

def get_args():
    parser = argparse.ArgumentParser(description="TaskCLI WebServer")
    parser.add_argument('mode', metavar='<mode>', type=str, 
        help="Either - 'DEV' (to run as a development server), 'LIVE' (to run "
             "the Live server), 'UNIT' (to run unit tests).")
    parser.add_argument('--noreload', action='store_true',
        help="stop the development server from autoreloading")
    
    args = parser.parse_args()

    if args.mode in ["UNIT", "DEV", "LIVE"]:
        pass
    else:
        parser.print_usage()
        quit()

    return args

def start_unit_tests(cli):
    print "Setting Up Unit Test Enviroment"
    thread.start_new_thread(cli.cmdloop, ("UNIT TEST",))
    run_unit_tests(cli)
    time.sleep(5)

    tc = app.test_client()
    print " Unit Test Enviroment setup complete. Running Tests."

    print "Test Get '/'"
    tc.get("/")

    print "Test Get '/messages'"
    tc.get("/messages")

    print "Test Get '/tasks'"
    tc.get("/tasks")

    print "Tests Passed."
    quit()

def start_live_server(cli, msg):
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    thread.start_new_thread(start_cli, (cli, msg))
    app.run()

def start_dev_server(cli, use_reloader=True):
    # If we're not careful here the Werkzeug reloader will created multiple
    # instances of the TaskCLI object resulting in some funky behaviour. More
    # details here: http://stackoverflow.com/questions/11571656
    if use_reloader and not os.environ.get("WERKZEUG_RUN_MAIN"):
        log.info('startup: pid %d is the werkzeug reloader', os.getpid())
    else:
        log.info('startup: pid %d is the active werkzeug', os.getpid())
        thread.start_new_thread(start_cli, (cli, msg + " DEVELOPMENT"))

    app.run(debug=True, use_reloader=use_reloader)


if __name__ == "__main__":

    args = get_args()
    cli, msg = get_cli()

    if args.mode == "UNIT":
        start_unit_tests(cli)
    elif args.mode == "DEV":
        start_dev_server(cli, use_reloader=(not args.noreload))
    elif args.mode == "LIVE":
        start_live_server(cli, msg)
    else:
        AssertionError("Webserver failed to start.")
